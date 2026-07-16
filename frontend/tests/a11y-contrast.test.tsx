import { describe, it, expect } from 'vitest';

/* Doc #8 §1.1 — 1.4.11 Non-text Contrast, §1.5 — 1.4.3 Contrast Minimum
 * These are design-token-level tests, not rendered-DOM tests.
 * They verify the theme tokens meet WCAG 2.1 AA thresholds.
 *
 * WCAG 2.1 AA contrast thresholds:
 *   - Normal text (<24px / <19px bold): 4.5:1
 *   - Large text (>=24px / >=19px bold): 3:1
 *   - Non-text UI components / graphics: 3:1
 */

/* Relative luminance formula (WCAG 2.1 §1.4.3) */
function relativeLuminance(hex: string): number {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;

  const linearize = (c: number) =>
    c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);

  return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b);
}

function contrastRatio(fg: string, bg: string): number {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

/* Theme tokens from frontend/src/index.css */
const theme = {
  /* Light mode */
  light: {
    bg: '#ffffff',
    surface: '#f5f5f5',
    border: '#666666',
    textPrimary: '#595959',
    textSecondary: '#767676',
    textAccent: '#0055cc',
    priorityUrgent: '#c62828',
    priorityModerate: '#e65100',
    priorityLow: '#2e7d32',
    focus: '#0055cc',
  },
  /* Dark mode */
  dark: {
    bg: '#121212',
    surface: '#1e1e1e',
    border: '#999999',
    textPrimary: '#e0e0e0',
    textSecondary: '#b0b0b0',
    textAccent: '#66b0ff',
    priorityUrgent: '#ef5350',
    priorityModerate: '#ff9800',
    priorityLow: '#66bb6a',
    focus: '#66b0ff',
  },
};

describe('Doc #8 §1.5 — 1.4.3 Contrast (Minimum) AA', () => {
  const thresholds = {
    bodyText: 4.5,
    largeText: 3.0,
    nonText: 3.0,
  };

  describe('Light theme', () => {
    const t = theme.light;

    it(`body text (#${t.textPrimary}) on bg (#${t.bg}) >= 4.5:1`, () => {
      const ratio = contrastRatio(t.textPrimary, t.bg);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.bodyText);
    });

    it(`secondary text (#${t.textSecondary}) on bg (#${t.bg}) >= 4.5:1`, () => {
      const ratio = contrastRatio(t.textSecondary, t.bg);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.bodyText);
    });

    it(`accent text (#${t.textAccent}) on bg (#${t.bg}) >= 4.5:1`, () => {
      const ratio = contrastRatio(t.textAccent, t.bg);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.bodyText);
    });

    it(`urgent priority (#${t.priorityUrgent}) on surface (#${t.surface}) >= 3:1 (non-text)`, () => {
      const ratio = contrastRatio(t.priorityUrgent, t.surface);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.nonText);
    });

    it(`moderate priority (#${t.priorityModerate}) on surface (#${t.surface}) >= 3:1`, () => {
      const ratio = contrastRatio(t.priorityModerate, t.surface);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.nonText);
    });

    it(`low priority (#${t.priorityLow}) on surface (#${t.surface}) >= 3:1`, () => {
      const ratio = contrastRatio(t.priorityLow, t.surface);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.nonText);
    });

    it(`border (#${t.border}) on bg (#${t.bg}) >= 3:1 (non-text)`, () => {
      const ratio = contrastRatio(t.border, t.bg);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.nonText);
    });

    it(`focus ring (#${t.focus}) on bg (#${t.bg}) >= 3:1`, () => {
      const ratio = contrastRatio(t.focus, t.bg);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.nonText);
    });
  });

  describe('Dark theme', () => {
    const t = theme.dark;

    it(`body text (#${t.textPrimary}) on bg (#${t.bg}) >= 4.5:1`, () => {
      const ratio = contrastRatio(t.textPrimary, t.bg);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.bodyText);
    });

    it(`secondary text (#${t.textSecondary}) on bg (#${t.bg}) >= 4.5:1`, () => {
      const ratio = contrastRatio(t.textSecondary, t.bg);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.bodyText);
    });

    it(`urgent priority (#${t.priorityUrgent}) on surface (#${t.surface}) >= 3:1`, () => {
      const ratio = contrastRatio(t.priorityUrgent, t.surface);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.nonText);
    });

    it(`moderate priority (#${t.priorityModerate}) on surface (#${t.surface}) >= 3:1`, () => {
      const ratio = contrastRatio(t.priorityModerate, t.surface);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.nonText);
    });

    it(`low priority (#${t.priorityLow}) on surface (#${t.surface}) >= 3:1`, () => {
      const ratio = contrastRatio(t.priorityLow, t.surface);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.nonText);
    });

    it(`border (#${t.border}) on bg (#${t.bg}) >= 3:1`, () => {
      const ratio = contrastRatio(t.border, t.bg);
      expect(ratio).toBeGreaterThanOrEqual(thresholds.nonText);
    });
  });
});
