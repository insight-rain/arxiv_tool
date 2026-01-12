# arXiv AI Reader - 项目工作流程与文档总结

## 📋 项目概述

**arXiv AI Reader** 是一个自动化的学术论文获取、分析和导出系统，使用 DeepSeek AI 对 arXiv 论文进行智能筛选和深度分析。

### 核心特性
- 🔄 自动从 arXiv 爬取论文
- 🤖 两阶段 AI 分析（快速筛选 + 深度分析）
- 📝 自动导出高评分论文为 Markdown
- ☁️ 自动上传到 GitHub Pages
- 📅 支持自定义日期范围
- 🎯 智能关键词过滤

---

## 🔄 完整工作流程

### 1. 启动流程 (`start.sh`)

```bash
./start.sh [start_date] [end_date] [options]
```

**启动步骤：**

1. **配置生成**
   - 删除旧的 `backend/data/config.json`
   - 从 `backend/default_config.py` 重新生成配置
   - 如果提供了日期参数，使用自定义日期范围
   - 否则使用默认日期（从 `models.py` 读取）

2. **静态资源构建**
   - 运行 `build_static.py`
   - 生成带缓存破坏的静态文件到 `frontend_dist/`

3. **服务器启动**
   - 启动 FastAPI 后端服务器（默认端口 5000）
   - 启动后台任务（自动爬取和分析）

4. **可选：导出功能**
   - 如果使用 `--export` 参数，会在启动前导出论文
   - 导出后自动上传到 GitHub（除非使用 `--no-upload`）

### 2. 论文爬取流程 (`fetcher.py`)

**后台自动执行（每 5 分钟一次）：**

```
1. 读取 config.json 获取日期范围
   ↓
2. 查询 arXiv API（按日期范围）
   - cs.RO (Robotics)
   - cs.AI (Artificial Intelligence)
   - cs.CV (Computer Vision)
   - cs.LG (Machine Learning)
   - cs.CL (Computation and Language)
   - cs.NE (Neural and Evolutionary Computing)
   ↓
3. 对每个论文：
   - 检查是否已存在（避免重复）
   - 下载 HTML 版本
   - 提取预览文本（摘要 + 前 1500 字符）
   - 创建 Paper 对象
   - 保存到 backend/data/papers/{arxiv_id}.json
   ↓
4. 触发分析任务（异步）
```

### 3. 两阶段分析流程 (`analyzer.py`)

#### Stage 1: 快速筛选

**目标：** 快速判断论文相关性，避免对无关论文进行昂贵分析

```
输入：论文预览文本（~2000 字符）
   ↓
DeepSeek API 分析
   ↓
输出：
- is_relevant: bool (是否相关)
- relevance_score: float (0-10 评分)
- extracted_keywords: List[str] (提取的关键词)
- one_line_summary: str (一句话总结)
   ↓
保存到 JSON 文件
```

**过滤规则：**
- 包含 `negative_keywords` → 自动标记为不相关（score=1）
- `relevance_score >= min_relevance_score_for_stage2` (默认 6.0) → 进入 Stage 2

#### Stage 2: 深度分析

**目标：** 对高相关性论文进行详细分析

```
输入：完整论文内容（HTML）
   ↓
1. 生成详细摘要（200-300 字中文）
   ↓
2. 回答预设问题（使用 KV 缓存优化）
   - 核心创新点
   - 方法框架
   - 实验结果
   - 局限性分析
   ↓
输出：
- detailed_summary: str
- qa_pairs: List[QAPair]
   ↓
保存到 JSON 文件
```

**KV 缓存优化：**
- 固定前缀：`system_prompt + paper_content`
- 只改变问题部分
- 大幅降低 API 成本

### 4. 自动导出流程 (`exporter.py`)

**触发时机：**
- 分析完成后自动触发
- 手动通过 API 或命令行触发

**导出流程：**

