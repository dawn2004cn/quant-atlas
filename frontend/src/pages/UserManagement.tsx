import { useState, useEffect, useCallback } from "react";
import { apiFetchV1 } from "../lib/api";

type UserItem = {
  username?: string;
  role?: string;
  role_name?: string;
  protected?: boolean;
};

type RoleItem = { code?: string; label?: string };

export default function UserManagement() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ username: "", password: "", role: "viewer" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [u, r] = await Promise.all([
        apiFetchV1<{ items?: UserItem[] }>("/users"),
        apiFetchV1<{ items?: RoleItem[] }>("/roles"),
      ]);
      setUsers(u.items ?? []);
      setRoles(r.items ?? []);
    } catch { /* keep state */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function createUser(e: React.FormEvent) {
    e.preventDefault();
    if (!form.username.trim() || !form.password) return;
    setCreating(true);
    try {
      await apiFetchV1("/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      setForm({ username: "", password: "", role: "viewer" });
      load();
    } finally { setCreating(false); }
  }

  async function updateRole(username: string, role: string) {
    await apiFetchV1(`/users/${encodeURIComponent(username)}/role`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    });
    load();
  }

  async function deleteUser(username: string) {
    if (!confirm(`确定要删除用户 ${username} 吗？`)) return;
    await apiFetchV1(`/users/${encodeURIComponent(username)}`, { method: "DELETE" });
    load();
  }

  async function changePassword(username: string) {
    const pw = prompt(`请输入 ${username} 的新密码:`);
    if (!pw) return;
    const pw2 = prompt("请再次输入新密码进行确认:");
    if (pw !== pw2) { alert("两次输入的密码不一致！"); return; }
    await apiFetchV1("/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, new_password: pw, confirm_password: pw2 }),
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs text-[var(--quant-accent)] font-medium mb-1">User Management</div>
        <h1 className="page-title">用户管理</h1>
        <p className="text-[var(--quant-muted)] text-sm mt-1">创建和管理系统用户</p>
      </div>

      {/* Create Form */}
      <div className="quant-card">
        <div className="text-sm font-bold mb-3">创建新用户</div>
        <form onSubmit={createUser} className="flex flex-wrap items-end gap-3">
          <div>
            <label className="text-xs text-[var(--quant-muted)] mb-1 block">用户名</label>
            <input
              type="text"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              required
              className="input input-bordered input-sm bg-[var(--quant-surface)] border-[var(--quant-surface-border)]"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--quant-muted)] mb-1 block">密码</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              className="input input-bordered input-sm bg-[var(--quant-surface)] border-[var(--quant-surface-border)]"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--quant-muted)] mb-1 block">角色</label>
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="select select-bordered select-sm bg-[var(--quant-surface)] border-[var(--quant-surface-border)]"
            >
              {roles.length > 0
                ? roles.map((r) => <option key={r.code} value={r.code}>{r.label}</option>)
                : <>
                    <option value="viewer">访客</option>
                    <option value="trader">交易员</option>
                    <option value="researcher">研究员</option>
                    <option value="developer">开发者</option>
                    <option value="admin">管理员</option>
                  </>
              }
            </select>
          </div>
          <button type="submit" className="btn-brand !text-xs" disabled={creating}>
            {creating ? "创建中..." : "创建用户"}
          </button>
        </form>
      </div>

      {/* User List */}
      <div className="quant-card">
        <div className="text-sm font-bold mb-3">现有用户 ({users.length})</div>
        {loading ? (
          <div className="text-sm text-[var(--quant-muted)]">加载中...</div>
        ) : users.length === 0 ? (
          <div className="text-sm text-[var(--quant-muted)]">暂无用户</div>
        ) : (
          <div className="space-y-2">
            {users.map((u) => (
              <div key={u.username} className="flex items-center justify-between py-2 px-3 rounded-lg bg-[var(--quant-surface)]">
                <div className="flex items-center gap-2 text-sm">
                  {u.protected && <span className="badge-soft !bg-[var(--quant-warn)]/10 !text-[var(--quant-warn)] text-xs">演示</span>}
                  <span className="font-medium">{u.username}</span>
                  <span className="text-[var(--quant-muted)]">({u.role_name ?? u.role})</span>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    defaultValue={u.role}
                    onChange={(e) => updateRole(u.username!, e.target.value)}
                    className="select select-bordered select-xs bg-[var(--quant-surface)] border-[var(--quant-surface-border)]"
                  >
                    {roles.length > 0
                      ? roles.map((r) => <option key={r.code} value={r.code}>{r.label}</option>)
                      : <>
                          <option value="viewer">访客</option>
                          <option value="trader">交易员</option>
                          <option value="researcher">研究员</option>
                          <option value="admin">管理员</option>
                        </>
                    }
                  </select>
                  <button type="button" className="btn btn-ghost btn-xs" onClick={() => changePassword(u.username!)}>改密</button>
                  {!u.protected && (
                    <button type="button" className="btn btn-ghost btn-xs text-[var(--quant-danger)]" onClick={() => deleteUser(u.username!)}>删除</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
