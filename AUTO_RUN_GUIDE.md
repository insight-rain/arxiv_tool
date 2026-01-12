# 自动运行和自动关闭功能使用指南

本文档说明如何在服务器上使用项目的自动运行和自动关闭功能。

## 📋 功能概述

项目支持两种运行模式：

1. **持续运行模式**（默认）：服务器持续运行，每5分钟自动抓取一次
2. **单次运行模式**（`--once`）：执行一次抓取和分析后自动退出

## 🚀 单次运行模式（自动关闭）

### 基本用法

```bash
# 使用默认日期范围，执行一次后退出
./start.sh --once

# 或者使用完整参数名
./start.sh --single-run
```

### 自动日期范围 + 单次运行（推荐）

```bash
# 自动计算日期范围（10天前到4天前，即7天范围），执行一次后退出
./start.sh --auto-date --once
```

### 自定义日期范围 + 单次运行

```bash
# 指定日期范围，执行一次后退出
./start.sh 2026-01-01 2026-01-07 --once

# 或使用参数名
./start.sh --start-date 2026-01-01 --end-date 2026-01-07 --once
```

### 通过环境变量启用

```bash
# 设置环境变量后启动
export SINGLE_RUN=1
./start.sh

# 或在一行中
SINGLE_RUN=1 ./start.sh
```

## ⚙️ 自动关闭机制详解

### 工作原理

当启用单次运行模式时，系统会：

1. **执行一次完整的工作流程**：
   ```
   抓取论文 → Stage 1分析 → Stage 2分析（如需要）→ 自动导出 → 自动上传GitHub
   ```

2. **等待所有任务完成**：
   - 在单次运行模式下，系统会**等待分析完成**（使用 `await` 而非异步任务）
   - 确保所有论文分析完成后再退出

3. **自动退出**：
   - 执行完成后，系统会打印 `✅ Single run completed!`
   - 等待2秒用于清理工作
   - 通过 `os.kill(os.getpid(), signal.SIGTERM)` 发送 SIGTERM 信号
   - uvicorn 服务器接收到信号后正常退出

### 代码实现位置

自动关闭逻辑在 `backend/api.py` 的 `background_fetcher()` 函数中：

```python
# 在单次运行模式下，等待分析完成
if single_run_mode:
    await analyze_papers_task(papers, config)

# 执行完成后退出
if single_run_mode:
    print(f"\n✅ Single run completed!")
    print(f"   All tasks finished. Exiting...")
    await asyncio.sleep(2)  # 给清理工作一些时间
    os.kill(os.getpid(), signal.SIGTERM)  # 发送退出信号
    return
```

### 错误处理

如果执行过程中出现错误，单次运行模式也会退出：

```python
except Exception as e:
    if single_run_mode:
        print(f"\n⚠️  Single run failed. Exiting...")
        os.kill(os.getpid(), signal.SIGTERM)
        return
```

## 🔄 在服务器上自动运行（定时任务）

### 方法1：使用 Cron（推荐）

编辑 crontab：

```bash
crontab -e
```

添加定时任务：

```bash
# 每天凌晨2点执行一次（自动计算日期范围）
0 2 * * * cd /path/to/Arxiv-AI-Reader-main-ori && export DEEPSEEK_API_KEY="your-api-key" && ./start.sh --auto-date --once >> /var/log/arxiv-reader.log 2>&1

# 每周一凌晨2点执行一次
0 2 * * 1 cd /path/to/Arxiv-AI-Reader-main-ori && export DEEPSEEK_API_KEY="your-api-key" && ./start.sh --auto-date --once >> /var/log/arxiv-reader.log 2>&1

# 每12小时执行一次（每天0点和12点）
0 0,12 * * * cd /path/to/Arxiv-AI-Reader-main-ori && export DEEPSEEK_API_KEY="your-api-key" && ./start.sh --auto-date --once >> /var/log/arxiv-reader.log 2>&1
```

**Cron 时间格式说明：**
```
分钟 小时 日 月 星期
*    *   *  *   *
```

### 方法2：使用 Systemd Timer（更现代的方式）

创建 systemd service 文件 `/etc/systemd/system/arxiv-reader.service`：

```ini
[Unit]
Description=Arxiv AI Reader Single Run
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/Arxiv-AI-Reader-main-ori
Environment="DEEPSEEK_API_KEY=your-api-key"
ExecStart=/usr/bin/bash /path/to/Arxiv-AI-Reader-main-ori/start.sh --auto-date --once
StandardOutput=journal
StandardError=journal
```

创建 systemd timer 文件 `/etc/systemd/system/arxiv-reader.timer`：

```ini
[Unit]
Description=Run Arxiv AI Reader Daily
Requires=arxiv-reader.service

[Timer]
# 每天凌晨2点执行
OnCalendar=daily
OnCalendar=02:00
# 如果系统关机错过执行时间，启动后立即执行一次
Persistent=true

[Install]
WantedBy=timers.target
```

启用和启动 timer：

```bash
sudo systemctl enable arxiv-reader.timer
sudo systemctl start arxiv-reader.timer
sudo systemctl status arxiv-reader.timer
```

查看执行历史：

