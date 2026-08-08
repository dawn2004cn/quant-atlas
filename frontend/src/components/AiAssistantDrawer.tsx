import { useEffect, useRef, useState } from "react";

type ChatMessage = { role: "user" | "assistant"; content: string };

type Props = {
  open: boolean;
  onClose: () => void;
};

/**
 * Global AI assistant drawer (SRS: ChatGPT-style sidebar).
 * Compact chat against /api/v1/ai/chat; full page remains at /ai-chat.
 */
export function AiAssistantDrawer({ open, onClose }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const handleSend = async (text: string) => {
    if (!text.trim() || submitting) return;
    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/ai/chat", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });
      if (!response.ok) throw new Error(`请求失败 (${response.status})`);
      const reader = response.body?.getReader();
      if (!reader) throw new Error("无法读取响应流");
      const assistantMsg: ChatMessage = { role: "assistant", content: "" };
      setMessages((prev) => [...prev, assistantMsg]);
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n");
        buffer = chunks.pop() || "";
        for (const line of chunks) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;
          const payload = trimmed.slice(5).trim();
          if (!payload || payload === "[DONE]") continue;
          try {
            const evt = JSON.parse(payload) as {
              type?: string;
              content?: string;
              session_id?: string;
              text?: string;
            };
            if (evt.session_id) setSessionId(evt.session_id);
            const piece = evt.content ?? evt.text ?? "";
            if (piece) {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === "assistant") {
                  next[next.length - 1] = { ...last, content: last.content + piece };
                }
                return next;
              });
            }
          } catch {
            /* ignore malformed SSE */
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "发送失败");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <aside
      className="fixed inset-y-0 right-0 z-[60] flex w-full max-w-md flex-col border-l border-[var(--quant-surface-border)] bg-[var(--quant-surface-strong)] shadow-xl"
      aria-label="AI 助手"
    >
      <div className="flex items-center justify-between border-b border-[var(--quant-surface-border)] px-4 py-3">
        <div>
          <div className="text-sm font-semibold text-[var(--quant-fg)]">AI 助手</div>
          <div className="text-xs text-[var(--quant-muted)]">Esc 关闭 · 完整页见 AI 对话</div>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="/app/ai-chat"
            className="text-xs text-[var(--quant-accent)] hover:underline"
          >
            打开完整页
          </a>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-sm text-[var(--quant-muted)] hover:bg-[var(--quant-surface)] hover:text-[var(--quant-fg)]"
          >
            关闭
          </button>
        </div>
      </div>

      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.length === 0 && (
          <p className="text-sm text-[var(--quant-muted)]">
            用自然语言问行情、策略或风控底线。回答流式返回。
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={`${m.role}-${i}`}
            className={
              m.role === "user"
                ? "ml-8 rounded-lg bg-[var(--quant-accent)]/15 px-3 py-2 text-sm text-[var(--quant-fg)]"
                : "mr-4 rounded-lg bg-[var(--quant-surface)] px-3 py-2 text-sm text-[var(--quant-fg)]"
            }
          >
            {m.content || (m.role === "assistant" && submitting ? "…" : "")}
          </div>
        ))}
        {error && <p className="text-sm text-[var(--tone-danger)]">{error}</p>}
      </div>

      <form
        className="border-t border-[var(--quant-surface-border)] p-3"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSend(input);
        }}
      >
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入问题…"
            className="min-w-0 flex-1 rounded-lg border border-[var(--quant-surface-border)] bg-[var(--quant-surface)] px-3 py-2 text-sm text-[var(--quant-fg)] outline-none focus:border-[var(--quant-accent)]"
            disabled={submitting}
          />
          <button
            type="submit"
            disabled={submitting || !input.trim()}
            className="rounded-lg bg-[var(--quant-accent)] px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            发送
          </button>
        </div>
      </form>
    </aside>
  );
}
