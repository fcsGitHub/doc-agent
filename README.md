# 文档智能生产与审核平台

基于 LLM 的文档智能生产与多角色审核平台。支持文档自动生成、多角色审核流程、语义搜索及版本管理。

## 前置要求

- [Docker](https://www.docker.com/) >= 24.0
- [Docker Compose](https://docs.docker.com/compose/) >= 2.20

## 快速开始

```bash
# 1. 复制环境变量文件并配置 LLM API Key
cp .env.example .env
# 编辑 .env，填入你的 LLM_API_KEY

# 2. 启动所有服务
docker compose up -d

# 3. 查看服务状态
docker compose ps
```

## 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:3000 | Next.js Web 界面 |
| 后端 API | http://localhost:8000 | FastAPI 接口 |
| 数据库 | localhost:5432 | PostgreSQL + pgvector |

## 架构概览

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Frontend   │────▶│   Backend    │────▶│    PostgreSQL     │
│  Next.js     │     │  FastAPI     │     │  + pgvector       │
│  :3000       │     │  :8000       │     │  :5432            │
└──────────────┘     └──────────────┘     └──────────────────┘
```

- **Frontend** — Next.js 14 App Router，提供文档编辑、审核界面
- **Backend** — FastAPI + LiteLLM，处理文档生成、审核逻辑、语义搜索
- **PostgreSQL** — pgvector 扩展，支持向量存储与语义检索

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接字符串 | `postgresql+asyncpg://docagent:docagent@localhost:5432/docagent` |
| `LLM_API_KEY` | LLM API 密钥 | — |
| `LLM_API_BASE` | LLM API 基础 URL | `https://api.openai.com/v1` |
| `LLM_DEFAULT_MODEL` | 默认生成模型 | `gpt-4o-mini` |
| `LLM_REVIEW_MODEL` | 审核模型 | `gpt-4o` |
| `LLM_EMBED_MODEL` | 向量嵌入模型 | `text-embedding-3-small` |
| `LITELLM_MOCK` | 是否使用 Mock LLM（离线/测试模式） | `false` |
| `SEED_DEMO_DATA` | 启动时是否加载示例数据 | `true` |
| `BACKEND_CORS_ORIGINS` | CORS 允许的前端地址 | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | 前端访问的后端 API 地址 | `http://localhost:8000` |

## 项目结构

```
doc-agent/
├── backend/          # FastAPI 后端
├── frontend/         # Next.js 前端
├── e2e/              # 端到端测试
├── scripts/          # 工具脚本
├── docker-compose.yml
├── .env.example
└── README.md
```

## 开发

```bash
# 查看日志
docker compose logs -f backend

# 重建服务
docker compose up --build

# 停止所有服务
docker compose down

# 停止并清除数据
docker compose down -v
```
