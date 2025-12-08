# 小红书热门文章抓取AI Agent系统

一个基于Agentic Agent架构的智能系统，用于在小红书搜索指定领域的热门知识文章，并自动保存点赞收藏量高的内容到本地。

## 系统架构

本系统采用**Master-Sub Agent架构**：

- **Master Agent**: 负责任务规划、拆解和结果评估
  - 使用OpenAI API进行智能任务规划
  - 将复杂任务拆解为可执行的子任务
  - 对抓取结果进行筛选和评估

- **Sub Agent**: 负责具体的网页操作和数据抓取
  - 使用Playwright进行浏览器自动化
  - 模拟真实用户行为（滚动、点击等）
  - 提取文章标题、作者、点赞数、收藏数等信息

- **Storage模块**: 负责数据持久化
  - 将筛选后的热门文章保存为JSON格式
  - 支持按领域分类存储
  - 生成抓取摘要报告

## 功能特性

- ✅ 智能任务规划：自动拆解搜索任务为多个子任务
- ✅ 多关键词搜索：支持同时搜索多个相关关键词
- ✅ 智能筛选：根据点赞数和收藏数筛选高质量内容
- ✅ 自动翻页：自动翻页抓取多页内容
- ✅ 数据去重：自动去除重复文章
- ✅ 本地存储：将结果保存为结构化的JSON文件

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

### 3. 安装Playwright浏览器

```bash
playwright install chromium
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置以下配置：

```env
# OpenAI API配置（必需）
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# 数据存储配置
DATA_DIR=./data

# 爬虫配置
MAX_ARTICLES=50          # 最多保存的文章数
MIN_LIKES=100            # 最少点赞数阈值
MIN_COLLECTIONS=50       # 最少收藏数阈值

# Playwright配置
HEADLESS=True            # 是否无头模式运行
TIMEOUT=30000            # 超时时间（毫秒）
```

## 使用方法

### 基本使用

```bash
python main.py "Python编程"
```

或者交互式运行：

```bash
python main.py
# 然后输入要搜索的领域
```

### 示例

```bash
# 搜索健身相关内容
python main.py "健身"

# 搜索美食相关内容
python main.py "美食"

# 搜索编程相关内容
python main.py "Python编程"
```

## 输出结果

### 文件结构

运行后会在 `data/` 目录下生成以下文件：

```
data/
├── articles/
│   ├── Python编程_20240101_120000.json    # 文章数据
│   └── 健身_20240101_130000.json
└── Python编程_summary_20240101_120000.json  # 抓取摘要
```

### 文章数据格式

每个文章JSON文件包含：

```json
{
  "domain": "Python编程",
  "crawled_at": "2024-01-01 12:00:00",
  "total_articles": 25,
  "articles": [
    {
      "title": "Python入门教程",
      "url": "https://www.xiaohongshu.com/explore/...",
      "author": "程序员小张",
      "likes": 1500,
      "collections": 800,
      "cover_image": "https://...",
      "content_preview": "这是一篇关于Python的...",
      "crawled_at": "2024-01-01 12:00:00"
    },
    ...
  ]
}
```

## 工作流程

1. **任务规划阶段**
   - Master Agent分析搜索领域
   - 生成搜索关键词列表
   - 拆解为多个子任务

2. **数据抓取阶段**
   - Sub Agent初始化浏览器
   - 访问小红书搜索页面
   - 执行搜索并抓取文章信息
   - 自动翻页获取更多内容

3. **结果评估阶段**
   - Master Agent评估抓取结果
   - 按点赞数和收藏数排序
   - 应用筛选标准

4. **数据存储阶段**
   - 保存筛选后的文章到本地
   - 生成抓取摘要报告

## 配置说明

### 筛选标准

在 `.env` 文件中可以调整：

- `MIN_LIKES`: 最少点赞数，低于此值的文章会被过滤
- `MIN_COLLECTIONS`: 最少收藏数，低于此值的文章会被过滤
- `MAX_ARTICLES`: 最多保存的文章数量

### 抓取策略

在 `config.py` 中可以调整：

- `MAX_PAGES`: 每个关键词最多翻页数
- `HEADLESS`: 是否显示浏览器窗口
- `TIMEOUT`: 页面加载超时时间

## 注意事项

1. **API密钥**: 需要有效的OpenAI API密钥才能使用Master Agent的规划功能

2. **反爬虫**: 小红书可能有反爬虫机制，建议：
   - 适当增加请求间隔
   - 使用真实浏览器环境
   - 不要过于频繁地抓取

3. **选择器更新**: 如果小红书更新了页面结构，可能需要更新 `sub_agent.py` 中的CSS选择器

4. **法律合规**: 请遵守小红书的服务条款和robots.txt，仅用于学习和研究目的

## 故障排除

### 问题：无法连接到OpenAI API

**解决方案**: 检查 `.env` 文件中的 `OPENAI_API_KEY` 是否正确设置

### 问题：Playwright浏览器启动失败

**解决方案**: 运行 `playwright install chromium` 重新安装浏览器

### 问题：抓取不到文章数据

**解决方案**: 
- 检查网络连接
- 尝试关闭无头模式（设置 `HEADLESS=False`）查看浏览器行为
- 小红书页面结构可能已更新，需要调整选择器

### 问题：登录弹窗无法关闭

**解决方案**: 可能需要手动登录一次，或者调整 `_handle_login_popup()` 方法中的选择器

## 开发计划

- [ ] 支持更多数据源（微博、知乎等）
- [ ] 添加数据分析和可视化功能
- [ ] 支持增量更新（只抓取新文章）
- [ ] 添加Web界面
- [ ] 支持导出为其他格式（CSV、Excel等）

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
