一、前言
！！！Agent，把天才 AI 变成一个能干活的人 ！！！
如果说 LLM 大模型是一个天才引擎，那么 Agent 就是很多无形的手，去控制这个天才引擎完成各种各样的工作和流程，替人类真正的干好活。
Agent 圈的主流产品/框架，如同百家争鸣般，赛道分化明显、定位泾渭分明：

有开箱即用的，可本地部署、多渠道接入的个人助手产品，最典型的就是 OpenClaw🦞
有适合生产落地的底层 Agent 编排框架，面向开发者/企业，自研复杂多智能体，比如：LangGraph
有高度产品化，内置于大厂应用；深度绑定自家模型，拥有工具调用、代码工程、终端任务能力的Agent协作平台。比如大家都在用的：Claude Code、Gemini、Codex


下面我们就深入的学习下这些 Agent 的核心能力和应用场景！

二、概览





























流派产物形态应用场景代表开箱即用型可部署的完整应用个人 / 团队 Agent 助手OpenClaw、ZeroClaw、Dify编排框架SDK / 库自研复杂多智能体LangGraph、CrewAI产品工具型CLI / IDE开发者编码、终端自动化Claude Code、Codex、Gemini Cli









































功能定位集成成本控制粒度使用难度扩展性安全性开箱即用型端到端任务执行中中低中高编排框架自建Agent编排高高高高高产品工具型工程现场协作低低极低低中
本文我们核心了解：OpenClaw、ZeroClaw、LangGraph、Codex、ClaudeCode
三、成品化 Agent 应用
这类 Agent 的特点是：你不需要写代码，部署好就能用。它们是完整的应用，开箱即用。
1. OpenClaw 🦞（368k★）
核心亮点

本地优先的 AI 网关：所有数据留在本地，隐私可控
25+ IM 平台接入，意味着你可以在社交软件上直接颁发指令：微信、QQ、飞书、iMessage、WhatsApp、Telegram、…… 几乎是全渠道触达
语音能力：macOS/iOS 支持唤醒词，Android 支持连续语音对话（ElevenLabs + 系统 TTS）
Live Canvas：Agent 驱动的可视化工作台（A2UI），不只是聊天框
多 Agent 路由：不同渠道可以路由到不同 Agent workspace，互相隔离

部署步骤
bash 体验AI代码助手 代码解读复制代码# 安装（Node.js 22.14+ / 推荐 24）
npm install -g openclaw@latest

# 引导式初始化（选模型 provider、接入渠道、配安全）
openclaw onboard --install-daemon

# 检查配置健康度
openclaw doctor

支持 npm / pnpm / bun，也支持 Nix 和 Docker 部署。
不挑模型 Provider —— 用你偏好的旗舰模型（Claude / GPT / Gemini / DeepSeek等）。
安全机制

DM 配对：陌生人发消息需要输入配对码才能与 Agent 交互
会话隔离：非主会话强制在沙箱中运行
openclaw doctor：一键审计配置安全性

常见玩法

全渠道个人助手：日程、邮件、待办、知识库问答，只要在IM平台上 @它就行
团队自动化 Bot：监听 GitHub / GitLab 事件 → 自动处理 → 群里汇报


总结：OpenClaw 是"Agent 界的 Homebrew" —— 生态决定了它能干多少事，本地优先保证了你的数据不出门。

2. ZeroClaw 🦀（31k★）
核心亮点

单 Rust 二进制：极致轻量，最小内核仅 6.6MB，冷启动极快
安全第一：默认 supervised 模式，OS 级沙箱（Linux Landlock / Bubblewrap / macOS Seatbelt / Docker），每次工具调用都有密码学签名收据，可审计
20+ 模型 Provider：Anthropic、OpenAI、Ollama、任何 OpenAI 兼容端点，支持 fallback 链和智能路由
硬件 IoT 集成：GPIO / I2C / SPI / USB，支持树莓派、STM32、Arduino、ESP32
SOP 引擎：事件驱动的标准操作流程（MQTT / Webhook / Cron / 外设触发），支持审批门和可恢复执行

