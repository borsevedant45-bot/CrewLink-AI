import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AskCrewLink } from '../src/pages/AskCrewLink';
import { LanguageProvider } from '../src/contexts/LanguageContext';

describe('AskCrewLink — FR-13 voice input stub [Doc #1 §9 Key Assumption 3]', () => {
  it('renders a disabled voice input button', () => {
    render(
      <LanguageProvider>
        <AskCrewLink />
      </LanguageProvider>,
    );

    const btn = screen.getByRole('button', { name: 'Voice' });
    expect(btn).toBeTruthy();
    expect(btn).toBeDisabled();
  });

  it('has a title attribute citing Key Assumption 3', () => {
    render(
      <LanguageProvider>
        <AskCrewLink />
      </LanguageProvider>,
    );

    const btn = screen.getByRole('button', { name: 'Voice' });
    const title = btn.getAttribute('title');
    expect(title).toBeTruthy();
    expect(title?.toLowerCase()).toContain('key assumption 3');
  });
});