```bash
sudo systemctl list-timers arxiv-reader.timer
sudo journalctl -u arxiv-reader.service -f
```

### 方法3：使用 Screen/Tmux（临时方案）

如果需要手动控制，可以使用 screen 或 tmux：

```bash
# 使用 screen
screen -dmS arxiv-reader bash -c "cd /path/to/project && export DEEPSEEK_API_KEY='your-key' && ./start.sh --auto-date --once"

# 使用 tmux
tmux new-session -d -s arxiv-reader "cd /path/to/project && export DEEPSEEK_API_KEY='your-key' && ./start.sh --auto-date --once"
```

## 📊 执行流程对比

### 持续运行模式（默认）

```
启动服务器
  ↓
每5分钟执行一次：
  ├─ 抓取论文（异步）
  ├─ Stage 1分析（异步）
  ├─ Stage 2分析（异步，如果分数>=6.0）
  └─ 自动导出和上传（异步）
  ↓
继续运行，等待下一次循环
```

### 单次运行模式（--once）

```
启动服务器
  ↓
执行一次：
  ├─ 抓取论文（同步等待）
  ├─ Stage 1分析（同步等待）
  ├─ Stage 2分析（同步等待，如果分数>=6.0）
  ├─ 自动导出和上传（同步等待）
  └─ 等待2秒清理
  ↓
发送 SIGTERM 信号
  ↓
服务器退出
```

## 💡 使用建议

### 1. 推荐使用场景

- ✅ **定期批量处理**：使用 cron 或 systemd timer + `--once` 模式
- ✅ **一次性分析**：手动执行 `./start.sh --auto-date --once`
- ✅ **CI/CD 集成**：在 CI 流水线中使用单次运行模式

### 2. 不推荐使用场景

- ❌ **需要持续访问 Web UI**：使用默认的持续运行模式
- ❌ **需要实时查看结果**：使用默认的持续运行模式

### 3. 最佳实践

1. **生产环境部署**：
   ```bash
   # 使用 systemd timer，每天自动运行
   # 不需要保持服务器一直运行
   ```

2. **开发测试**：
   ```bash
   # 使用默认模式，方便调试
   ./start.sh
   ```

3. **日志记录**：
   ```bash
   # 将输出重定向到日志文件
   ./start.sh --auto-date --once >> /var/log/arxiv-reader.log 2>&1
   ```

4. **环境变量管理**：
   ```bash
   # 使用 .env 文件或系统环境变量
   # 避免在脚本中硬编码 API Key
   export DEEPSEEK_API_KEY="your-key"
   ```

## 🔍 故障排查

### 问题1：单次运行模式没有退出

**可能原因**：
- 有未完成的异步任务
- 网络请求超时

**解决方案**：
- 检查日志查看是否有错误
- 增加超时设置
- 检查是否有死锁

### 问题2：Cron 任务没有执行

**检查步骤**：
```bash
# 检查 cron 服务是否运行
sudo systemctl status cron  # Ubuntu/Debian
sudo systemctl status crond  # CentOS/RHEL

# 检查 cron 日志
sudo tail -f /var/log/cron  # CentOS/RHEL
grep CRON /var/log/syslog   # Ubuntu/Debian

# 测试 cron 任务（使用绝对路径）
cd /absolute/path/to/project && ./start.sh --auto-date --once
```

### 问题3：权限问题

**解决方案**：
```bash
# 确保脚本有执行权限
chmod +x start.sh

# 确保使用正确的用户运行
# 在 crontab 中使用完整路径
```

### 问题4：环境变量未设置

**解决方案**：
```bash
# 在 crontab 中设置环境变量
0 2 * * * export DEEPSEEK_API_KEY="your-key" && cd /path/to/project && ./start.sh --auto-date --once

# 或使用 .env 文件
# 或使用系统级环境变量
```

## 📝 完整示例

### 示例1：每天自动运行（Cron）

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天凌晨2点执行）
0 2 * * * cd /home/user/Arxiv-AI-Reader-main-ori && export DEEPSEEK_API_KEY="your-api-key-here" && /usr/bin/bash ./start.sh --auto-date --once >> /home/user/logs/arxiv-reader-$(date +\%Y\%m\%d).log 2>&1
```

### 示例2：每周运行（Systemd Timer）

```ini
# /etc/systemd/system/arxiv-reader.timer
[Unit]
Description=Run Arxiv AI Reader Weekly
Requires=arxiv-reader.service

[Timer]
OnCalendar=weekly
OnCalendar=Mon 02:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 示例3：手动执行一次

```bash
# 设置环境变量
export DEEPSEEK_API_KEY="your-api-key"

# 执行一次（自动日期范围）
./start.sh --auto-date --once

# 或指定日期范围
./start.sh 2026-01-01 2026-01-07 --once
```

## 🎯 总结

- **单次运行模式**：使用 `--once` 或 `--single-run` 参数
- **自动关闭**：执行完成后通过 SIGTERM 信号正常退出
- **定时任务**：使用 cron 或 systemd timer 定期执行
- **推荐方案**：`./start.sh --auto-date --once` 配合 cron/systemd timer

这样就可以实现完全自动化的论文抓取和分析，无需手动干预！