```
1. 读取所有论文（从 backend/data/papers/）
   ↓
2. 加载 config.json 获取日期范围
   ↓
3. 过滤论文：
   - relevance_score >= min_score (默认 3.0)
   - published_date 在日期范围内
   ↓
4. 按分数从高到低排序
   ↓
5. 生成 Markdown 文件：
   - 文件名：high_score_papers_YYYYMMDD_HHMMSS.md
   - 包含所有论文的完整信息
   - 保存到 backend/data/markdown_export/
   ↓
6. 自动上传到 GitHub（如果启用）
```

### 5. GitHub 上传流程 (`upload_to_github.sh`)

**自动执行（导出完成后）：**

```
1. 检查最新的 Markdown 文件
   ↓
2. 克隆/更新 GitHub 仓库
   - 仓库：insight-rain/insight-rain.github.io
   - 本地目录：github_pages/
   ↓
3. 复制 Markdown 文件到仓库
   ↓
4. Git 操作：
   - git add {filename}
   - git commit -m "Auto-update: ..."
   - git push origin main/master
   ↓
5. 完成上传
```

---

## 📁 项目文件结构

```
Arxiv-AI-Reader-main-ori/
├── backend/                    # 后端代码
│   ├── api.py                 # FastAPI 服务器 + REST API
│   ├── fetcher.py             # arXiv 论文爬取
│   ├── analyzer.py            # DeepSeek AI 分析
│   ├── exporter.py            # Markdown 导出（新增）
│   ├── models.py              # 数据模型（Paper, Config, QAPair）
│   ├── default_config.py      # 默认配置
│   └── data/
│       ├── config.json        # 运行时配置（自动生成）
│       ├── papers/           # 论文 JSON 文件
│       │   └── {arxiv_id}.json
│       └── markdown_export/  # 导出的 Markdown 文件
│           └── high_score_papers_*.md
│
├── frontend/                   # 前端源码
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── frontend_dist/              # 构建后的前端文件
│
├── github_pages/               # GitHub Pages 仓库（自动克隆）
│   └── high_score_papers_*.md
│
├── start.sh                    # 启动脚本（增强版）
├── upload_to_github.sh         # GitHub 上传脚本（新增）
├── build_static.py             # 静态资源构建
├── requirements.txt           # Python 依赖
└── README.md                   # 项目文档
```

---

## 🚀 使用指南

### 基本启动

```bash
# 1. 设置 API Key
export DEEPSEEK_API_KEY="your-api-key"

# 2. 启动服务器（使用默认日期）
./start.sh

# 3. 启动服务器（指定日期范围）
./start.sh 2025-12-25 2025-12-31

# 4. 使用参数名指定日期
./start.sh --start-date 2025-12-25 --end-date 2025-12-31
```

### 导出功能

```bash
# 只导出，不启动服务器
./start.sh export

# 导出并指定最低分数
./start.sh export 3.0

# 导出并自定义文件名
./start.sh export 3.0 custom_name

# 导出但不上传 GitHub
./start.sh export 3.0 custom_name --no-upload

# 启动前先导出
./start.sh --export
```

### 自定义端口

```bash
# 使用 8000 端口
PORT=8000 ./start.sh
```

---

## ⚙️ 配置说明

### 配置文件位置

- **默认配置：** `backend/default_config.py`
- **运行时配置：** `backend/data/config.json`（自动生成）

### 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `filter_keywords` | `List[str]` | - | 正向关键词（用于相关性评分） |
| `negative_keywords` | `List[str]` | - | 负面关键词（自动拒绝） |
| `preset_questions` | `List[str]` | - | Stage 2 预设问题 |
| `system_prompt` | `str` | - | DeepSeek 系统提示词 |
| `start_date` | `str` | "2025-12-28" | 爬取开始日期 |
| `end_date` | `str` | "2025-12-29" | 爬取结束日期 |
| `fetch_interval` | `int` | 300 | 爬取间隔（秒） |
| `max_papers_per_fetch` | `int` | 100 | 每次爬取最大论文数 |
| `model` | `str` | "deepseek-chat" | DeepSeek 模型 |
| `temperature` | `float` | 0.3 | LLM 温度参数 |
| `max_tokens` | `int` | 2000 | 最大 token 数 |
| `concurrent_papers` | `int` | 10 | 并发分析论文数 |
| `min_relevance_score_for_stage2` | `float` | 6.0 | Stage 2 最低分数 |

