import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { useTranslation } from 'react-i18next';
import {
  LanguageProvider,
  useLanguage,
} from '../src/contexts/LanguageContext';


/*
 * Test 2: Doc #8 §1.5 (3.1.1) — changing preferred_language updates
 * the document root's `lang` attribute. Never hardcoded to `en`.
 */

beforeEach(() => {
  document.documentElement.lang = '';
  document.documentElement.dir = '';
  localStorage.clear();
});

function TestConsumer() {
  const { language, setLanguage } = useLanguage();
  const { t } = useTranslation();

  return (
    <div>
      <span data-testid="current-lang">{language}</span>
      <span data-testid="doc-lang">{document.documentElement.lang}</span>
      <span data-testid="doc-dir">{document.documentElement.dir}</span>
      <span data-testid="translated-title">{t('app.title')}</span>
      <button
        data-testid="set-es"
        onClick={() => setLanguage('es')}
      >
        Set Spanish
      </button>
      <button
        data-testid="set-ar"
        onClick={() => setLanguage('ar')}
      >
        Set Arabic
      </button>
      <button
        data-testid="set-ja"
        onClick={() => setLanguage('ja')}
      >
        Set Japanese
      </button>
    </div>
  );
}

describe('LanguageContext — lang attribute [Doc #8 §1.5, §3.1.1]', () => {
  it('initialises document lang to en by default', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>,
    );

    expect(document.documentElement.lang).toBe('en');
    expect(document.documentElement.dir).toBe('ltr');
  });

  it('updates document.lang when preferred_language changes to es', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>,
    );

    act(() => {
      screen.getByTestId('set-es').click();
    });

    expect(document.documentElement.lang).toBe('es');
    expect(screen.getByTestId('current-lang').textContent).toBe('es');
  });

  it('sets dir="rtl" for Arabic (ar)', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>,
    );

    act(() => {
      screen.getByTestId('set-ar').click();
    });

    expect(document.documentElement.lang).toBe('ar');
    expect(document.documentElement.dir).toBe('rtl');
  });

  it('maintains dir="ltr" for Japanese (ja)', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>,
    );

    act(() => {
      screen.getByTestId('set-ja').click();
    });

    expect(document.documentElement.lang).toBe('ja');
    expect(document.documentElement.dir).toBe('ltr');
  });

  it('persists language choice to localStorage', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>,
    );

    act(() => {
      screen.getByTestId('set-es').click();
    });

    expect(localStorage.getItem('crewlink_preferred_language')).toBe('es');
  });

  it('loads persisted language from localStorage on mount', () => {
    localStorage.setItem('crewlink_preferred_language', 'fr');

    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>,
    );

    expect(document.documentElement.lang).toBe('fr');
    expect(screen.getByTestId('current-lang').textContent).toBe('fr');
  });
});
