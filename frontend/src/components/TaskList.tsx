import { useEffect, useState } from "react";
import { listTasks, deleteTask } from "../api/client";
import type { TaskSummary } from "../types";

interface Props {
  onViewTask: (id: string) => void;
  onNewTask: () => void;
}

const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  pending: { label: "等待中", cls: "border-slate-600 bg-slate-800 text-slate-400" },
  running: { label: "执行中", cls: "border-blue-500/30 bg-blue-500/15 text-blue-400" },
  complete: { label: "已完成", cls: "border-green-500/30 bg-green-500/15 text-green-400" },
  cancelled: { label: "已取消", cls: "border-amber-500/30 bg-amber-500/15 text-amber-400" },
  error: { label: "异常", cls: "border-red-500/30 bg-red-500/15 text-red-400" },
};

export default function TaskList({ onViewTask, onNewTask }: Props) {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const data = await listTasks();
      setTasks(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await deleteTask(id);
      refresh();
    } catch {
      // ignore
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">合规审查任务</h2>
        <button
          onClick={onNewTask}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
        >
          新建任务
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
        </div>
      ) : tasks.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-700 py-16 text-center">
          <p className="text-sm text-slate-500">暂无合规审查任务</p>
          <p className="mt-1 text-xs text-slate-600">点击"新建任务"创建第一个合规审查</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => {
            const st = STATUS_MAP[task.status] || STATUS_MAP.pending;
            return (
              <div
                key={task.task_id}
                className="group rounded-xl border border-slate-800 bg-slate-900/50 p-4 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1 cursor-pointer" onClick={() => onViewTask(task.task_id)}>
                    <h3 className="text-sm font-medium text-white truncate">{task.task_name}</h3>
                    <p className="mt-0.5 text-xs text-slate-500 truncate">{task.target_folder}</p>
                    <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
                      <span>({task.pass_count} 通过 / {task.fail_count} 不通过 / {task.error_count} 异常)</span>
                      <span className="text-slate-600">{new Date(task.created_at).toLocaleString("zh-CN")}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`rounded-lg border px-2 py-1 text-xs font-medium ${st.cls}`}>{st.label}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(task.task_id); }}
                      className="rounded-lg px-2 py-1 text-xs text-slate-600 hover:text-red-400 hover:bg-red-500/10 opacity-0 group-hover:opacity-100 transition-all"
                    >
                      删除
                    </button>
                  </div>
                </div>
                {task.total_skills > 0 && (
                  <div className="mt-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 flex-1 rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-blue-500 transition-all duration-500"
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-500">{task.progress}%</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
