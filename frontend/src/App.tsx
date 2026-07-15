import { useState } from "react";
import { getStoredUser, isAuthenticated, logout } from "./api/client";
import TaskList from "./components/TaskList";
import NewTaskForm from "./components/NewTaskForm";
import TaskDetail from "./components/TaskDetail";
import AgentPanel from "./components/AgentPanel";
import type { User } from "./types";

type Page = "list" | "new" | "detail" | "agent";
type AuthMode = "login" | "register";

export default function App() {
  const [user, setUser] = useState<User | null>(getStoredUser);
  const [page, setPage] = useState<Page>("list");
  const [taskId, setTaskId] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [loading, setLoading] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>("login");

  const handleLogin = async () => {
    setAuthError("");
    setLoading(true);
    try {
      const { login } = await import("./api/client");
      const u = await login(username, password);
      setUser(u);
    } catch (e: unknown) {
      setAuthError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    setAuthError("");
    if (username.length < 2) { setAuthError("Username must be at least 2 characters"); return; }
    if (password.length < 4) { setAuthError("Password must be at least 4 characters"); return; }
    setLoading(true);
    try {
      const { register } = await import("./api/client");
      const u = await register(username, password);
      setUser(u);
    } catch (e: unknown) {
      setAuthError(e instanceof Error ? e.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    setUser(null);
  };

  if (!user || !isAuthenticated()) {
    const isLogin = authMode === "login";
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="w-full max-w-sm rounded-xl border border-slate-800 bg-slate-900/80 p-8 shadow-2xl">
          <h1 className="mb-2 text-center text-xl font-bold text-white">ComplianceAudit</h1>
          <p className="mb-6 text-center text-sm text-slate-400">
            {isLogin ? "合规用例审查系统" : "注册新账号"}
          </p>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">用户名</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (isLogin ? handleLogin() : handleRegister())}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                placeholder="admin"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (isLogin ? handleLogin() : handleRegister())}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                placeholder="password"
              />
            </div>
            {authError && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-3 py-2 text-xs text-red-400">
                {authError}
              </div>
            )}
            <button
              onClick={isLogin ? handleLogin : handleRegister}
              disabled={loading}
              className="w-full rounded-lg bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
            >
              {loading ? "处理中..." : (isLogin ? "登录" : "注册")}
            </button>
            <div className="text-center">
              <button
                onClick={() => { setAuthMode(isLogin ? "register" : "login"); setAuthError(""); }}
                className="text-xs text-slate-400 hover:text-blue-400"
              >
                {isLogin ? "没有账号？点击注册" : "已有账号？点击登录"}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <nav className="border-b border-slate-800 bg-slate-900/60">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-4">
            <h1 className="text-sm font-bold text-white">ComplianceAudit</h1>
            <div className="flex gap-1">
              <button
                onClick={() => { setPage("list"); setTaskId(""); }}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  page === "list" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
              >
                任务列表
              </button>
              <button
                onClick={() => setPage("new")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  page === "new" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
              >
                新建任务
              </button>
              <button
                onClick={() => setPage("agent")}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  page === "agent" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
              >
                Agent
              </button>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">{user.username}</span>
            <button
              onClick={handleLogout}
              className="rounded-lg px-3 py-1.5 text-xs text-slate-400 hover:text-white hover:bg-slate-800"
            >
              退出
            </button>
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-6xl px-4 py-8">
        {page === "list" && (
          <TaskList
            onViewTask={(id) => { setTaskId(id); setPage("detail"); }}
            onNewTask={() => setPage("new")}
          />
        )}
        {page === "new" && (
          <NewTaskForm
            onCreated={(id) => { setTaskId(id); setPage("detail"); }}
            onBack={() => setPage("list")}
          />
        )}
        {page === "detail" && (
          <TaskDetail
            taskId={taskId}
            onBack={() => { setPage("list"); setTaskId(""); }}
          />
        )}
        {page === "agent" && (
          <AgentPanel onBack={() => setPage("list")} />
        )}
      </main>
    </div>
  );
}
