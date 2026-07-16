import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import type { SupportedLanguage } from '@/i18n';

/*
 * Doc #8 §1.5 (3.1.1) — base `lang` attribute matches volunteer's
 * preferred_language on load, never hardcoded to `en`.
 * Doc #8 §3.2 — volunteer sets preferred_language at onboarding,
 * changeable from settings.
 */

interface LanguageContextValue {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

const LANG_STORAGE_KEY = 'crewlink_preferred_language';

function getStoredLanguage(): SupportedLanguage | null {
  try {
    const val = localStorage.getItem(LANG_STORAGE_KEY);
    if (val === 'en' || val === 'es' || val === 'pt' || val === 'fr' ||
        val === 'de' || val === 'ja' || val === 'ko' || val === 'ar') {
      return val;
    }
    return null;
  } catch {
    return null;
  }
}

function setDocumentLang(lang: string): void {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const { i18n } = useTranslation();
  const stored = getStoredLanguage();
  const [language, setLanguageState] = useState<SupportedLanguage>(
    stored ?? 'en',
  );

  useEffect(() => {
    setDocumentLang(language);
    void i18n.changeLanguage(language);
  }, [language, i18n]);

  const setLanguage = useCallback(
    (lang: SupportedLanguage) => {
      setLanguageState(lang);
      try {
        localStorage.setItem(LANG_STORAGE_KEY, lang);
      } catch {
        /* storage unavailable — ephemeral session only */
      }
    },
    [],
  );

  const value = useMemo(() => ({ language, setLanguage }), [language, setLanguage]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return ctx;
}
