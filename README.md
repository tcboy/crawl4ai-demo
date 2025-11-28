# Crawl4AI 支付宝登录爬取示例

本项目使用 crawl4ai 实现支付宝登录态保存和后续页面爬取功能。

## 功能说明

1. **登录脚本 (login.py)**: 打开浏览器访问登录页面，等待用户手动登录后保存登录态
2. **爬取脚本 (scrape.py)**: 使用保存的登录态爬取需要登录后才能访问的页面

## 安装依赖

```bash
pip install -r requirements.txt
```

首次使用需要安装 Playwright 浏览器：

```bash
playwright install chromium
```

## 使用方法

### 步骤 1: 登录并保存登录态

运行登录脚本：

```bash
python login.py
```

脚本会：
- 打开浏览器窗口
- 访问支付宝登录页面
- 等待你手动完成登录
- 登录完成后，在终端按 Enter 键
- 自动保存登录态到 `alipay_session.json` 文件

### 步骤 2: 使用登录态爬取页面

运行爬取脚本：

```bash
python scrape.py
```

脚本会：
- 自动加载保存的登录态
- 使用登录态访问需要登录的页面
- 返回页面内容（HTML/Markdown）
- 可选择是否显示浏览器窗口

## 文件说明

- `login.py`: 登录脚本，用于保存登录态
- `scrape.py`: 爬取脚本，使用保存的登录态进行爬取
- `alipay_session.json`: 保存的登录态文件（自动生成）
- `requirements.txt`: Python 依赖包列表

## 注意事项

1. 登录态可能会过期，如果爬取失败，请重新运行 `login.py` 更新登录态
2. 请遵守网站的使用条款和 robots.txt 规定
3. 建议合理控制爬取频率，避免对服务器造成压力
