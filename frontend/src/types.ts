export interface SkillInfo {
  name: string;
  label: string;
  description: string;
  enabled: boolean;
}

export interface TaskSummary {
  task_id: string;
  task_name: string;
  target_folder: string;
  status: "pending" | "running" | "complete" | "cancelled" | "error";
  progress: number;
  total_skills: number;
  completed_skills: number;
  created_at: string;
  pass_count: number;
  fail_count: number;
  error_count: number;
}

export interface SkillResult {
  skill_name: string;
  skill_label: string;
  status: "pass" | "fail" | "error" | "pending" | "running";
  output: string;
  result_detail: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
}

export interface TaskDetail {
  task_id: string;
  task_name: string;
  target_folder: string;
  skills: string[];
  status: string;
  progress: number;
  total_skills: number;
  completed_skills: number;
  created_at: string;
  updated_at: string;
  error_message: string | null;
  results: SkillResult[];
  summary: TaskSummary;
}

export interface AgentInfo {
  agent_id: string;
  name: string;
  ip: string;
  last_seen: string;
  online: boolean;
}

export interface User {
  user_id: string;
  username: string;
  role: string;
}
