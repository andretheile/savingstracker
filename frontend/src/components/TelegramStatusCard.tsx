import { useEffect, useState } from 'react';
import { Send, Clock, Link2, Unlink, Loader2, AlertCircle, CheckCircle2, Sparkles } from 'lucide-react';
import { fetchJson } from '../api';

interface TelegramStatus {
  bot_configured: boolean;
  bot_running: boolean;
  bot_username: string | null;
  bot_name: string | null;
  connected: boolean;
  telegram_id: number | null;
  next_digest: string;
  llm_configured: boolean;
  llm_model: string | null;
}

const LLM_MODELS = [
  'x-ai/grok-4.6',
  'anthropic/claude-sonnet-4',
  'openai/gpt-4o-mini',
  'google/gemini-2.5-flash',
];

export const TelegramStatusCard: React.FC = () => {
  const [status, setStatus] = useState<TelegramStatus | null>(null);
  const [token, setToken] = useState('');
  const [llmKey, setLlmKey] = useState('');
  const [llmModel, setLlmModel] = useState(LLM_MODELS[0]);
  const [linkCode, setLinkCode] = useState<string | null>(null);
  const [deepLink, setDeepLink] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    const data = await fetchJson<TelegramStatus>('/telegram/status');
    setStatus(data);
    if (data.llm_model) {
      setLlmModel(data.llm_model);
    }
  };

  useEffect(() => {
    refresh().catch((err) => console.error('Failed to load Telegram status', err));
  }, []);

  const handleSaveLlm = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await fetchJson('/telegram/llm', {
        method: 'POST',
        body: JSON.stringify({ api_key: llmKey.trim(), model: llmModel }),
      });
      setLlmKey('');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save OpenRouter key');
    } finally {
      setBusy(false);
    }
  };

  const handleSaveToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await fetchJson('/telegram/token', {
        method: 'POST',
        body: JSON.stringify({ token: token.trim() }),
      });
      setToken('');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save token');
    } finally {
      setBusy(false);
    }
  };

  const handleConnect = async () => {
    setBusy(true);
    setError('');
    try {
      const data = await fetchJson<{ code: string; deep_link: string | null }>('/telegram/link', {
        method: 'POST',
      });
      setLinkCode(data.code);
      setDeepLink(data.deep_link);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create link');
    } finally {
      setBusy(false);
    }
  };

  const handleUnlink = async () => {
    setBusy(true);
    setError('');
    try {
      await fetchJson('/telegram/unlink', { method: 'POST' });
      setLinkCode(null);
      setDeepLink(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not unlink');
    } finally {
      setBusy(false);
    }
  };

  const handleTest = async () => {
    setBusy(true);
    setError('');
    try {
      await fetchJson('/telegram/test', { method: 'POST' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send test message');
    } finally {
      setBusy(false);
    }
  };

  if (!status) {
    return (
      <div className="cream-panel p-6 mb-8">
        <p className="text-xs text-[#8A8278]">Loading Telegram status…</p>
      </div>
    );
  }

  return (
    <div className="cream-panel p-6 mb-8">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 bg-[#F3F0EA] border border-[#E5DFD4] flex items-center justify-center shrink-0">
            <Send className="w-4 h-4 text-[#8F7848]" strokeWidth={1.6} />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h3 className="text-lg font-semibold text-[#1A1714] font-heading leading-none">Telegram</h3>
              <span
                className={`text-[10px] font-medium tracking-wide uppercase ${
                  status.connected ? 'text-[#3D6B54]' : 'text-[#8A8278]'
                }`}
              >
                {status.connected ? 'Connected' : status.bot_configured ? 'Not linked' : 'Not configured'}
              </span>
            </div>
            <p className="text-xs text-[#6B645A] mt-1">
              {status.connected
                ? `Household digest on the 1st of each month${status.bot_username ? ` via @${status.bot_username}` : ''}. Chat in Telegram to look up or change data.`
                : 'Link Telegram to chat about household finances, or get /kpis and /balance.'}
            </p>
          </div>
        </div>

        {status.connected && (
          <div className="flex items-center gap-2 text-xs text-[#6B645A] shrink-0 md:pl-0 pl-11">
            <Clock className="w-3.5 h-3.5" strokeWidth={1.6} />
            <span>Next: {status.next_digest}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 p-3 bg-[#FAF4F2] border border-[#E8D4CE] text-xs text-[#8C4A3A] flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" strokeWidth={1.6} />
          <p>{error}</p>
        </div>
      )}

      {!status.bot_configured && (
        <form onSubmit={handleSaveToken} className="mt-5 space-y-3">
          <p className="text-xs text-[#6B645A]">
            1. Message{' '}
            <a href="https://t.me/BotFather" className="text-[#8F7848] underline" target="_blank" rel="noreferrer">
              @BotFather
            </a>{' '}
            → /newbot → copy the token.
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="123456789:AAH..."
              className="cream-input text-xs px-3 py-2 flex-1 font-mono"
              required
            />
            <button type="submit" disabled={busy} className="gold-button-primary text-xs px-4 py-2">
              {busy ? 'Saving…' : 'Save token'}
            </button>
          </div>
        </form>
      )}

      {status.bot_configured && !status.connected && (
        <div className="mt-5 space-y-3">
          {linkCode ? (
            <div className="p-3.5 bg-[#F3F0EA] border border-[#E5DFD4] text-xs text-[#6B645A] space-y-2">
              <p className="font-medium text-[#1A1714]">Open Telegram and start the bot</p>
              {deepLink ? (
                <a
                  href={deepLink}
                  target="_blank"
                  rel="noreferrer"
                  className="gold-button-primary inline-flex text-xs px-3 py-2"
                >
                  Open @{status.bot_username || 'bot'}
                </a>
              ) : (
                <p>
                  In Telegram send <code className="font-mono">/start {linkCode}</code>
                  {status.bot_username ? ` to @${status.bot_username}` : ''}.
                </p>
              )}
              <p className="text-[10px] text-[#8A8278]">Code {linkCode} expires in 10 minutes. Then refresh this page.</p>
              <button type="button" onClick={refresh} className="cream-button text-[11px] px-3 py-1.5">
                I have started the bot
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleConnect}
              disabled={busy}
              className="gold-button-primary text-xs px-4 py-2 inline-flex items-center gap-1.5"
            >
              {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Link2 className="w-3.5 h-3.5" strokeWidth={1.6} />}
              Connect Telegram
            </button>
          )}
        </div>
      )}

      {status.connected && (
        <div className="mt-5 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleTest}
            disabled={busy}
            className="cream-button text-xs px-3 py-2 inline-flex items-center gap-1.5"
          >
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.6} />}
            Send test message
          </button>
          <button
            type="button"
            onClick={handleUnlink}
            disabled={busy}
            className="cream-button text-xs px-3 py-2 inline-flex items-center gap-1.5"
          >
            <Unlink className="w-3.5 h-3.5" strokeWidth={1.6} />
            Disconnect
          </button>
        </div>
      )}

      <div className="mt-6 pt-5 border-t border-[#E5DFD4]">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 bg-[#F3F0EA] border border-[#E5DFD4] flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4 text-[#8F7848]" strokeWidth={1.6} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2.5">
              <h4 className="text-sm font-semibold text-[#1A1714] font-heading leading-none">Chat (OpenRouter)</h4>
              <span
                className={`text-[10px] font-medium tracking-wide uppercase ${
                  status.llm_configured ? 'text-[#3D6B54]' : 'text-[#8A8278]'
                }`}
              >
                {status.llm_configured ? 'Ready' : 'Not configured'}
              </span>
            </div>
            <p className="text-xs text-[#6B645A] mt-1">
              {status.llm_configured
                ? `Using ${status.llm_model}. The bot can list transactions, recategorize, exclude one-offs, and change household settings.`
                : 'Paste an OpenRouter key so chat (web or Telegram) can query and update your data.'}
            </p>
            <form onSubmit={handleSaveLlm} className="mt-3 space-y-2">
              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  type="password"
                  value={llmKey}
                  onChange={(e) => setLlmKey(e.target.value)}
                  placeholder={status.llm_configured ? 'Replace key (sk-or-v1-…)' : 'sk-or-v1-…'}
                  className="cream-input text-xs px-3 py-2 flex-1 font-mono"
                  required={!status.llm_configured}
                />
                <select
                  value={llmModel}
                  onChange={(e) => setLlmModel(e.target.value)}
                  className="cream-input text-xs px-3 py-2 sm:w-56"
                >
                  {Array.from(new Set([...LLM_MODELS, llmModel].filter(Boolean))).map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
                <button type="submit" disabled={busy} className="gold-button-primary text-xs px-4 py-2">
                  {busy ? 'Saving…' : status.llm_configured ? 'Update' : 'Save key'}
                </button>
              </div>
              <p className="text-[10px] text-[#8A8278]">
                Create a key at{' '}
                <a href="https://openrouter.ai/keys" className="text-[#8F7848] underline" target="_blank" rel="noreferrer">
                  openrouter.ai/keys
                </a>
                . It is stored in the local .env file.
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