### 修改配置

**方法 1：修改默认配置**
```bash
vim backend/default_config.py
# 下次启动时会重新生成 config.json
```

**方法 2：直接修改运行时配置**
```bash
vim backend/data/config.json
# 服务器会在下次爬取时读取新配置
```

**方法 3：通过 API**
```bash
curl -X PUT http://localhost:5000/config \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-12-25", "end_date": "2025-12-31"}'
```

---

## 📊 数据流程

### 论文数据流

```
arXiv.org
   ↓ (RSS Feed)
ArxivFetcher.fetch_latest()
   ↓
Paper 对象创建
   ↓
保存到 backend/data/papers/{id}.json
   ↓
DeepSeekAnalyzer.stage1_filter()
   ↓ (如果相关)
DeepSeekAnalyzer.stage2_qa()
   ↓
更新 JSON 文件
   ↓
MarkdownExporter.export()
   ↓
生成 Markdown 文件
   ↓
upload_to_github.sh
   ↓
GitHub Pages
```

### 文件存储

**论文数据：** `backend/data/papers/{arxiv_id}.json`
- 每个论文一个 JSON 文件
- 包含完整信息：元数据、分析结果、问答对

**导出文件：** `backend/data/markdown_export/high_score_papers_*.md`
- 带时间戳的文件名
- 包含所有高评分论文（按分数排序）

**GitHub 仓库：** `github_pages/`
- 自动克隆的 GitHub Pages 仓库
- 包含所有导出的 Markdown 文件

---

## 🔧 新增功能说明

### 1. Markdown 导出功能 (`exporter.py`)

**功能：**
- 自动筛选 `relevance_score >= 3.0` 的论文
- 按日期范围过滤（从 `config.json` 读取）
- 按分数从高到低排序
- 生成单个 Markdown 文件（包含所有论文）
- 文件名自动包含时间戳

**使用：**
```python
from exporter import MarkdownExporter

exporter = MarkdownExporter()
result = exporter.export(min_score=3.0)
```

### 2. GitHub 自动上传 (`upload_to_github.sh`)

**功能：**
- 自动克隆/更新 GitHub 仓库
- 复制最新的 Markdown 文件
- 自动提交并推送

**配置：**
- 仓库：`https://github.com/insight-rain/insight-rain.github.io.git`
- 本地目录：`github_pages/`

### 3. 日期范围支持

**功能：**
- 启动时通过命令行参数指定日期范围
- 自动更新 `config.json` 中的日期
- 导出时按日期范围过滤论文

**使用：**
```bash
./start.sh 2025-12-25 2025-12-31
```

### 4. 自动导出触发

**触发时机：**
- 分析完成后自动导出
- 深度分析完成后自动导出
- 导出后自动上传到 GitHub

---

## 🎯 关键设计原则

### 1. 文件系统作为数据库
- 每个论文一个 JSON 文件
- 无需数据库，易于备份和迁移
- 备份：`cp -r backend/data/ backup/`

### 2. 两阶段分析
- Stage 1：快速筛选（低成本）
- Stage 2：深度分析（仅高相关性论文）
- 节省 API 成本

### 3. KV 缓存优化
- 固定前缀：`system_prompt + paper_content`
- 只改变问题部分
- 大幅降低 API 调用成本

### 4. 异步处理
- 所有网络请求异步执行
- 并发分析多个论文
- 非阻塞后台任务

### 5. 日期范围过滤
- 爬取时按日期范围查询
- 导出时按日期范围过滤
- 确保数据一致性

---

## 📡 API 端点

### 论文相关

- `GET /papers` - 获取论文列表（支持分页、排序、筛选）
- `GET /papers/{id}` - 获取论文详情
- `POST /papers/{id}/ask` - 提问（非流式）
- `POST /papers/{id}/ask_stream` - 提问（流式响应）
- `POST /papers/{id}/star` - 收藏/取消收藏
- `POST /papers/{id}/hide` - 隐藏论文
- `POST /papers/{id}/update_relevance` - 手动更新相关性评分

