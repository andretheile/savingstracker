import React, { useEffect, useRef, useState } from 'react';
import { Brain, Check, CircleAlert, Loader2, Send, Sparkles, Trash2, Wrench } from 'lucide-react';
import { fetchJson, streamChat, type ChatStreamEvent } from '../api';
import { ChatMarkdown } from './ChatMarkdown';

interface ChatStep {
  id: string;
  type: 'thinking' | 'tool';
  content?: string;
  name?: string;
  label?: string;
  arguments?: Record<string, unknown>;
  summary?: string;
  status?: 'running' | 'done' | 'error';
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  steps?: ChatStep[];
}

interface LLMStatus {
  configured: boolean;
  model: string | null;
}

const STORAGE_KEY = 'savingstracker-chat';
const SUGGESTIONS = [
  'How is household cashflow this month?',
  'What did we spend on groceries?',
  'Which accounts count toward household totals?',
];

function loadMessages(): ChatMessage[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChatMessage[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveMessages(messages: ChatMessage[]) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  } catch {
    /* ignore quota */
  }
}

function newId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function formatArgs(args?: Record<string, unknown>) {
  if (!args) return '';
  return Object.entries(args)
    .map(([key, value]) => `${key} ${String(value)}`)
    .join(' · ');
}

const ChatTrace: React.FC<{ steps: ChatStep[] }> = ({ steps }) => {
  if (steps.length === 0) return null;
  return (
    <div className="mb-2.5 space-y-1.5">
      {steps.map((step) => (
        <div key={step.id} className="flex items-start gap-2 text-[11px] text-[#8A8278] leading-snug">
          {step.type === 'thinking' ? (
            <Brain className="w-3.5 h-3.5 mt-0.5 shrink-0 text-[#C4B49A]" strokeWidth={1.6} />
          ) : step.status === 'error' ? (
            <CircleAlert className="w-3.5 h-3.5 mt-0.5 shrink-0 text-[#8C4A3A]" strokeWidth={1.6} />
          ) : step.status === 'running' ? (
            <Loader2 className="w-3.5 h-3.5 mt-0.5 shrink-0 animate-spin text-[#8F7848]" strokeWidth={1.6} />
          ) : (
            <Wrench className="w-3.5 h-3.5 mt-0.5 shrink-0 text-[#C4B49A]" strokeWidth={1.6} />
          )}
          <div className="min-w-0">
            {step.type === 'thinking' ? (
              <p>{step.content}</p>
            ) : (
              <p>
                <span className="text-[#6B645A]">{step.label || step.name}</span>
                {formatArgs(step.arguments) ? (
                  <span className="text-[#A39B90]"> · {formatArgs(step.arguments)}</span>
                ) : null}
                {step.summary ? (
                  <span className={step.status === 'error' ? 'text-[#8C4A3A]' : 'text-[#3D6B54]'}>
                    {' '}
                    {step.status === 'done' ? (
                      <Check className="w-3 h-3 inline -mt-0.5" strokeWidth={2} />
                    ) : null}{' '}
                    {step.summary}
                  </span>
                ) : step.status === 'running' ? (
                  <span className="text-[#A39B90]"> …</span>
                ) : null}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

interface ChatViewProps {
  onDataChanged?: () => void | Promise<void>;
  onOpenSettings?: () => void;
}

export const ChatView: React.FC<ChatViewProps> = ({ onDataChanged, onOpenSettings }) => {
  const [status, setStatus] = useState<LLMStatus | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>(loadMessages);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const refreshStatus = async () => {
    const data = await fetchJson<LLMStatus>('/llm/status');
    setStatus(data);
  };

  useEffect(() => {
    refreshStatus().catch((err) => console.error('Failed to load chat status', err));
  }, []);

  useEffect(() => {
    saveMessages(messages);
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setDraft('');
    setError('');
    const userMsg: ChatMessage = { id: newId(), role: 'user', content: trimmed };
    const assistantId = newId();
    const assistantMsg: ChatMessage = { id: assistantId, role: 'assistant', content: '', steps: [] };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setBusy(true);

    const patchAssistant = (updater: (msg: ChatMessage) => ChatMessage) => {
      setMessages((prev) =>
        prev.map((msg) => (msg.id === assistantId ? updater(msg) : msg))
      );
    };

    try {
      await streamChat(trimmed, (event: ChatStreamEvent) => {
        if (event.type === 'thinking' && event.content) {
          const step: ChatStep = { id: newId(), type: 'thinking', content: event.content };
          patchAssistant((msg) => ({ ...msg, steps: [...(msg.steps || []), step] }));
        } else if (event.type === 'tool') {
          const step: ChatStep = {
            id: newId(),
            type: 'tool',
            name: event.name,
            label: event.label,
            arguments: event.arguments,
            status: 'running',
          };
          patchAssistant((msg) => ({ ...msg, steps: [...(msg.steps || []), step] }));
        } else if (event.type === 'tool_result') {
          patchAssistant((msg) => {
            const steps = [...(msg.steps || [])];
            for (let i = steps.length - 1; i >= 0; i -= 1) {
              if (steps[i].type === 'tool' && steps[i].name === event.name && steps[i].status === 'running') {
                steps[i] = {
                  ...steps[i],
                  summary: event.summary,
                  status: event.status === 'error' ? 'error' : 'done',
                };
                break;
              }
            }
            return { ...msg, steps };
          });
        } else if (event.type === 'reply' && event.content) {
          patchAssistant((msg) => ({ ...msg, content: event.content || '' }));
        } else if (event.type === 'error') {
          setError(event.detail || 'Chat request failed');
        }
      });
      await onDataChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chat request failed');
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void send(draft);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void send(draft);
    }
  };

  const handleReset = async () => {
    setBusy(true);
    setError('');
    try {
      await fetchJson('/llm/reset', { method: 'POST' });
      setMessages([]);
      sessionStorage.removeItem(STORAGE_KEY);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not clear chat');
    } finally {
      setBusy(false);
    }
  };

  if (!status) {
    return (
      <div className="cream-panel p-6">
        <p className="text-xs text-[#8A8278]">Loading chat…</p>
      </div>
    );
  }

  if (!status.configured) {
    return (
      <div className="cream-panel p-6">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 bg-[#F3F0EA] border border-[#E5DFD4] flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4 text-[#8F7848]" strokeWidth={1.6} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-[#1A1714] font-heading leading-none">Chat</h3>
            <p className="text-xs text-[#6B645A] mt-2">
              Add an OpenRouter key in Settings to ask about spending, recategorize payments, or change household data.
            </p>
            {onOpenSettings && (
              <button
                type="button"
                onClick={onOpenSettings}
                className="gold-button-primary text-xs px-4 py-2 mt-4"
              >
                Open settings
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="cream-panel flex flex-col min-h-[calc(100vh-14rem)]">
      <div className="flex items-center justify-between gap-3 px-5 py-3.5 border-b border-[#E5DFD4]">
        <div className="flex items-center gap-2.5 min-w-0">
          <Sparkles className="w-4 h-4 text-[#8F7848] shrink-0" strokeWidth={1.6} />
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-[#1A1714] font-heading leading-none">Chat</h3>
            <p className="text-[10px] text-[#8A8278] mt-1 truncate">{status.model}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void handleReset()}
          disabled={busy || messages.length === 0}
          className="cream-button h-8 px-3 text-xs inline-flex items-center gap-1.5 disabled:opacity-40"
        >
          <Trash2 className="w-3.5 h-3.5" strokeWidth={1.6} />
          Clear
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {messages.length === 0 && !busy && (
          <div className="py-8 text-center">
            <p className="text-sm text-[#6B645A]">
              Ask about household finances, or change data the way you would in the other tabs.
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => void send(prompt)}
                  className="cream-button h-auto px-3 py-1.5 text-xs text-left"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] px-3.5 py-2.5 text-[13px] leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-[#1A1714] text-[#F4F1EA] rounded-lg rounded-br-sm whitespace-pre-wrap'
                  : 'bg-[#F3F0EA] text-[#1A1714] border border-[#E5DFD4] rounded-lg rounded-bl-sm'
              }`}
            >
              {msg.role === 'assistant' && <ChatTrace steps={msg.steps || []} />}
              {msg.role === 'user' ? msg.content : <ChatMarkdown content={msg.content} />}
              {msg.role === 'assistant' && busy && !msg.content && (
                <div className="flex items-center gap-1.5 pt-1">
                  <span className="chat-dot" />
                  <span className="chat-dot" />
                  <span className="chat-dot" />
                </div>
              )}
            </div>
          </div>
        ))}

        {busy && messages[messages.length - 1]?.role !== 'assistant' && (
          <div className="flex justify-start">
            <div className="bg-[#F3F0EA] border border-[#E5DFD4] rounded-lg rounded-bl-sm px-3.5 py-2.5 flex items-center gap-1.5">
              <span className="chat-dot" />
              <span className="chat-dot" />
              <span className="chat-dot" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <p className="px-5 pb-2 text-xs text-[#8C4A3A]">{error}</p>
      )}

      <form onSubmit={handleSubmit} className="border-t border-[#E5DFD4] p-3 flex items-end gap-2">
        <textarea
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about spending, categories, KPIs…"
          rows={1}
          disabled={busy}
          className="cream-input chat-composer flex-1 px-3 text-sm"
        />
        <button
          type="submit"
          disabled={busy || !draft.trim()}
          className="gold-button-primary h-9 w-9 px-0 shrink-0 disabled:opacity-40"
          aria-label="Send"
        >
          {busy ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" strokeWidth={1.6} />
          )}
        </button>
      </form>
    </div>
  );
};
