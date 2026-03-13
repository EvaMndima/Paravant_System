#!/usr/bin/env python
"""
Playwright test to check the system and capture console errors
"""
import asyncio
import json
import sys
import os

# Fix Windows encoding issue
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright

async def test_system():
    console_logs = {
        "errors": [],
        "warnings": [],
        "info": []
    }

    async with async_playwright() as p:
        print("=" * 70)
        print("PARAVANT SYSTEM TEST WITH PLAYWRIGHT")
        print("=" * 70)

        # Launch browser
        print("\n[1] Launching browser...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Capture console messages
        def handle_console_msg(msg):
            log_type = msg.type
            text = msg.text[:200] if msg.text else ""  # Truncate long messages
            if log_type == "error":
                console_logs["errors"].append(text)
                print(f"  [ERROR] {text}")
            elif log_type == "warning":
                console_logs["warnings"].append(text)
                print(f"  [WARNING] {text}")
            elif log_type == "log":
                console_logs["info"].append(text)
                # print(f"  [LOG] {text}")

        page.on("console", handle_console_msg)

        # Go to dashboard
        print("\n[2] Loading dashboard (http://localhost:3001)...")
        try:
            await page.goto("http://localhost:3001", wait_until="domcontentloaded", timeout=15000)
            print("  [OK] Dashboard loaded")
        except Exception as e:
            print(f"  [FAILED] Could not load dashboard: {e}")
            await browser.close()
            return

        # Wait for page to settle
        await page.wait_for_timeout(2000)

        # Check page title/content
        page_text = await page.text_content("body")
        if "Backtest" in page_text or "backtest" in page_text:
            print("  [OK] Backtest page content found")
        else:
            print("  [WARNING] Backtest page content not clearly visible")

        # Try to find and click Run Backtest button
        print("\n[3] Looking for Run Backtest button...")
        try:
            # Try multiple selectors
            button = await page.query_selector('button:has-text("Run Backtest")')
            if not button:
                button = await page.query_selector('[role="button"]:has-text("Run")')
            if not button:
                buttons = await page.query_selector_all("button")
                print(f"  Found {len(buttons)} buttons on page")
                for idx, btn in enumerate(buttons[:5]):
                    text = await btn.text_content()
                    print(f"    Button {idx}: {text[:50]}")
            else:
                print("  [OK] Run Backtest button found")
                print("  [INFO] Clicking button...")
                await page.click('button:has-text("Run Backtest")')
                print("  [OK] Button clicked, waiting for response...")
                await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  [WARNING] Could not interact with button: {e}")

        # Check for error messages on page
        print("\n[4] Checking for error messages on page...")
        error_elements = await page.query_selector_all('[role="alert"], .error, [class*="error"]')
        print(f"  Found {len(error_elements)} potential error elements")
        for elem in error_elements[:3]:
            text = await elem.text_content()
            print(f"    Error: {text[:100]}")

        await browser.close()

        # Print summary
        print("\n" + "=" * 70)
        print("CONSOLE ERROR SUMMARY")
        print("=" * 70)
        print(f"Total Console Errors:   {len(console_logs['errors'])}")
        print(f"Total Console Warnings: {len(console_logs['warnings'])}")
        print(f"Total Console Info:     {len(console_logs['info'])}")

        if console_logs['errors']:
            print("\nDETAILED ERRORS:")
            for i, error in enumerate(console_logs['errors'], 1):
                print(f"{i}. {error}")

        if console_logs['warnings']:
            print("\nDETAILED WARNINGS (first 5):")
            for i, warning in enumerate(console_logs['warnings'][:5], 1):
                print(f"{i}. {warning}")

        print("\n" + "=" * 70)
        print("RECOMMENDATIONS:")
        print("=" * 70)
        if len(console_logs['errors']) > 0:
            print("- Multiple console errors detected")
            print("- Open browser DevTools (F12) to inspect further")
            print("- Check Network tab for failed requests (4xx, 5xx)")
        else:
            print("- No console errors detected - system appears healthy!")

if __name__ == "__main__":
    asyncio.run(test_system())
