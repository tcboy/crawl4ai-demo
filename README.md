# GitHub信息抓取机器人

使用Playwright实现的GitHub用户和项目信息自动化抓取工具。

## 功能特性

- ✅ 自动打开浏览器，等待用户手动登录GitHub账号
- ✅ 支持抓取GitHub用户信息（提交记录、项目列表、粉丝数）
- ✅ 支持抓取GitHub项目信息（README内容、提交记录、提交人、Star数）
- ✅ 支持SOCKS5代理访问
- ✅ 支持将结果导出为JSON格式

## 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

## 使用方法

### 基本用法

```bash
# 抓取用户信息
python github_bot.py <github_username>

# 抓取项目信息
python github_bot.py <username/repo>

# 使用SOCKS5代理
python github_bot.py <github_username> --proxy socks5://127.0.0.1:1080

# 保存结果到JSON文件
python github_bot.py <github_username> --output result.json
```

### 参数说明

- `input`: GitHub用户名或项目名（必填）
  - 用户名格式：`username`
  - 项目名格式：`username/repo`
- `--proxy, -p`: SOCKS5代理地址（可选）
  - 格式：`socks5://host:port`
  - 示例：`socks5://127.0.0.1:1080`
- `--output, -o`: 输出JSON文件路径（可选）

### 使用示例

```bash
# 示例1: 抓取用户信息
python github_bot.py octocat

# 示例2: 抓取项目信息
python github_bot.py microsoft/vscode

# 示例3: 使用代理并保存结果
python github_bot.py octocat --proxy socks5://127.0.0.1:1080 --output user_info.json
```

## 工作流程

1. 程序启动后会自动打开浏览器
2. 访问GitHub登录页面
3. **等待用户在浏览器中手动完成登录**
4. 用户在终端按回车键继续
5. 程序自动访问目标用户或项目页面
6. 抓取相关信息并输出
7. 可选择将结果保存为JSON文件

## 输出信息

### 用户信息包含：
- 用户名
- 粉丝数
- 项目列表（名称、URL、描述、语言、Stars）
- 最近的提交记录

### 项目信息包含：
- 项目名称
- Star数
- README内容
- 最近的提交记录（包含提交人和日期）
- 贡献者列表

## 注意事项

1. **登录要求**: 程序需要用户手动在浏览器中登录GitHub账号，这是为了避免自动化登录可能触发的安全验证
2. **网络要求**: 确保能够访问GitHub网站，如果使用代理，请正确配置SOCKS5代理地址
3. **浏览器**: 程序使用Chromium浏览器，首次运行需要安装浏览器驱动
4. **数据抓取**: 由于GitHub页面结构可能变化，某些信息可能无法完全抓取，程序会尽可能获取可用信息

## 故障排除

### 问题：无法安装Playwright浏览器
```bash
# 手动安装Chromium
playwright install chromium
```

### 问题：代理连接失败
- 检查代理地址和端口是否正确
- 确认代理服务正在运行
- 检查代理是否需要认证（当前版本不支持认证）

### 问题：无法抓取某些信息
- GitHub页面结构可能已更新，需要更新选择器
- 某些信息可能需要登录后才能访问
- 检查网络连接是否正常

## 许可证

MIT License