部署步骤
bash 体验AI代码助手 代码解读复制代码# 一键安装
curl -fsSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/master/install.sh | bash

# 或从源码编译（支持自定义 features）
git clone https://github.com/zeroclaw-labs/zeroclaw.git
cd zeroclaw && ./install.sh --source --features "telegram,ollama,gpio"

# 最小安装（仅内核，6.6MB）
./install.sh --minimal

配置文件：~/.zeroclaw/config.toml，单文件可以管理全部配置，非常方便。
技术架构

应用场景

边缘 AI / IoT：在树莓派上 7×24 跑 Agent，通过 GPIO 控制硬件
高安全环境：密码学收据 + OS 沙箱，适合金融 / 医疗合规场景
终端设备： Windows、Android（ZeroClaw-Android）整机设备的 Agent 总控


ZeroClaw 是"Agent 界的嵌入式 Linux"——极致轻量 + 硬件级安全 + IoT 原生，在资源受限环境里它是唯一选择。

3.OpenClaw vs ZeroClaw













































维度OpenClaw 🦞ZeroClaw 🦀语言/运行时Node.jsRust 单二进制最小体积~100MB+6.6MB生态规模368k★，ClawHub 技能丰富31k★，兼容部分 OpenClaw Skills安全模型DM 配对 + 沙箱密码学收据 + OS 级沙箱硬件支持无GPIO/I2C/SPI/USB适合场景个人/团队全渠道助手终端设备设备 / IoT / 高安全环境WindowsWSL2WSL2

选型建议：资源充足、追求生态 → OpenClaw；资源受限、安全优先、要碰硬件 → ZeroClaw。

4. 插入讲解下，最近很火的 Hermes 框架
Hermes Agent（132k★）
Nous Research 出品—— "The Agent That Grows With You" 。
核心理念：Agent 不该是静态的，它的 Skills、Prompts、代码应该随使用持续自我优化，成长学习。
技术框架
核心抽象：

Skills（程序记忆） ：Agent 完成复杂任务后自动提取可复用 Skill，下次直接调用
Persistent Memory：用户画像 + 会话历史 + 长期知识，跨会话保留
Subagent 并行：spawn 隔离子 Agent 并行处理子任务
Cron 调度器：内置定时任务，Agent 可自主设定周期性工作
六种执行后端：Local / Docker / SSH / Daytona / Singularity / Modal

技术特点和优势

✅ 自我进化的 Skills：任务完成后自动创建 Skill，使用中自动改进
✅ Self-evolution：DSPy + GEPA（遗传帕累托提示进化，ICLR 2026 Oral），纯 API 调用无需 GPU，单次 $2-10
✅ 模型无关：OpenRouter 200+ 模型、OpenAI、Anthropic、NVIDIA NIM、Ollama
✅ 多平台网关：Telegram / Discord / Slack / WhatsApp / Signal / Email，单进程多渠道
✅ 40+ 内置工具 + 原生 MCP 扩展
✅ FTS5 会话搜索：全文检索 + LLM 摘要
⚠️ Self-evolution 仍在早期：Phase 1 已实现，Phase 2-5 规划中

安装和上手
bash 体验AI代码助手 代码解读复制代码# 一键安装
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc

# 交互式配置
hermes model    # 选择 LLM provider
hermes tools    # 配置可用工具
hermes setup    # 完整设置向导

# 启动
hermes          # CLI 聊天
hermes gateway  # 多渠道网关

Self-evolution 工作原理
markdown 体验AI代码助手 代码解读复制代码日常使用 → 完成任务 → 自动创建/改进 Skill
    ↓
触发 Self-evolution（手动或定时）
    ↓
DSPy 收集反馈 → GEPA 遗传算法搜索最优方案
    ↓
帕累托筛选（准确性 × 效率 × 成本）
    ↓
最优变体替换原 Skill → Agent 变得更聪明


适合的场景

持续优化的 AI 助手：越用越顺手，不需要手动调 prompt
多渠道运营：一个进程同时服务多个平台
Serverless 弹性：Modal/Daytona 按需休眠
研究探索：Self-evolution 本身是很好的研究工具


