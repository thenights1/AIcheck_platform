import { useEffect, useState } from "react";
import { getAgents } from "../api/client";
import type { AgentInfo } from "../types";

interface Props {
  onBack: () => void;
}

const DOWNLOAD_URL = "/api/agent/download";

export default function AgentPanel({ onBack }: Props) {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const data = await getAgents();
      setAgents(data);
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

  const onlineCount = agents.filter((a) => a.online).length;

  return (
    <div>
      <div className="mb-6 flex items-center gap-3">
        <button onClick={onBack} className="text-sm text-slate-400 hover:text-white">&larr; 返回</button>
        <h2 className="text-lg font-semibold text-white">Agent 管理</h2>
      </div>

      {/* Agent install guide */}
      <div className="mb-8 rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <h3 className="text-sm font-semibold text-white mb-4">Agent 安装指南</h3>
        <div className="space-y-4 text-sm text-slate-300">

          <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 px-4 py-3">
            <p className="text-xs text-blue-300 leading-relaxed">
              Agent 在用户本地运行，对指定文件夹中的文档进行 SKILL 驱动的合规审查。
              运行前提：本地已安装 <strong>opencode CLI</strong>。其余依赖和技能文件从本页面一键下载。
            </p>
          </div>

          <div>
            <h4 className="font-medium text-slate-200 mb-2">1. 下载 Agent 包</h4>
            <p className="text-slate-400 mb-2">点击下方按钮下载 Agent 包（含运行代码、合规技能、配置文件）：</p>
            <a
              href={DOWNLOAD_URL}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              下载 Agent 包 (ZIP)
            </a>
            <p className="mt-2 text-xs text-slate-500">包含内容：agent/ 运行代码、compliance_skills/ 合规技能、agent.yaml 配置、run_agent.bat 启动脚本</p>
          </div>

          <div>
            <h4 className="font-medium text-slate-200 mb-2">2. 解压并配置服务器地址</h4>
            <p className="text-slate-400 mb-1">解压下载的 ZIP 到任意目录，编辑 <code className="rounded bg-slate-800 px-1 text-xs">agent.yaml</code>：</p>
            <div className="rounded-lg bg-slate-950 px-3 py-2 font-mono text-xs text-slate-300">
              server_url: "http://&lt;本系统地址&gt;:8000"
            </div>
          </div>

          <div>
            <h4 className="font-medium text-slate-200 mb-2">3. 启动 Agent</h4>
            <p className="text-slate-400 mb-1">双击 <code className="rounded bg-slate-800 px-1 text-xs">run_agent.bat</code> 启动，或命令行执行：</p>
            <div className="rounded-lg bg-slate-950 px-3 py-2 font-mono text-xs text-slate-300">
              run_agent.bat &lt;服务器地址&gt;
            </div>
            <p className="mt-1 text-xs text-slate-500">不带参数时默认连接 http://localhost:8000</p>
          </div>

          <div className="rounded-lg border border-green-500/20 bg-green-500/10 px-3 py-2">
            <p className="text-xs text-green-300">
              启动成功后，Agent 会自动注册到本系统。你可以在下方列表中看到它，之后新建审查任务时即可选择此 Agent 来执行。
            </p>
          </div>
        </div>
      </div>

      {/* Agent list */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">
            已连接 Agent
            <span className="ml-2 text-xs font-normal text-slate-500">（{onlineCount}/{agents.length} 在线）</span>
          </h3>
          <button
            onClick={refresh}
            className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs text-slate-400 hover:text-white hover:bg-slate-700"
          >
            刷新
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
          </div>
        ) : agents.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-700 py-12 text-center">
            <p className="text-sm text-slate-500">暂无 Agent 连接</p>
            <p className="mt-1 text-xs text-slate-600">请按照上方指南在目标机器上安装并启动 Agent</p>
          </div>
        ) : (
          <div className="space-y-3">
            {agents.map((agent) => (
              <div
                key={agent.agent_id}
                className={`rounded-xl border p-4 ${
                  agent.online
                    ? "border-slate-700/50 bg-slate-900/50"
                    : "border-slate-800 bg-slate-900/30 opacity-50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span
                      className={`h-2.5 w-2.5 rounded-full flex-shrink-0 ${
                        agent.online ? "bg-green-400 shadow-sm shadow-green-400/50" : "bg-slate-600"
                      }`}
                    />
                    <div>
                      <div className="text-sm font-medium text-white">{agent.name}</div>
                      <div className="text-xs text-slate-500">
                        {agent.ip} &middot; {new Date(agent.last_seen).toLocaleString("zh-CN")}
                      </div>
                    </div>
                  </div>
                  <span
                    className={`rounded-lg border px-2 py-0.5 text-xs font-medium ${
                      agent.online
                        ? "border-green-500/30 bg-green-500/15 text-green-400"
                        : "border-slate-600 bg-slate-800 text-slate-500"
                    }`}
                  >
                    {agent.online ? "在线" : "离线"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
