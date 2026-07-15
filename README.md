# ComplianceAudit

SKILL 驱动的合规用例审查系统。前端下发审查任务 → Agent 在用户本地对指定文件夹中的文档材料逐个执行合规 SKILL → 前端展示结果。

## 架构

```
Browser ──HTTP──► Backend (FastAPI, :8000) ◄──WebSocket── Agent (用户本地)
                       │   JSON 文件存储                       │
                       │   静态文件服务                         ├── opencode CLI
                       │                                      └── compliance_skills/
                  Agent 下载 ZIP                               
                 (/api/agent/download)                         
```

- **Backend**：FastAPI，提供 REST API + WebSocket + 前端静态文件
- **Agent**：Python 守护进程，连接后端 WebSocket，在本地执行合规审查
- **Frontend**：React + TypeScript + Vite + Tailwind CSS（构建到 `backend/static/`）

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动后端

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

或双击 `start.bat`

### 启动前端（开发模式）

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器跑在 `http://localhost:5173`，自动代理 API 到 8000 端口。

### 构建前端

```bash
cd frontend
npm run build
```

构建产物输出到 `backend/static/`，后端会直接提供静态文件服务。

### 部署 Agent

1. 浏览器打开 `http://<服务器地址>:8000`，进入 **Agent** 页面
2. 点击 **下载 Agent 包 (ZIP)**
3. 解压到目标机器，编辑 `agent.yaml` 中的 `server_url` 为服务器地址
4. 双击 `run_agent.bat` 启动 Agent

**前提**：目标机器需要安装 [opencode CLI](https://github.com/anomalyco/opencode)。

## 新增合规技能

在 `compliance_skills/` 下创建新目录，放入两个文件：

```
compliance_skills/<技能名>/
├── checker.yaml   # 技能元信息
└── SKILL.md       # AI 审查指令
```

**checker.yaml 示例**：

```yaml
name: my_skill
label: 我的合规技能
description: 描述这个技能检查什么
enabled: true
mode: opencode
```

**SKILL.md 示例**：

```markdown
# 我的合规技能

对目标文件夹中的文档进行以下检查：

## 审查要点
...

## 输出要求
审查完成后，以 JSON 格式输出结果：
{ "overall": "pass|fail", "checks": [...] }
```

添加后无需重启后端，前端自动轮询加载新技能。下载的 ZIP 包也会自动包含。

## 项目结构

```
ComplianceAudit/
├── backend/              # FastAPI 后端
│   ├── main.py           # 应用入口
│   ├── config.py         # 配置加载
│   ├── models.py         # Pydantic 数据模型
│   ├── registry.py       # 技能发现
│   ├── store.py          # JSON 文件存储
│   ├── static/           # 前端构建产物
│   └── api/
│       ├── agent.py      # WebSocket + Agent 注册
│       ├── auth.py       # 认证
│       ├── checkers.py   # 技能列表
│       ├── download.py   # Agent ZIP 下载
│       └── scan.py       # 任务 CRUD + 下发
├── agent/                # Agent 运行代码
│   ├── main.py           # WebSocket 客户端
│   ├── config.py         # Agent 配置
│   ├── server.py         # 命令处理
│   ├── runner.py         # 合规审查执行器
│   └── reporter.py       # HTTP 结果上报
├── compliance_skills/    # 合规技能定义
├── frontend/             # React 前端
├── config.yaml           # 后端配置
├── agent.yaml            # Agent 配置模板
├── requirements.txt      # Python 依赖
├── run_agent.bat         # Agent 启动脚本
├── start.bat             # 后端启动脚本
└── README.md
```

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python FastAPI + WebSocket |
| 存储 | JSON 文件（`data/tasks/`） |
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS |
| Agent | Python asyncio + websockets + httpx |
| AI 驱动 | opencode CLI (SKILL.md 作为系统指令) |
| 通信 | REST API + WebSocket (Agent ↔ Backend) |