Hermes 是"会长大的 Agent"——你用它，它也在学你。Self-evolution 是它最大的护城河。

四、Agent 编排底层框架
这类框架解决的核心问题是：我要在自己的产品里造一个 Agent，但不想从零实现调度、状态管理、工具注册这些脏活。
换言之：你的业务逻辑才是核心，框架帮你搞定"让 AI 按流程干活"这件事。
1. LangGraph（31.2k★）
LangChain 团队出品，灵感来自 Google Pregel、Apache Beam 和 NetworkX——用 有向图 来编排 Agent 的工作流。控制粒度最细的 Agent 框架，没有之一。
技术框架
三个核心抽象：

Node（节点） ：每个节点是一个处理步骤——LLM 调用、工具执行、或任何 Python/TS 函数
Edge（边） ：节点之间的转换逻辑，支持条件路由
State（状态） ：跨节点共享的上下文，自动持久化，进程挂了也能从断点恢复

语言支持：Python（langgraph）+ TypeScript（langgraphjs）双版本。
技术特点和优势

✅ 显式可控：每个决策分支都是代码里的一条边，不存在"LLM 自己决定下一步"的黑盒
✅ 持久化执行：State 自动持久化到 Postgres / Redis / SQLite，进程崩溃可从 Checkpoint 恢复
✅ Human-in-the-loop：任意节点可插入人工审批，Agent 暂停等人确认后继续
✅ Time-travel 调试：回溯到任意历史 State 快照，重放执行路径
✅ 可观测性：深度集成 LangSmith，每一步 token 消耗、延迟、决策路径全可追踪
✅ 长期记忆：支持短期工作记忆 + 跨会话长期持久记忆
⚠️ 学习曲线陡：StateGraph / MessageGraph / Pregel 多种抽象，新手容易迷失
⚠️ 生态绑定：虽然可独立使用，但强引导走 LangChain + LangSmith 全家桶

典型代码示例
python 体验AI代码助手 代码解读复制代码from langgraph.graph import StateGraph, END
from typing import TypedDict

# 1. 定义状态
class AgentState(TypedDict):
    messages: list
    next_action: str

# 2. 定义节点函数
def analyze(state: AgentState) -> AgentState:
    ...

def execute(state: AgentState) -> AgentState:
    ...

# 3. 组装图
graph = StateGraph(AgentState)
graph.add_node("analyze", analyze)
graph.add_node("execute", execute)
graph.add_node("review", human_review)

# 4. 条件路由
graph.set_entry_point("analyze")
graph.add_edge("analyze", "execute")
graph.add_conditional_edges(
    "execute",
    lambda s: s["next_action"] == "need_review",
    {True: "review", False: END}
)

# 5. 编译（带持久化）
app = graph.compile(checkpointer=PostgresSaver(...))

接入流程
 体验AI代码助手 代码解读复制代码需求分析 
　↓
定义 State Schema 
　↓
编写 Node 函数 
　↓
定义 Edge 路由逻辑 
　↓
组装 StateGraph 
　↓
配置 Checkpointer（Postgres/Redis）
　↓
部署（LangGraph Cloud / 自托管）
　↓
接入 LangSmith 监控

适合的场景

企业级审批流程：贷款审批、内容审核、风控决策——每一步可追溯
客服系统：意图识别 → 检索 → 工具调用 → 人工升级，精确控制
数据处理 Pipeline：ETL + AI 分析 + 人工确认的混合流程
多步推理：需要 Human-in-the-loop 的复杂分析场景


LangGraph 是"Agent 界的状态机" —— 你画什么图，Agent 就走什么路。确定性最强，学习成本也最高。

五、内置 Agent 能力的大厂应用
这是研发同学最熟悉的，我们日常就在用 Codex、Claude Code、Gemini 等进行AI编码。
这些工具都深度绑定自家模型，内置了很垂类的任务规划、工具调用终端运维等 Agent 场景，无需依赖第三方框架即可直接使用智能体能力。
本质上，这些工具自带 Agent —— 且通过 MCP 协议，你的项目还能反向调用它们的能力。
1. Codex（80k★）
定位：OpenAI 开源的终端 Agent，"Lightweight coding agent that runs in your terminal"。
安装方式：
bash 体验AI代码助手 代码解读复制代码npm install -g @openai/codex
# 直接下载桌面应用也可以

