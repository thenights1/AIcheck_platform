const BASE = "/api";

function getHeaders(): Record<string, string> {
  const token = localStorage.getItem("compliance_token");
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem("compliance_token");
}

export function getStoredUser() {
  const raw = localStorage.getItem("compliance_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function logout() {
  localStorage.removeItem("compliance_token");
  localStorage.removeItem("compliance_user");
}

export async function login(username: string, password: string) {
  const resp = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!resp.ok) {
    const err = await resp.json();
    throw new Error(err.detail || "Login failed");
  }
  const data = await resp.json();
  localStorage.setItem("compliance_token", data.token);
  localStorage.setItem("compliance_user", JSON.stringify(data.user));
  return data.user;
}

export async function getSkills() {
  const resp = await fetch(`${BASE}/checkers`, { headers: getHeaders() });
  if (!resp.ok) throw new Error("Failed to fetch skills");
  return resp.json();
}

export async function createTask(
  taskName: string,
  targetFolder: string,
  skills: string[],
  agentId: string = "",
) {
  const resp = await fetch(`${BASE}/scan`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ task_name: taskName, target_folder: targetFolder, skills, agent_id: agentId }),
  });
  if (!resp.ok) {
    const err = await resp.json();
    throw new Error(err.detail || "Failed to create task");
  }
  return resp.json();
}

export async function listTasks() {
  const resp = await fetch(`${BASE}/scan`, { headers: getHeaders() });
  if (!resp.ok) throw new Error("Failed to fetch tasks");
  return resp.json();
}

export async function getTaskDetail(taskId: string) {
  const resp = await fetch(`${BASE}/scan/${taskId}`, { headers: getHeaders() });
  if (!resp.ok) throw new Error("Task not found");
  return resp.json();
}

export async function deleteTask(taskId: string) {
  const resp = await fetch(`${BASE}/scan/${taskId}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!resp.ok) throw new Error("Failed to delete task");
  return resp.json();
}

export async function getAgents() {
  const resp = await fetch(`${BASE}/agent/list`, { headers: getHeaders() });
  if (!resp.ok) return [];
  return resp.json();
}
