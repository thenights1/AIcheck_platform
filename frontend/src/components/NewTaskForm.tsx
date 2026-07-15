import { useEffect, useState } from "react";
import { getSkills, getAgents, createTask } from "../api/client";
import type { AgentInfo, SkillInfo } from "../types";

interface Props {
  onCreated: (taskId: string) => void;
  onBack: () => void;
}

export default function NewTaskForm({ onCreated, onBack }: Props) {
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [taskName, setTaskName] = useState("");
  const [targetFolder, setTargetFolder] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [selectedAgent, setSelectedAgent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getSkills().then(setSkills).catch(() => {});
    getAgents().then(setAgents).catch(() => {});
  }, []);

  const toggle = (name: string) => {
    const next = new Set(selected);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setSelected(next);
  };

  const selectAll = () => {
    if (selected.size === skills.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(skills.map((s) => s.name)));
    }
  };

  const handleSubmit = async () => {
    setError("");
    if (!taskName.trim()) {
      setError("请输入任务名称");
      return;
    }
    if (!targetFolder.trim()) {
      setError("请输入目标文件夹路径");
      return;
    }
    if (selected.size === 0) {
      setError("请至少选择一个合规技能");
      return;
    }

    setSubmitting(true);
    try {
      const result = await createTask(taskName.trim(), targetFolder.trim(), Array.from(selected), selectedAgent);
      onCreated(result.task_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  const onlineAgents = agents.filter((a) => a.online);

  return (
    <div>
      <div className="mb-6 flex items-center gap-3">
        <button onClick={onBack} className="text-sm text-slate-400 hover:text-white">&larr; 返回</button>
        <h2 className="text-lg font-semibold text-white">新建合规审查任务</h2>
      </div>

      <div className="max-w-xl space-y-6">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1.5">任务名称</label>
          <input
            type="text"
            value={taskName}
            onChange={(e) => setTaskName(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
            placeholder="例如：2024年Q4数据隐私合规审查"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1.5">目标文件夹路径</label>
          <input
            type="text"
            value={targetFolder}
            onChange={(e) => setTargetFolder(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
            placeholder="例如：D:\projects\compliance-docs\2024Q4"
          />
          <p className="mt-1 text-xs text-slate-500">Agent 将在此目录下按技能逐一审查文档</p>
        </div>

        {/* Agent selection */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1.5">执行 Agent</label>
          {onlineAgents.length === 0 ? (
            <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-400">
              暂无可用的在线 Agent。请先在目标机器上安装并启动 Agent，然后前往 <strong>Agent</strong> 页面确认连接状态。
            </div>
          ) : (
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            >
              <option value="">-- 选择 Agent --</option>
              {onlineAgents.map((ag) => (
                <option key={ag.agent_id} value={ag.agent_id}>
                  {ag.name} ({ag.ip})
                </option>
              ))}
            </select>
          )}
          <p className="mt-1 text-xs text-slate-500">
            选择一台已连接的 Agent 执行审查任务。只有在线 Agent 可选。
          </p>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="text-sm font-medium text-slate-300">选择合规技能</label>
            <button onClick={selectAll} className="text-xs text-blue-400 hover:text-blue-300">
              {selected.size === skills.length ? "取消全选" : "全选"}
            </button>
          </div>
          {skills.length === 0 ? (
            <p className="text-xs text-slate-500">暂无可用的合规技能</p>
          ) : (
            <div className="space-y-2">
              {skills.map((skill) => (
                <label
                  key={skill.name}
                  className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                    selected.has(skill.name)
                      ? "border-blue-500/40 bg-blue-500/10"
                      : "border-slate-700 bg-slate-800/50 hover:border-slate-600"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(skill.name)}
                    onChange={() => toggle(skill.name)}
                    className="mt-0.5 h-4 w-4 rounded border-slate-600 bg-slate-800 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <div className="text-sm font-medium text-white">{skill.label}</div>
                    <div className="mt-0.5 text-xs text-slate-400">{skill.description}</div>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
            {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={submitting || onlineAgents.length === 0}
          className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
        >
          {onlineAgents.length === 0 ? "需要先连接 Agent" : (submitting ? "创建中..." : "创建审查任务")}
        </button>
      </div>
    </div>
  );
}