使用最佳实践：

全自动模式：codex "重构这个函数并加上单测" → Agent 自动规划、修改、验证
审批模式（推荐） ：每一步操作需确认后才执行，适合生产代码
沙箱隔离：所有文件操作在沙箱内执行，不会直接污染工作目录

模型支持：

默认 GPT-4.5（推荐）
支持 o3、o4-mini 等推理模型
通过环境变量可切换模型：OPENAI_MODEL=o3 codex "..."

多会话管理：

支持 --resume 恢复上次会话
项目级上下文：自动读取 AGENTS.md / codex.md 作为项目指令

MCP / Skills 管理：

原生支持 MCP（Model Context Protocol），可接入外部工具
通过 codex.md 配置项目级 instructions 和工具权限
支持自定义 approval 规则：哪些操作自动执行、哪些需审批

2. Claude Code（120k★）
定位：Anthropic 官方 CLI Agent，目前生态最完整、社区最活跃的编码 Agent。
安装方式：
bash 体验AI代码助手 代码解读复制代码npm install -g @anthropic-ai/claude-code

使用最佳实践：

Plan → Execute 分离：复杂任务先让它出计划（/plan），确认后再执行
Sub-agent 并行：大任务自动拆分成多个子 Agent 并行处理
Skills 系统：把常用操作封装成 Skill，一键复用（如"写飞书文档"、"生成 PR"）

模型支持：

默认 Claude Opus 4（最强推理）
支持 Sonnet 4 / Haiku 4（快速模式 /fast）
通过 /model 命令或 CLAUDE_MODEL 环境变量切换

多会话管理：

自动上下文压缩：对话无限长，系统自动管理
/resume 恢复历史会话
支持多 workspace 并行：每个项目独立上下文
后台 Agent：run_in_background 让 Agent 在后台跑长任务

MCP / Skills 管理：

MCP 双向通道：

作为 MCP Client：接入飞书、GitHub、数据库等外部工具
作为 MCP Server：让其他应用调用 Claude Code 的能力（读代码、改文件、跑命令）


Skills 生态：.claude/skills/ 目录管理项目级技能
权限体系：.claude/settings.json 精细控制工具权限
Hooks：在工具调用前后自动执行自定义脚本

3. Codex vs Claude Code


















































维度CodexClaude Code开源程度完全开源部分开源（CLI 开源，模型闭源）模型绑定OpenAI 系（GPT-4.1 / o3）Anthropic 系（Opus / Sonnet）执行模式沙箱优先直接执行 + 权限审批多 Agent单 AgentSub-agent 并行委派MCP 生态支持，较新最完整，双向通道Skillscodex.md 配置目录级 skill 系统社区活跃度高极高（120k★）适合场景想用 GPT 系模型 + 沙箱安全优先复杂工程任务 + 生态整合

Codex 胜在开源透明 + 沙箱安全Claude Code 胜在生态完整 + 多 Agent 编排选模型偏好先，再选工具。

六、总结 ➡️ 玩转 Agent
可以根据以下思路去选择要怎么使用 Agent ：

我只想验证一个想法 → openClaw / zeroClaw
我要把 AI 流程嵌进现有业务系统 → LangGraph
我每天写代码，想让 AI 帮我干活 → Claude Code / Codex

实际上肯定是混着用的：

openClaw 探索一些新的咨询 ➡️ LangGraph支撑生产业务 ➡️ 使用 codex 或 cc，让 AI 帮我们上班

回过头看 AI 大模型一开始的模样: 基础的一问一答。
3 年时间过去，AI 能在各行各业深入落地，Workflow + Agent 功不可没。
所以，别再简单的用豆包、ds 查问题了。
把工具用起来，来编排任务驱动 AI 干活，解放我们自己的生产力！
