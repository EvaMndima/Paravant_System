"""Configuration backup and restore system.

Provides compressed backup creation, point-in-time restore, and
retention policy enforcement for critical system state. Backups
include strategies, accounts, positions, risk configuration,
and system state.

Decision: DEC-2026-02-10-002 - Backup retention policy (30 daily + 12 monthly)
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
"""
from __future__ import annotations

import gzip
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)


def _json_encoder(obj: Any) -> str:
    """Custom JSON encoder for non-serializable types.

    Handles datetime objects by converting to ISO format with timezone.
    Raises TypeError for other non-serializable types to prevent silent
    data corruption.

    Args:
        obj: Object to serialize.

    Returns:
        JSON-serializable string representation.

    Raises:
        TypeError: If object type cannot be safely serialized.
    """
    if isinstance(obj, datetime):
        # Preserve timezone information (critical for trading timestamps)
        return obj.isoformat()
    raise TypeError(
        f"Object of type {type(obj).__name__} is not JSON serializable. "
        "Add explicit handling to _json_encoder if this type is required."
    )


class BackupMetadata:
    """Metadata for a backup file.

    Attributes:
        filepath: Full path to the backup file.
        timestamp: When the backup was created (UTC).
        version: Backup format version.
        size_bytes: File size in bytes.
    """

    def __init__(
        self,
        filepath: Path,
        timestamp: datetime,
        version: str = "1.0.0",
        size_bytes: int = 0,
    ) -> None:
        """Initialize backup metadata.

        Args:
            filepath: Path to the backup file.
            timestamp: Creation timestamp (UTC).
            version: Backup format version string.
            size_bytes: File size in bytes.
        """
        self.filepath = filepath
        self.timestamp = timestamp
        self.version = version
        self.size_bytes = size_bytes

    def to_dict(self) -> dict[str, str | int]:
        """Convert metadata to a dictionary.

        Returns:
            Dictionary representation of the metadata.
        """
        return {
            "filepath": str(self.filepath),
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "size_bytes": self.size_bytes,
        }


