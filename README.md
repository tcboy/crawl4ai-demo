# Google Scholar 论文搜索机器人

使用 Playwright 实现的自动化程序，可以搜索指定作者在 Google Scholar 上的论文，并提取论文标题、摘要、引用次数等信息。

## 功能特性

- 🔍 自动搜索指定作者的论文
- 📄 提取论文标题、摘要、引用次数等信息
- 🔒 支持 socks5 代理访问
- 💾 支持将结果导出为 JSON 格式
- 🎯 获取最近的论文（默认前10篇）

## 安装依赖

1. 安装 Python 依赖：
```bash
pip install -r requirements.txt
```

2. 安装 Playwright 浏览器：
```bash
playwright install chromium
```

## 使用方法

### 基本用法

```bash
python scholar_scraper.py "作者姓名"
```

### 使用代理

```bash
python scholar_scraper.py "作者姓名" --proxy socks5://127.0.0.1:1080
```

### 保存结果到文件

```bash
python scholar_scraper.py "作者姓名" --output results.json
```

### 完整示例

```bash
python scholar_scraper.py "John Smith" --proxy socks5://127.0.0.1:1080 --output results.json
```

## 参数说明

- `author_name` (必需): 要搜索的作者姓名
- `--proxy` (可选): socks5 代理地址，格式: `socks5://host:port`
- `--output` (可选): 输出 JSON 文件路径

## 输出格式

程序会在控制台输出论文信息，如果指定了 `--output` 参数，还会将结果保存为 JSON 文件。

JSON 格式示例：
```json
{
  "author": "John Smith",
  "total_papers": 10,
  "papers": [
    {
      "title": "论文标题",
      "authors_info": "作者信息",
      "year": "2023",
      "cited_by": 42,
      "abstract": "论文摘要..."
    }
  ]
}
```

## 注意事项

1. Google Scholar 可能会检测自动化访问，建议使用代理并适当控制访问频率
2. 如果搜索结果页面结构发生变化，可能需要更新选择器
3. 程序默认获取前10篇论文，可以在代码中修改 `paper_elements[:10]` 来调整数量

## 故障排除

- 如果遇到 "Timeout" 错误，可能是网络连接问题，尝试使用代理
- 如果无法找到论文，检查作者姓名是否正确
- 如果选择器失效，Google Scholar 可能更新了页面结构，需要更新代码中的选择器
