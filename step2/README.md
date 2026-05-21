# AI 素材审核助手 · Step 2 完整系统

> 从个人工具到团队级产品，支持 Web 上传、AI 自动审核、云端存储、管理后台

## 功能特性

- 🌐 **Web 上传页面** - 达人自助上传素材，无需人工介入
- 🤖 **AI 自动审核** - 定时扫描新素材，自动调用 Claude 进行合规性审核
- 📧 **邮件自动通知** - 审核结果自动发送给达人和运营团队
- ☁️ **云端存储** - 支持腾讯云 COS、阿里云 OSS
- 📊 **管理后台** - 数据统计、素材管理、审核记录、调度器控制

## 快速开始

### 1. 安装依赖

```bash
cd step2
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.py` 或设置环境变量：

```bash
# AI 审核配置
export DMXAPI_API_KEY="your-api-key"
export DMXAPI_BASE_URL="https://www.dmxapi.cn"
export CLAUDE_MODEL="kimi-k2.6"

# 邮件配置
export SENDER_EMAIL="your-email@foxmail.com"
export SMTP_HOST="smtp.exmail.qq.com"
export SMTP_USER="your-email@foxmail.com"
export SMTP_PASS="your-smtp-auth-code"

# 管理后台账号
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="your-secure-password"

# 云存储配置（可选）
export USE_CLOUD_STORAGE="false"  # 先用本地存储测试
```

### 3. 启动服务

```bash
# 开发环境
python app.py

# 生产环境
python app.py --prod
```

### 4. 访问

- 上传页面：http://localhost:8080/
- 管理后台：http://localhost:8080/admin

## 部署到服务器

### 方式一：直接运行（开发/测试）

```bash
# 后台运行
nohup python app.py --prod > logs/app.log 2>&1 &

# 检查状态
ps aux | grep app.py
tail -f logs/app.log
```

### 方式二：使用 systemd（推荐用于生产环境）

创建服务文件 `/etc/systemd/system/ai-reviewer.service`：

```ini
[Unit]
Description=AI Material Reviewer - Step 2
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/step2
ExecStart=/usr/bin/python3 /path/to/step2/app.py --prod
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-reviewer
sudo systemctl start ai-reviewer

# 查看状态
sudo systemctl status ai-reviewer
```

### 方式三：使用 Docker（可选）

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "app.py", "--prod"]
```

构建和运行：

```bash
docker build -t ai-reviewer .
docker run -d -p 8080:8080 \
  -e DMXAPI_API_KEY="your-key" \
  -e SENDER_EMAIL="your-email@foxmail.com" \
  -e SMTP_PASS="your-auth-code" \
  -e ADMIN_PASSWORD="secure-password" \
  ai-reviewer
```

## 项目结构

```
step2/
├── app.py              # 主入口程序
├── config.py           # 配置文件
├── database.py         # 数据库模块（SQLite）
├── cloud_storage.py    # 云存储模块（COS/OSS）
├── review_scheduler.py # AI 审核调度器
├── email_sender.py     # 邮件发送模块
├── routes.py           # Web 路由
├── requirements.txt    # 依赖列表
├── templates/          # 前端模板
│   ├── upload.html     # 上传页面
│   ├── login.html     # 登录页面
│   ├── dashboard.html # 管理后台首页
│   ├── materials.html # 素材管理页
│   ├── reviews.html   # 审核记录页
│   └── material_detail.html # 素材详情页
├── uploads/            # 上传文件目录
├── reports/            # 审核报告目录
├── logs/               # 日志目录
└── review.db           # SQLite 数据库
```

## API 接口

### 认证

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 登录 |
| `/api/auth/logout` | POST | 登出 |
| `/api/auth/status` | GET | 检查登录状态 |

### 素材管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload` | POST | 上传素材 |
| `/api/materials` | GET | 获取素材列表 |
| `/api/materials/<id>` | GET | 获取素材详情 |
| `/api/materials/<id>` | DELETE | 删除素材 |
| `/api/materials/<id>/review` | POST | 手动触发审核 |

