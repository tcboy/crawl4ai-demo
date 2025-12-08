# 小红书热门内容搜索 AI Agent 系统

一个基于 Agentic Agent 架构的智能系统，用于自动搜索小红书上的热门知识文章并保存到本地。

## 功能特性

- 🤖 **Agentic Agent 架构**: Master Agent 负责任务规划，Search Agent 负责执行搜索
- 🔍 **智能搜索**: 自动搜索指定领域的热门内容
- 📊 **数据筛选**: 根据点赞数、收藏数等指标筛选高质量内容
- 💾 **本地存储**: 自动保存文章内容到本地 JSON 文件
- 🔐 **登录支持**: 支持小红书账号登录，提高访问权限
- 🎯 **智能规划**: 使用 LLM 自动拆解和规划搜索任务

## 系统架构

```
┌─────────────────┐
│   Master Agent  │  ← 任务规划与拆解
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Search Agent  │  ← 执行搜索任务
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 小红书爬虫工具   │  ← Playwright 自动化
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   数据存储模块   │  ← 本地文件存储
└─────────────────┘
```

## 安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd xiaohongshu-agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 安装 Playwright 浏览器

```bash
playwright install chromium
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# OpenAI API配置（用于Agent推理）
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# 小红书账号配置（可选，但建议配置以提高访问权限）
XHS_USERNAME=your_username
XHS_PASSWORD=your_password

# 数据存储路径
DATA_DIR=./data

# 浏览器配置
HEADLESS=false  # 设置为 true 可无头模式运行
BROWSER_TIMEOUT=30000
```

## 使用方法

### 基本使用

```bash
python main.py "Python编程教程"
```

或者在交互模式下运行：

```bash
python main.py
# 然后输入搜索关键词
```

### 示例

```bash
# 搜索 Python 相关热门内容
python main.py "Python编程"

# 搜索健身相关热门内容
python main.py "健身减脂"

# 搜索美食相关热门内容
python main.py "美食探店"
```

## 工作流程

1. **任务规划阶段** (Master Agent)
   - 分析用户需求
   - 拆解为具体的搜索关键词
   - 制定筛选策略和质量标准

2. **搜索执行阶段** (Search Agent)
   - 初始化浏览器和登录状态
   - 对每个关键词执行搜索
   - 提取文章信息（标题、作者、点赞数、收藏数等）

3. **数据筛选阶段**
   - 根据设定的阈值筛选高质量内容
   - 按热度（点赞+收藏）排序

4. **数据存储阶段**
   - 将筛选后的文章保存为 JSON 文件
   - 按领域分类存储到不同目录

## 输出格式

文章数据以 JSON 格式保存，包含以下字段：

```json
{
  "article_id": "文章ID",
  "note_id": "笔记ID",
  "title": "文章标题",
  "author": "作者名称",
  "url": "文章链接",
  "cover_img": "封面图片URL",
  "likes": 1000,
  "collections": 500,
  "comments": 200,
  "content": "文章内容",
  "keyword": "搜索关键词",
  "scraped_at": "2024-01-01 12:00:00",
  "saved_at": "2024-01-01T12:00:00"
}
```

## 目录结构

```
.
├── main.py                 # 主程序入口
├── agents/                 # Agent模块
│   ├── master_agent.py    # Master Agent
│   └── search_agent.py    # Search Agent
├── tools/                 # 工具模块
│   └── xiaohongshu_scraper.py  # 小红书爬虫工具
├── utils/                  # 工具函数
│   ├── config.py          # 配置管理
│   └── storage.py         # 数据存储
├── data/                   # 数据存储目录
│   └── [领域名称]/        # 按领域分类
├── .auth/                  # 登录状态保存目录
├── requirements.txt        # 依赖包
└── README.md              # 项目说明
```

## 注意事项

1. **账号登录**: 
   - 首次运行可能需要手动处理验证码
   - 登录状态会保存到 `.auth/xhs_state.json`，下次运行会自动加载
   - 建议配置账号密码以提高访问权限和稳定性

2. **反爬虫机制**:
   - 系统已实现基本的反检测措施
   - 建议适当控制搜索频率，避免触发限制
   - 如遇到验证码，系统会等待30秒供手动处理

3. **数据准确性**:
   - 小红书的页面结构可能会变化，如遇到解析错误，可能需要更新爬虫代码
   - 建议定期检查输出数据的完整性

4. **API 配置**:
   - 需要配置 OpenAI API Key 用于 Agent 推理
   - 也可以使用其他兼容 OpenAI API 的服务

## 故障排除

### 问题1: 登录失败

**解决方案**:
- 检查账号密码是否正确
- 首次登录可能需要手动处理验证码
- 检查网络连接是否正常

### 问题2: 搜索无结果

**解决方案**:
- 检查关键词是否有效
- 尝试调整筛选条件（降低点赞/收藏阈值）
- 检查是否需要登录

### 问题3: Playwright 错误

**解决方案**:
```bash
playwright install chromium
playwright install-deps
```

## 开发计划

- [ ] 支持更多筛选条件（发布时间、作者等）
- [ ] 添加数据分析和可视化功能
- [ ] 支持批量导出为其他格式（CSV、Markdown等）
- [ ] 添加定时任务功能
- [ ] 优化反爬虫策略

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
