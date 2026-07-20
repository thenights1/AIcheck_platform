import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getTaskDetail } from "../api/client";
import type { TaskDetail as TaskDetailType } from "../types";

interface Props {
  taskId: string;
  onBack: () => void;
}

const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  pending: { label: "等待中", cls: "border-slate-600 bg-slate-800 text-slate-400" },
  running: { label: "执行中", cls: "border-blue-500/30 bg-blue-500/15 text-blue-400" },
  complete: { label: "已完成", cls: "border-green-500/30 bg-green-500/15 text-green-400" },
  cancelled: { label: "已取消", cls: "border-amber-500/30 bg-amber-500/15 text-amber-400" },
  error: { label: "异常", cls: "border-red-500/30 bg-red-500/15 text-red-400" },
};

const RESULT_STATUS_MAP: Record<string, { label: string; cls: string }> = {
  pending: { label: "等待", cls: "text-slate-500" },
  running: { label: "执行中", cls: "text-blue-400" },
  pass: { label: "通过", cls: "text-green-400" },
  fail: { label: "不通过", cls: "text-red-400" },
  error: { label: "异常", cls: "text-amber-400" },
};

export default function TaskDetail({ taskId, onBack }: Props) {
  const [task, setTask] = useState<TaskDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [rawExpanded, setRawExpanded] = useState<Set<string>>(new Set());

  const refresh = async () => {
    try {
      const data = await getTaskDetail(taskId);
      setTask(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, [taskId]);

  const toggleExpand = (name: string) => {
    const next = new Set(expanded);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setExpanded(next);
  };

  const toggleRaw = (name: string) => {
    const next = new Set(rawExpanded);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setRawExpanded(next);
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-slate-500">任务未找到</p>
        <button onClick={onBack} className="mt-2 text-sm text-blue-400 hover:text-blue-300">返回列表</button>
      </div>
    );
  }

  const st = STATUS_MAP[task.status] || STATUS_MAP.pending;
  const totalResults = task.results?.length || 0;
  const passCount = task.results?.filter((r) => r.status === "pass").length || 0;
  const failCount = task.results?.filter((r) => r.status === "fail").length || 0;
  const errorCount = task.results?.filter((r) => r.status === "error").length || 0;

  return (
    <div>
      <div className="mb-6 flex items-center gap-3">
        <button onClick={onBack} className="text-sm text-slate-400 hover:text-white">&larr; 返回</button>
        <h2 className="text-lg font-semibold text-white">{task.task_name}</h2>
      </div>

      {/* Summary card */}
      <div className="mb-6 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <div className="text-xs text-slate-500">状态</div>
            <span className={`inline-block mt-1 rounded-lg border px-2 py-0.5 text-xs font-medium ${st.cls}`}>
              {st.label}
            </span>
          </div>
          <div>
            <div className="text-xs text-slate-500">目标文件夹</div>
            <div className="mt-1 text-sm text-slate-300 truncate">{task.target_folder}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">技能进度</div>
            <div className="mt-1 text-sm text-slate-300">
              {task.completed_skills} / {task.total_skills}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500">结果汇总</div>
            <div className="mt-1 text-sm">
              <span className="text-green-400">{passCount}</span>
              <span className="text-slate-600"> / </span>
              <span className="text-red-400">{failCount}</span>
              <span className="text-slate-600"> / </span>
              <span className="text-amber-400">{errorCount}</span>
            </div>
          </div>
        </div>
        {task.total_skills > 0 && (
          <div className="mt-4">
            <div className="flex items-center gap-2">
              <div className="h-2 flex-1 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-blue-500 transition-all duration-500"
                  style={{ width: `${task.progress}%` }}
                />
              </div>
              <span className="text-xs text-slate-500">{task.progress}%</span>
            </div>
          </div>
        )}
        {task.error_message && (
          <div className="mt-3 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
            {task.error_message}
          </div>
        )}
      </div>

      {/* Results per skill */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-300">技能执行结果</h3>
        {totalResults === 0 ? (
          <p className="text-xs text-slate-500">等待 Agent 执行...</p>
        ) : (
          task.results.map((result) => {
            const rs = RESULT_STATUS_MAP[result.status] || RESULT_STATUS_MAP.pending;
            const isExpanded = expanded.has(result.skill_name);
            return (
              <div
                key={result.skill_name}
                className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden"
              >
                <button
                  onClick={() => toggleExpand(result.skill_name)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-800/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500 w-5 text-center">
                      {isExpanded ? "▼" : "▶"}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-white">{result.skill_label}</div>
                      <div className="text-xs text-slate-500">{result.skill_name}</div>
                    </div>
                  </div>
                  <span className={`rounded-lg px-2 py-0.5 text-xs font-medium ${rs.cls}`}>
                    {rs.label}
                  </span>
                </button>
                {isExpanded && (
                  <div className="border-t border-slate-800 px-4 py-3">
                    {result.started_at && (
                      <div className="mb-2 text-xs text-slate-500">
                        执行时间：{new Date(result.started_at).toLocaleString("zh-CN")}
                        {result.finished_at && ` → ${new Date(result.finished_at).toLocaleString("zh-CN")}`}
                      </div>
                    )}
                    {result.output ? (
                      <div>
                        <div className="prose prose-invert prose-sm max-w-none bg-slate-950 rounded-lg p-4 max-h-96 overflow-auto">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.output}</ReactMarkdown>
                        </div>
                        {result.result_detail?.raw_output ? (
                          <div className="mt-2">
                            <button
                              onClick={() => toggleRaw(result.skill_name)}
                              className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                            >
                              {rawExpanded.has(result.skill_name) ? "▲ 收起原始报告" : "▼ 原始报告"}
                            </button>
                            {rawExpanded.has(result.skill_name) && (
                              <div className="mt-2 prose prose-invert prose-sm max-w-none bg-slate-950 rounded-lg p-4 max-h-96 overflow-auto border border-slate-700">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{String(result.result_detail.raw_output)}</ReactMarkdown>
                              </div>
                            )}
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500">等待输出...</p>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