### 配置相关

- `GET /config` - 获取配置
- `PUT /config` - 更新配置

### 系统相关

- `POST /fetch` - 手动触发爬取
- `GET /stats` - 获取统计信息
- `GET /search?q={query}` - 搜索论文或按 arXiv ID 获取

### 导出相关（新增）

- `POST /export/markdown?min_score=3.0&output_file=custom_name` - 导出 Markdown

---

## 🔍 故障排查

### 常见问题

1. **端口被占用**
   ```bash
   # 查看占用进程
   lsof -ti :5000
   
   # 使用不同端口
   PORT=8000 ./start.sh
   ```

2. **API 余额不足（402 错误）**
   - 检查 DeepSeek API 账户余额
   - 错误会自动跳过，不会导致程序崩溃

3. **找不到论文**
   - 检查日期范围是否正确
   - 确认 arXiv 上该日期有论文提交

4. **GitHub 上传失败**
   - 检查 Git 是否安装
   - 确认有仓库访问权限
   - 检查网络连接

5. **导出包含旧论文**
   - 已修复：导出时会按日期范围过滤
   - 确保 `config.json` 中的日期正确

---

## 📝 工作流程总结图

```
┌─────────────────────────────────────────────────────────┐
│                   启动流程 (start.sh)                    │
│  1. 生成 config.json（从 default_config.py）            │
│  2. 构建静态资源                                         │
│  3. 启动 FastAPI 服务器                                  │
│  4. 启动后台任务                                         │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │   后台爬取循环           │
        │  (每 5 分钟执行)         │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │   1. 从 arXiv 爬取论文   │
        │   2. 保存到 papers/     │
        │   3. 触发 Stage 1 分析   │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │   Stage 1: 快速筛选      │
        │   - 评分 (0-10)          │
        │   - 提取关键词            │
        │   - 一句话总结            │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │   分数 >= 6.0?           │
        └────────────┬────────────┘
                     │ 是
        ┌────────────▼────────────┐
        │   Stage 2: 深度分析      │
        │   - 详细摘要              │
        │   - 回答预设问题          │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │   自动导出 Markdown      │
        │   - 筛选 score >= 3.0   │
        │   - 按日期范围过滤        │
        │   - 生成带时间戳的文件    │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │   自动上传到 GitHub      │
        │   - 克隆/更新仓库        │
        │   - 提交并推送           │
        └─────────────────────────┘
```

---

## 📚 相关文档

- **README.md** - 项目主要文档
- **REFRESH_GUIDE.md** - 刷新指南（如果存在）
- **WORKFLOW.md** - 本文档（工作流程总结）

---

## 🎓 最佳实践

1. **定期检查 API 余额**
   - 避免因余额不足导致分析失败

2. **合理设置日期范围**
   - 不要设置过大的范围（会增加爬取时间）
   - 建议每次查询 1-7 天

3. **调整分析阈值**
   - `min_relevance_score_for_stage2` 越高，分析成本越低
   - 但可能错过一些相关论文

4. **定期备份数据**
   ```bash
   cp -r backend/data/ backup_$(date +%Y%m%d)/
   ```

5. **监控导出文件**
   - 检查 `backend/data/markdown_export/` 目录
   - 确认 GitHub 上传成功

---

## 🔄 更新日志

### 新增功能（本次更新）

1. ✅ **Markdown 导出功能**
   - 自动导出高评分论文
   - 按日期范围过滤
   - 文件名包含时间戳

2. ✅ **GitHub 自动上传**
   - 导出后自动上传
   - 支持跳过上传选项

3. ✅ **日期范围支持**
   - 启动时指定日期范围
   - 自动更新配置

4. ✅ **配置自动生成**
   - 每次启动自动重新生成 config.json
   - 支持命令行参数指定日期

5. ✅ **端口检测与处理**
   - 自动检测端口占用
   - 支持自定义端口

---

## 📞 技术支持

如有问题，请检查：
1. API Key 是否正确设置
2. 网络连接是否正常
3. 日期范围是否合理
4. 查看日志输出获取详细错误信息

