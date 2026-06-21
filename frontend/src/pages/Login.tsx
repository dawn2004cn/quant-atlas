import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { loginWithPassword, loginWithSession } from "../lib/api";

type LoginMode = "session" | "jwt";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo =
    (location.state as { from?: string } | null)?.from ?? "/";
  const [mode, setMode] = useState<LoginMode>("session");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (mode === "jwt") {
        await loginWithPassword(username, password);
      } else {
        await loginWithSession(username, password);
      }
      navigate(redirectTo, { replace: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : "登录失败";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center">
      <div className="glass-card p-8">
        <h1 className="text-2xl font-bold">登录 Quant Atlas</h1>
        <p className="mt-2 text-sm text-slate-500">
          Session 模式使用浏览器 Cookie 保持登录
        </p>
        <div className="mt-2 flex items-center gap-2 text-sm">
          <a className="link link-primary" href="/login">
            使用经典登录页
          </a>
          <span className="text-slate-400">|</span>
          <a className="link link-secondary" href="#"
            onClick={(e) => { e.preventDefault(); setMode(mode === "session" ? "jwt" : "session"); }}
          >
            {mode === "session" ? "API JWT 模式" : "Session 模式"}
          </a>
        </div>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <label className="form-control w-full">
            <span className="label-text">用户名</span>
            <input
              className="input input-bordered w-full"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="form-control w-full">
            <span className="label-text">密码</span>
            <input
              type="password"
              className="input input-bordered w-full"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error ? <div className="alert alert-error text-sm">{error}</div> : null}
          <button type="submit" className="btn btn-primary w-full" disabled={loading}>
            {loading ? "登录中…" : "登录"}
          </button>
        </form>
      </div>
    </div>
  );
}
