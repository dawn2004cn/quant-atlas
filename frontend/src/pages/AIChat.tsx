import { useState, useRef, useEffect } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type OnboardingStep = {
  label: string;
  prompt: string;
};

const ONBOARDING_STEPS: OnboardingStep[] = [
  { label: "大盘分析", prompt: "请分析当前A股市场整体走势和情绪" },
  { label: "热点板块", prompt: "今天有哪些热点板块？资金流向如何？" },
  { label: "个股诊断", prompt: "如何分析一只股票的估值和基本面？" },
];

export function AIChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  /* Check if there's an existing session */
  const { data: sessionData, isLoading: sessionLoading } = useSWR(
    "ai-chat-session",
    () => apiFetchV1<{ session_id?: string }>("/ai/chat/session").catch(
      () => ({}) as { session_id?: string },
    ),
  );

  useEffect(() => {
    if (sessionData?.session_id) {
      setSessionId(sessionData.session_id);
    }
  }, [sessionData]);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

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

      if (!response.ok) {
        throw new Error(`请求失败 (${response.status})`);
      }

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

        for (const chunk of chunks) {
          const trimmed = chunk.trim();
          if (trimmed.startsWith("data: ")) {
            const payload = trimmed.slice(6);
            if (payload === "[DONE]") break;
            try {
              const parsed = JSON.parse(payload);
              const delta = parsed.choices?.[0]?.delta?.content || parsed.content || "";
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  updated[updated.length - 1] = { ...last, content: last.content + delta };
                }
                return updated;
              });
            } catch {
              /* skip malformed chunk */
            }
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "发送失败");
    } finally {
      setSubmitting(false);
    }
  };

  if (sessionLoading) {
    return <PageSkeleton rows={3} />;
  }

  const isEmpty = messages.length === 0;

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <div>
        <h1 className="text-2xl font-bold">AI 对话</h1>
        <p className="text-sm text-zinc-500">与投资研究助手自然语言交流</p>
      </div>

      <Panel className="flex h-[60vh] flex-col gap-4 overflow-y-auto p-4">
        {isEmpty && !error && (
          <div className="flex flex-1 flex-col items-center justify-center gap-6 text-center">
            <div className="text-4xl">🤖</div>
            <p className="max-w-md text-sm text-zinc-400">
              你好！我是 Quant Atlas 投资助手。你可以问我关于市场分析、个股诊断、策略建议等问题。
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {ONBOARDING_STEPS.map((step) => (
                <button
                  key={step.label}
                  type="button"
                  className="rounded-lg border border-zinc-700/60 px-3 py-1.5 text-xs font-medium text-zinc-400 transition-colors hover:bg-zinc-800/60 hover:text-zinc-200"
                  onClick={() => handleSend(step.prompt)}
                  disabled={submitting}
                >
                  {step.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`chat ${msg.role === "user" ? "chat-end" : "chat-start"}`}
          >
            <div
              className={`chat-bubble max-w-[80%] text-sm ${
                msg.role === "user"
                  ? "chat-bubble-primary"
                  : "bg-zinc-100 dark:bg-zinc-800"
              }`}
            >
              {msg.content || (
                <span className="loading loading-dots loading-sm" />
              )}
            </div>
          </div>
        ))}
      </Panel>

      {error && <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">{error}</div>}

      <div className="flex gap-2">
        <input
          type="text"
          className="rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20 flex-1"
          placeholder="输入你的问题..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend(input);
            }
          }}
          disabled={submitting}
        />
        <button
          type="button"
          className="rounded-lg bg-emerald-500/15 px-4 py-2 text-sm font-semibold text-emerald-400 ring-1 ring-emerald-500/30 transition-colors hover:bg-emerald-500/20"
          onClick={() => handleSend(input)}
          disabled={!input.trim() || submitting}
        >
          {submitting ? (
            <span className="loading loading-spinner loading-sm" />
          ) : (
            "发送"
          )}
        </button>
      </div>
    </div>
  );
}