### 审核

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/reviews` | GET | 获取审核记录 |
| `/api/reviews/<material_id>` | GET | 获取审核结果 |

### 调度器

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/scheduler/status` | GET | 调度器状态 |
| `/api/scheduler/start` | POST | 启动调度器 |
| `/api/scheduler/stop` | POST | 停止调度器 |
| `/api/scheduler/trigger` | POST | 手动触发审核 |

### 统计

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/statistics` | GET | 获取统计数据 |

## 数据库表结构

### materials（素材表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| filename | TEXT | 文件名 |
| original_filename | TEXT | 原始文件名 |
| file_path | TEXT | 本地路径 |
| cloud_path | TEXT | 云端路径 |
| file_size | INTEGER | 文件大小 |
| mime_type | TEXT | MIME 类型 |
| uploader_email | TEXT | 上传者邮箱 |
| uploader_name | TEXT | 上传者昵称 |
| upload_time | TEXT | 上传时间 |
| status | TEXT | 状态 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### reviews（审核记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| material_id | INTEGER | 素材 ID |
| filename | TEXT | 文件名 |
| reviewer_result | TEXT | 审核结果 |
| violations | TEXT | 违规条款（JSON） |
| suggestions | TEXT | 修改建议（JSON） |
| notes | TEXT | 备注 |
| raw_response | TEXT | AI 原始回复 |
| review_time | TEXT | 审核时间 |
| reviewer_model | TEXT | 审核模型 |
| email_sent | INTEGER | 邮件已发送 |
| email_sent_time | TEXT | 邮件发送时间 |

## 环境变量参考

```bash
# 服务器配置
export APP_HOST="0.0.0.0"
export APP_PORT="8080"
export APP_DEBUG="false"

# AI 审核配置
export DMXAPI_API_KEY="your-api-key"
export DMXAPI_BASE_URL="https://www.dmxapi.cn"
export CLAUDE_MODEL="kimi-k2.6"

# 邮件配置
export SENDER_EMAIL="your-email@foxmail.com"
export SENDER_NAME="AI 素材审核助手"
export SMTP_HOST="smtp.exmail.qq.com"
export SMTP_PORT="465"
export SMTP_USER="your-email@foxmail.com"
export SMTP_PASS="your-smtp-auth-code"
export OPERATION_TEAM_EMAIL="operation@example.com"

# 管理后台认证
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="your-secure-password"

# 云存储配置
export USE_CLOUD_STORAGE="false"
export COS_PROVIDER="tencent"
export TENCENT_SECRET_ID="your-secret-id"
export TENCENT_SECRET_KEY="your-secret-key"
export TENCENT_COS_REGION="ap-guangzhou"
export TENCENT_COS_BUCKET="your-bucket"

# 审核调度配置
export ENABLE_AUTO_REVIEW="true"
export REVIEW_INTERVAL="5"
```

## 安全建议

1. **修改默认密码**：首次部署务必修改 `ADMIN_PASSWORD`
2. **使用 HTTPS**：生产环境建议使用 Nginx 反向代理并启用 HTTPS
3. **限制上传大小**：配置文件中的 `MAX_FILE_SIZE_MB` 限制
4. **定期备份**：定期备份 `review.db` 数据库文件

## 故障排查

### 服务无法启动

```bash
# 检查端口占用
netstat -tlnp | grep 8080

# 查看错误日志
tail -f logs/app.log
```

### 审核不自动执行

```bash
# 检查调度器是否启动
curl http://localhost:8080/api/scheduler/status

# 手动触发审核
python app.py --trigger-review
```

### 邮件发送失败

```bash
# 检查 SMTP 配置
# 确认授权码正确（不是登录密码）
# 确认网络可以访问 SMTP 服务器
```

## 许可证

MIT License
