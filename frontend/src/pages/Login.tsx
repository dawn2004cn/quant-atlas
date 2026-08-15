import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { loginWithPassword, loginWithSession } from "../lib/api";
import { hasCompletedOnboarding } from "../lib/onboarding";
import { toSpaPath } from "../lib/spaPath";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = toSpaPath((location.state as { from?: string } | null)?.from ?? "/");
  const [mode, setMode] = useState<"jwt" | "session">("jwt");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      try {
        await loginWithPassword(username, password);
      } catch (jwtErr: unknown) {
        const msg = jwtErr instanceof Error ? jwtErr.message : "";
        if (msg.includes("not configured") || msg.includes("API JWT")) {
          setMode("session");
          await loginWithSession(username, password);
        } else {
          throw jwtErr;
        }
      }
      navigate(hasCompletedOnboarding() ? redirectTo : "/onboarding", { replace: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : "登录失败";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-zinc-950 px-4">
      {/* Background decorative element */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden>
        <div className="absolute -left-[20%] -top-[20%] h-[60%] w-[60%] rounded-full bg-emerald-500/3 blur-[120px]" />
        <div className="absolute -bottom-[20%] -right-[20%] h-[50%] w-[50%] rounded-full bg-sky-500/2 blur-[100px]" />
      </div>

      <div className="relative w-full max-w-sm">
        {/* Brand header */}
        <div className="mb-8 text-center">
          <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 ring-1 ring-emerald-500/20">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-emerald-400">
              <path d="M3 3v18h18" /><path d="M7 16l4-8 4 4 4-6" />
            </svg>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100">
            Quant Atlas
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            智能投研平台
          </p>
        </div>

        {/* Login card */}
        <div className="rounded-xl bg-zinc-900/70 p-6 ring-1 ring-zinc-800/50">
          {/* Mode tabs */}
          <div className="mb-6 flex gap-px rounded-lg bg-zinc-800/60 p-0.5">
            <button
              type="button"
              onClick={() => setMode("session")}
              className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                mode === "session"
                  ? "bg-zinc-800 text-zinc-200 shadow-sm"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              Session
            </button>
            <button
              type="button"
              onClick={() => setMode("jwt")}
              className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                mode === "jwt"
                  ? "bg-zinc-800 text-zinc-200 shadow-sm"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              API Token
            </button>
          </div>

          <form className="space-y-4" onSubmit={onSubmit}>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400" htmlFor="username">
                用户名
              </label>
              <input
                id="username"
                className="w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 transition-colors focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20"
                placeholder="输入用户名"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400" htmlFor="password">
                密码
              </label>
              <input
                id="password"
                type="password"
                className="w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 transition-colors focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20"
                placeholder="输入密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>

            {error ? (
              <div className="rounded-lg border border-rose-500/20 bg-rose-500/8 px-3 py-2.5 text-sm text-rose-400">
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-emerald-500/15 px-4 py-2.5 text-sm font-semibold text-emerald-400 ring-1 ring-emerald-500/30 transition-all hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-emerald-400/40 border-t-emerald-400" />
                  登录中…
                </span>
              ) : (
                "登录"
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-zinc-600">
          <a href="/login" className="transition-colors hover:text-zinc-400">
            使用经典登录页
          </a>
        </p>
      </div>
    </div>
  );
}