class ConfigBackupManager:
    """Manages configuration backups with retention policy enforcement.

    Creates compressed (gzip) JSON backups of critical system state and
    enforces a retention policy of 30 daily backups and 12 monthly backups.

    Attributes:
        backup_dir: Directory where backup files are stored.
        daily_retention_days: Number of daily backups to retain.
        monthly_retention_months: Number of monthly backups to retain.
    """

    # Filename pattern: backup_YYYYMMDD_HHMMSS.json.gz
    _FILENAME_PATTERN = re.compile(
        r"backup_(\d{8}_\d{6})\.json\.gz"
    )
    _TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

    def __init__(
        self,
        backup_dir: Path | None = None,
        daily_retention_days: int = 30,
        monthly_retention_months: int = 12,
    ) -> None:
        """Initialize the backup manager.

        Args:
            backup_dir: Directory for storing backups.
                Defaults to ``backups/``.
            daily_retention_days: Number of daily backups to keep.
            monthly_retention_months: Number of monthly backups to keep.

        Raises:
            ValueError: If retention values are negative.
        """
        # MEDIUM-005: Validate retention values are non-negative
        if daily_retention_days < 0:
            raise ValueError(
                f"daily_retention_days must be non-negative, got {daily_retention_days}"
            )
        if monthly_retention_months < 0:
            raise ValueError(
                f"monthly_retention_months must be non-negative, got {monthly_retention_months}"
            )

        self.backup_dir = backup_dir or Path("backups")
        self.daily_retention_days = daily_retention_days
        self.monthly_retention_months = monthly_retention_months

    def _ensure_backup_dir(self) -> None:
        """Create the backup directory if it does not exist."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        data: dict[str, Any] | None = None,
    ) -> BackupMetadata:
        """Create a compressed backup of the provided or current system state.

        If no data is provided, creates a backup with empty collections.
        In production, the caller (Orchestrator) should provide the data
        by querying the database via DataStore.

        Args:
            data: Dictionary containing backup data. If None, creates
                a backup with empty placeholder data.

        Returns:
            BackupMetadata with details about the created backup.
        """
        self._ensure_backup_dir()

        timestamp = datetime.now(timezone.utc)

        # Build backup payload
        backup_data: dict[str, Any] = {
            "timestamp": timestamp.isoformat(),
            "version": "1.0.0",
            "type": "configuration_backup",
        }

        if data is not None:
            backup_data.update(data)
        else:
            # Placeholder structure when no data provided
            backup_data.update({
                "strategies": [],
                "accounts": [],
                "positions": [],
                "risk_config": {},
                "system_state": None,
            })

        # Generate filename and write compressed backup
        filename = f"backup_{timestamp.strftime(self._TIMESTAMP_FORMAT)}.json.gz"
        filepath = self.backup_dir / filename

        # CRITICAL: Use atomic write pattern to prevent corruption
        # Write to temp file first, then rename (atomic on POSIX, near-atomic on Windows)
        temp_filepath = filepath.with_suffix(".tmp")
        try:
            with gzip.open(temp_filepath, "wt", encoding="utf-8") as f:
                # Use custom encoder to preserve datetime timezone info (DEC-2026-02-08-003)
                # NEVER use default=str - it silently corrupts data
                json.dump(backup_data, f, indent=2, default=_json_encoder)

            # Atomic rename completes the backup
            temp_filepath.replace(filepath)
        except Exception:
            # Clean up temp file on failure
            if temp_filepath.exists():
                temp_filepath.unlink()
            raise

        size_bytes = filepath.stat().st_size

        logger.info(
            "backup_created",
            filepath=str(filepath),
            size_bytes=size_bytes,
            timestamp=timestamp.isoformat(),
        )

        metadata = BackupMetadata(
            filepath=filepath,
            timestamp=timestamp,
            version="1.0.0",
            size_bytes=size_bytes,
        )

        # Enforce retention policy after creating backup
        self._apply_retention_policy()

        return metadata

    def restore_backup(self, backup_path: Path) -> dict[str, Any]:
        """Load and return data from a compressed backup file.

        The caller is responsible for applying the restored data to
        the database. This method only reads and returns the data.

        Args:
            backup_path: Path to the backup file to restore.

        Returns:
            Dictionary containing the backup data.

        Raises:
            FileNotFoundError: If the backup file does not exist.
            ValueError: If the backup file is corrupt or invalid.
        """
        if not backup_path.exists():
            raise FileNotFoundError(
                f"Backup file not found: {backup_path}"
            )

        logger.warning(
            "backup_restore_started",
            backup_path=str(backup_path),
        )

        try:
            with gzip.open(backup_path, "rt", encoding="utf-8") as f:
                backup_data: dict[str, Any] = json.load(f)
        except (gzip.BadGzipFile, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Corrupt or invalid backup file: {backup_path}"
            ) from exc

        # Validate required fields
        if "timestamp" not in backup_data or "version" not in backup_data:
            raise ValueError(
                f"Invalid backup format: missing required fields in {backup_path}"
            )

        logger.info(
            "backup_restored",
            backup_path=str(backup_path),
            backup_timestamp=backup_data.get("timestamp"),
            backup_version=backup_data.get("version"),
        )

        return backup_data

    def list_backups(self) -> list[BackupMetadata]:
        """List all available backups sorted by timestamp (newest first).

        Returns:
            List of BackupMetadata objects for each backup file.
        """
        self._ensure_backup_dir()

        backups: list[BackupMetadata] = []
        for filepath in sorted(self.backup_dir.glob("backup_*.json.gz"), reverse=True):
            match = self._FILENAME_PATTERN.match(filepath.name)
            if match:
                timestamp_str = match.group(1)
                try:
                    timestamp = datetime.strptime(
                        timestamp_str, self._TIMESTAMP_FORMAT
                    ).replace(tzinfo=timezone.utc)
                    backups.append(
                        BackupMetadata(
                            filepath=filepath,
                            timestamp=timestamp,
                            size_bytes=filepath.stat().st_size,
                        )
                    )
                except ValueError:
                    logger.warning(
                        "backup_invalid_filename",
                        filepath=str(filepath),
                    )

        return backups

    def _apply_retention_policy(self) -> None:
        """Delete old backups exceeding the retention policy.

        Keeps:
        - Last ``daily_retention_days`` days of daily backups
        - Last ``monthly_retention_months`` months of the most recent
          backup from each month
        """
        now = datetime.now(timezone.utc)
        daily_cutoff = now - timedelta(days=self.daily_retention_days)
        monthly_cutoff = now - timedelta(
            days=self.monthly_retention_months * 30
        )

        all_backups = self.list_backups()

        # Track which monthly backups to keep (first backup per month)
        monthly_kept: dict[str, BackupMetadata] = {}

        for backup in all_backups:
            month_key = backup.timestamp.strftime("%Y-%m")
            if month_key not in monthly_kept:
                monthly_kept[month_key] = backup

        # Determine which backups to delete
        for backup in all_backups:
            # Keep if within daily retention window
            if backup.timestamp >= daily_cutoff:
                continue

            # Keep if it is the representative monthly backup and within
            # the monthly retention window
            month_key = backup.timestamp.strftime("%Y-%m")
            is_monthly_representative = (
                month_key in monthly_kept
                and monthly_kept[month_key].filepath == backup.filepath
            )
            if is_monthly_representative and backup.timestamp >= monthly_cutoff:
                continue

            # Delete backup outside retention windows
            try:
                backup.filepath.unlink()
                logger.info(
                    "backup_deleted_by_retention",
                    filepath=str(backup.filepath),
                    timestamp=backup.timestamp.isoformat(),
                )
            except OSError as exc:
                logger.error(
                    "backup_delete_failed",
                    filepath=str(backup.filepath),
                    error=str(exc),
                )

    def get_latest_backup(self) -> BackupMetadata | None:
        """Get the most recent backup.

        Returns:
            BackupMetadata for the latest backup, or None if no
            backups exist.
        """
        backups = self.list_backups()
        return backups[0] if backups else None
