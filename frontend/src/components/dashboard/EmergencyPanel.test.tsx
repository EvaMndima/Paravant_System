/**
 * Tests for EmergencyPanel's confirmation gate.
 *
 * This is the most safety-critical component in the UI. Its buttons are
 * labelled HALT TRADING and CLOSE ALL, and in a wired-up system they would
 * halt a live trading loop and close real positions. The gate between an
 * accidental click and execution is a typed confirmation, and that gate is
 * what these tests defend.
 *
 * Scope is deliberate. The panel is 483 lines of prototype with hardcoded
 * positions and a toast in place of a real API call; testing its full surface
 * would be pinning mock data. What is pinned here is the property that must
 * survive the rewiring in assessment item 3.4: **a destructive action requires
 * an exact typed confirmation, and nothing fires before it.**
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ToastProvider } from '@/contexts/ToastContext';

import { EmergencyPanel } from './EmergencyPanel';

function renderPanel(props: Partial<{ isOpen: boolean; onClose: () => void }> = {}) {
  const onClose = props.onClose ?? vi.fn();
  const utils = render(
    <ToastProvider>
      <EmergencyPanel isOpen={props.isOpen ?? true} onClose={onClose} />
    </ToastProvider>,
  );
  return { ...utils, onClose };
}

/** The EXECUTE button inside the confirmation dialog. */
function executeButton(): HTMLButtonElement {
  return screen.getByRole('button', { name: 'EXECUTE' }) as HTMLButtonElement;
}

describe('EmergencyPanel', () => {
  describe('visibility', () => {
    it('renders nothing when closed', () => {
      renderPanel({ isOpen: false });

      expect(screen.queryByText('HALT TRADING')).not.toBeInTheDocument();
    });

    it('renders the emergency actions when open', () => {
      renderPanel();

      expect(screen.getByText('HALT TRADING')).toBeInTheDocument();
      expect(screen.getByText('CLOSE ALL')).toBeInTheDocument();
    });
  });

  describe('confirmation gate', () => {
    it('does not execute on the first click of a destructive action', async () => {
      // The click opens a dialog. If this ever executes directly, a misclick
      // halts trading.
      renderPanel();

      await userEvent.click(screen.getByText('HALT TRADING'));

      expect(screen.getByText('HALT ALL TRADING')).toBeInTheDocument();
      expect(screen.queryByText('Emergency Action Executed')).not.toBeInTheDocument();
    });

    it('disables EXECUTE until the confirmation is typed', async () => {
      renderPanel();

      await userEvent.click(screen.getByText('HALT TRADING'));

      expect(executeButton()).toBeDisabled();
    });

    it('keeps EXECUTE disabled for a partial confirmation', async () => {
      renderPanel();
      await userEvent.click(screen.getByText('HALT TRADING'));

      await userEvent.type(screen.getByPlaceholderText('CONFIRM'), 'CONFIR');

      expect(executeButton()).toBeDisabled();
    });

    it('keeps EXECUTE disabled for the wrong case', async () => {
      // The check is `!== 'CONFIRM'`, so it is case-sensitive. Pinned because
      // relaxing it later would weaken the gate, and that should be a decision
      // rather than a refactor side effect.
      renderPanel();
      await userEvent.click(screen.getByText('HALT TRADING'));

      await userEvent.type(screen.getByPlaceholderText('CONFIRM'), 'confirm');

      expect(executeButton()).toBeDisabled();
    });

    it('keeps EXECUTE disabled when extra characters follow the word', async () => {
      renderPanel();
      await userEvent.click(screen.getByText('HALT TRADING'));

      await userEvent.type(screen.getByPlaceholderText('CONFIRM'), 'CONFIRM!');

      expect(executeButton()).toBeDisabled();
    });

    it('enables EXECUTE on the exact confirmation', async () => {
      renderPanel();
      await userEvent.click(screen.getByText('HALT TRADING'));

      await userEvent.type(screen.getByPlaceholderText('CONFIRM'), 'CONFIRM');

      expect(executeButton()).toBeEnabled();
    });

    it('executes once confirmed', async () => {
      // Asserts the outcome, not the dialog's disappearance. AnimatePresence
      // keeps the exiting node mounted for the duration of its transition, so
      // `not.toBeInTheDocument()` races framer-motion rather than testing
      // anything about the gate.
      renderPanel();
      await userEvent.click(screen.getByText('HALT TRADING'));
      await userEvent.type(screen.getByPlaceholderText('CONFIRM'), 'CONFIRM');

      await userEvent.click(executeButton());

      expect(await screen.findByText('Emergency Action Executed')).toBeInTheDocument();
    });

    it('CANCEL dismisses without executing', async () => {
      renderPanel();
      await userEvent.click(screen.getByText('HALT TRADING'));

      await userEvent.click(screen.getByRole('button', { name: 'CANCEL' }));

      // The action must not have fired. This is the assertion that matters --
      // a cancel that still executes is the worst possible defect here.
      expect(screen.queryByText('Emergency Action Executed')).not.toBeInTheDocument();
    });

    it('does not carry a typed confirmation over to the next action', async () => {
      // If the input is not cleared, the second destructive action arrives
      // pre-confirmed and one click executes it.
      renderPanel();
      await userEvent.click(screen.getByText('HALT TRADING'));
      await userEvent.type(screen.getByPlaceholderText('CONFIRM'), 'CONFIRM');
      await userEvent.click(executeButton());

      await userEvent.click(screen.getByText('CLOSE ALL'));

      expect(executeButton()).toBeDisabled();
    });

    it('requires confirmation for every destructive action, not just the first', async () => {
      renderPanel();

      await userEvent.click(screen.getByText('CLOSE ALL'));

      expect(screen.getByText('CLOSE ALL POSITIONS')).toBeInTheDocument();
      expect(executeButton()).toBeDisabled();
    });
  });
});
