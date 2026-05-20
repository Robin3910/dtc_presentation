# AI 素材审核助手 · Step 1 轻量 Demo

本地文件夹 + 单个脚本，跑通 AI 审核核心流程，无需任何外部依赖。

---

## 工作原理

```
达人素材（图片）  →  Python 脚本  →  Claude AI 审核  →  自动发邮件通知达人
```

## 目录结构

```
step1/
├── main.py              # 入口程序
├── config.py            # 配置文件（API Key / SMTP）
├── claude_client.py     # Claude AI 客户端
├── email_sender.py      # 邮件发送模块
├── brand_rules.md       # 品牌审核规范（可自定义）
├── requirements.txt     # Python 依赖
├── materials/          # ← 达人素材放这里
│   ├── user001@foxmail.com.png
│   └── user002@foxmail.com.png
└── reports/            # ← 生成的审核报告在这里
```

## 快速开始

### 1. 安装依赖

```bash
cd step1
pip install -r requirements.txt
```

### 2. 配置（编辑 config.py）

```python
# Claude API Key
CLAUDE_API_KEY = "sk-ant-xxxx"   # 从 https://console.anthropic.com/ 获取

# 邮件发件配置
SENDER_EMAIL = "your-email@foxmail.com"
SMTP_HOST    = "smtp.exmail.qq.com"   # QQ企业邮箱
SMTP_PORT    = 465
SMTP_USER    = "your-email@foxmail.com"
SMTP_PASS    = "your-smtp-auth-code"  # QQ邮箱的「授权码」
```

> **如何获取 QQ 邮箱授权码？**
> QQ 邮箱 → 设置 → 账户 → POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务 → 开启服务 → 生成授权码

### 3. 放入素材

将达人的素材图片放入 `materials/` 目录，**文件名格式为达人邮箱**：

```
materials/
├── user001@foxmail.com.png    ← 图片文件名就是达人邮箱
├── user002@foxmail.com.png
└── user003@foxmail.com.jpg
```

### 4. 运行

```bash
# 完整流程：审核 + 发邮件
python main.py

# 仅生成报告，不发邮件
python main.py --report-only

# 指定素材目录
python main.py --materials ./my_materials
```

---

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--report-only` | 仅生成报告，不发送邮件 |
| `--skip-review` | 跳过 AI 审核，用上次报告发邮件 |
| `--materials <path>` | 指定素材目录（默认 `materials/`） |
| `--to <email>` | 指定收件人邮箱 |
| `--rules <path>` | 指定品牌规范文件 |

---

## 运行效果

```
╔══════════════════════════════════════════════╗
║     AI 素材审核助手 · Step 1 轻量 Demo       ║
╚══════════════════════════════════════════════╝

📁 素材目录：.../step1/materials
📁 报告目录：.../step1/reports

📦 发现 11 份待审核素材：
   - user001@foxmail.com.png
   - user002@foxmail.com.png
   ...

[1/11] 正在审核：user001@foxmail.com.png → user001@foxmail.com
[2/11] 正在审核：user002@foxmail.com.png → user002@foxmail.com
...

==================================================
  审核结果摘要
==================================================
  ✅ 通过：8 份
  ⚠️ 需修改：2 份
  ❌ 违规：1 份

  通过率：72.7%
  总计：11 份素材

📄 报告已保存：.../step1/reports/review_report_20260520_230000.md
✉️  开始发送邮件通知...

✨ 所有流程执行完毕！
```

---

## 邮件预览

审核完成后，达人会收到一封美观的 HTML 邮件，包含审核结果汇总表格和每份素材的处理建议。

---

## 注意事项

- 图片文件名格式：**`名字@域名.com.png`**（如 `user001@foxmail.com.png`），程序会自动从中提取邮箱作为收件人
- 每次审核会调用 Claude API，**按 token 计费**，建议先用少量素材测试
- 审核规范可随时编辑 `brand_rules.md`，AI 会读取最新规范进行审核
- 报告保存在 `reports/` 目录，可随时查阅历史审核记录
