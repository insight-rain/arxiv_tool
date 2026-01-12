# 部署指南 / Deployment Guide

本文档说明如何将项目部署到服务器。

## 系统要求

- Python 3.8 或更高版本
- 至少 1GB RAM（推荐 2GB+）
- DeepSeek API Key

## 快速部署

### 1. 克隆项目

```bash
git clone <your-repository-url>
cd Arxiv-AI-Reader-main-ori
```

### 2. 创建虚拟环境（推荐）

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
export DEEPSEEK_API_KEY="your-api-key-here"
```

或者创建 `.env` 文件（如果使用环境变量管理工具）：

```bash
echo "DEEPSEEK_API_KEY=your-api-key-here" > .env
```

### 5. 启动服务

```bash
# 使用默认配置
./start.sh

# 或指定日期范围
./start.sh 2026-01-01 2026-01-07

# 或使用自定义端口
PORT=8000 ./start.sh
```

## 生产环境部署

### 使用 systemd (Linux)

创建 systemd 服务文件 `/etc/systemd/system/arxiv-reader.service`:

```ini
[Unit]
Description=Arxiv AI Reader Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/Arxiv-AI-Reader-main-ori
Environment="DEEPSEEK_API_KEY=your-api-key"
Environment="PORT=5000"
ExecStart=/path/to/venv/bin/python backend/api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl enable arxiv-reader
sudo systemctl start arxiv-reader
sudo systemctl status arxiv-reader
```

### 使用 supervisor

创建配置文件 `/etc/supervisor/conf.d/arxiv-reader.conf`:

```ini
[program:arxiv-reader]
directory=/path/to/Arxiv-AI-Reader-main-ori
command=/path/to/venv/bin/python backend/api.py
user=your-username
autostart=true
autorestart=true
stderr_logfile=/var/log/arxiv-reader.err.log
stdout_logfile=/var/log/arxiv-reader.out.log
environment=DEEPSEEK_API_KEY="your-api-key",PORT="5000"
```

启动服务：

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start arxiv-reader
```

### 使用 Docker（可选）

如果需要使用 Docker，可以创建 `Dockerfile` 和 `docker-compose.yml`（项目中已包含相关脚本）。

## 配置说明

1. **配置文件**: `backend/data/config.json` 会在启动时从 `backend/default_config.py` 自动生成
2. **数据目录**: 论文数据存储在 `backend/data/papers/` 目录
3. **导出目录**: Markdown 导出文件在 `backend/data/markdown_export/` 目录

## 常见问题

### 端口冲突

如果默认端口 5000 被占用，使用环境变量指定其他端口：

```bash
PORT=8000 ./start.sh
```

### API Key 未设置

确保设置了 `DEEPSEEK_API_KEY` 环境变量：

```bash
export DEEPSEEK_API_KEY="your-key"
echo $DEEPSEEK_API_KEY  # 验证
```

### 依赖安装问题

如果遇到依赖安装问题，确保使用最新版本的 pip：

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Python 版本问题

项目需要 Python 3.8+。检查版本：

```bash
python3 --version
```

## 更新项目

```bash
git pull origin main
pip install -r requirements.txt --upgrade
# 重启服务
```

## 备份数据

项目数据存储在 `backend/data/` 目录，建议定期备份：

```bash
tar -czf backup-$(date +%Y%m%d).tar.gz backend/data/
```

