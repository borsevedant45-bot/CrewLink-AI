import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

export function Login() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [badgeCode, setBadgeCode] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(badgeCode, pin);
      navigate('/tasks', { replace: true });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t('auth.loginError'),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded border border-field-border bg-field-surface p-6"
      >
        <h1 className="mb-6 text-field-xl">{t('auth.login')}</h1>

        {error && (
          <div
            role="alert"
            className="mb-4 rounded border border-field-priority-urgent bg-field-priority-urgent/10 p-3 text-field-base text-field-priority-urgent"
          >
            {error}
          </div>
        )}

        <div className="mb-4">
          <label
            htmlFor="badgeCode"
            className="mb-1 block text-field-base font-semibold"
          >
            {t('auth.badgeCode')}
          </label>
          <input
            id="badgeCode"
            type="text"
            value={badgeCode}
            onChange={(e) => setBadgeCode(e.target.value)}
            required
            className="min-h-thumb w-full rounded border border-field-border bg-field-bg px-3 text-field-base"
          />
        </div>

        <div className="mb-6">
          <label
            htmlFor="pin"
            className="mb-1 block text-field-base font-semibold"
          >
            {t('auth.pin')}
          </label>
          <input
            id="pin"
            type="password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            required
            className="min-h-thumb w-full rounded border border-field-border bg-field-bg px-3 text-field-base"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="min-h-thumb w-full rounded-lg bg-field-text-accent text-field-base font-semibold text-white disabled:opacity-50"
        >
          {loading ? t('app.loading') : t('auth.login')}
        </button>
      </form>
    </div>
  );
}
