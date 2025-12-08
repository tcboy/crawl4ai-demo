# CUA Agent 示例项目

这是一个使用 [CUA 框架](https://github.com/trycua/cua) 创建 AI Agent 的示例项目。

## 什么是 CUA？

CUA (Computer-Use Agents) 是一个开源框架，用于构建能够通过视觉理解和动作执行来自主操作计算机的 AI 系统。与依赖选择器或 API 的传统自动化工具不同，CUA 使用视觉-语言模型来感知屏幕内容并推理界面交互。

## 快速开始

### 0. 检查 Python 版本

CUA 框架需要 **Python 3.12 或 3.13**（Python 3.14 目前不支持）。

```bash
# 检查当前 Python 版本
python3 --version

# 运行环境检查脚本（推荐）
python3 check_python_version.py
```

如果你的 Python 版本是 3.11 或更早，需要升级：

- **Ubuntu/Debian**: 运行 `bash upgrade_python.sh` 或查看 `PYTHON_UPGRADE_GUIDE.md`
- **macOS**: 使用 `brew install python@3.12` 或 `pyenv`
- **Windows**: 从 [Python 官网](https://www.python.org/downloads/) 下载安装程序

详细升级指南请查看 [PYTHON_UPGRADE_GUIDE.md](./PYTHON_UPGRADE_GUIDE.md)

### 1. 安装依赖

```bash
# 安装 Agent SDK
pip install cua-agent[all]

# 安装 Computer SDK
pip install cua-computer
```

### 2. 设置环境变量

创建 `.env` 文件并添加你的 API 密钥：

```bash
# OpenAI API 密钥（如果使用 OpenAI 模型）
OPENAI_API_KEY=your_openai_api_key

# Anthropic API 密钥（如果使用 Claude 模型）
ANTHROPIC_API_KEY=your_anthropic_api_key

# Cua Cloud API 密钥（如果使用云端计算机）
CUA_API_KEY=your_cua_api_key
```

### 3. 运行示例

```bash
python simple_agent.py
```

## 项目结构

- `simple_agent.py` - 一个简单的 agent 示例
- `advanced_agent.py` - 更高级的 agent 示例，包含多个任务
- `computer_example.py` - 直接使用 Computer SDK 的示例
- `requirements.txt` - Python 依赖列表
- `check_python_version.py` - Python 版本和环境检查脚本
- `upgrade_python.sh` - Ubuntu/Debian 系统 Python 升级脚本
- `PYTHON_UPGRADE_GUIDE.md` - 详细的 Python 升级指南

## 支持的模型

CUA 支持多种模型配置：

### 单一模型（完整计算机使用）
- `openai/computer-use-preview` - OpenAI 的计算机使用预览模型
- `anthropic/claude-sonnet-4-5-20250929` - Anthropic Claude Sonnet
- `anthropic/claude-haiku-4-5` - Anthropic Claude Haiku

### 组合模型（Grounding + LLM）
- `moondream3+openai/gpt-4o` - Moondream3 用于 UI 检测 + GPT-4o 用于规划
- `omniparser+anthropic/claude-opus-4-20250514` - OmniParser + Claude

更多模型配置请参考 [CUA 文档](https://cua.ai/docs)。

## 使用场景

- 桌面自动化（Windows、macOS、Linux）
- 浏览器自动化
- 移动设备自动化
- 复杂的多步骤工作流

## 更多资源

- [CUA 官方文档](https://cua.ai/docs)
- [GitHub 仓库](https://github.com/trycua/cua)
- [Discord 社区](https://discord.com/invite/cua-ai)
