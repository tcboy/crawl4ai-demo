# Python 3.11 升级到 3.12 指南

本指南提供了在不同操作系统上将 Python 从 3.11 升级到 3.12 的方法。

## 检查当前 Python 版本

首先检查你当前的 Python 版本：

```bash
python3 --version
python --version
```

## 方法一：Ubuntu/Debian 系统

### 使用 deadsnakes PPA（推荐）

```bash
# 1. 更新包列表
sudo apt update

# 2. 安装必要的依赖
sudo apt install -y software-properties-common

# 3. 添加 deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa

# 4. 更新包列表
sudo apt update

# 5. 安装 Python 3.12
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# 6. 安装 pip（如果还没有）
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# 7. 验证安装
python3.12 --version
```

### 设置 Python 3.12 为默认版本（可选）

```bash
# 查看所有 Python 版本
ls -la /usr/bin/python*

# 创建符号链接（谨慎操作，可能影响系统）
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
sudo update-alternatives --config python3

# 或者使用别名（更安全）
echo 'alias python3=python3.12' >> ~/.bashrc
source ~/.bashrc
```

## 方法二：使用 pyenv（推荐，支持多版本管理）

pyenv 允许你在同一系统上管理多个 Python 版本。

```bash
# 1. 安装 pyenv 依赖
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
libffi-dev liblzma-dev

# 2. 安装 pyenv
curl https://pyenv.run | bash

# 3. 配置环境变量（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

# 4. 重新加载 shell
source ~/.bashrc

# 5. 安装 Python 3.12
pyenv install 3.12.3

# 6. 设置为全局默认版本
pyenv global 3.12.3

# 7. 验证
python --version
```

## 方法三：从源码编译（高级用户）

```bash
# 1. 安装编译依赖
sudo apt update
sudo apt install -y build-essential zlib1g-dev libncurses5-dev \
libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev \
libsqlite3-dev wget libbz2-dev

# 2. 下载 Python 3.12 源码
cd /tmp
wget https://www.python.org/ftp/python/3.12.3/Python-3.12.3.tgz
tar -xzf Python-3.12.3.tgz
cd Python-3.12.3

# 3. 配置编译选项
./configure --enable-optimizations --prefix=/usr/local

# 4. 编译（这可能需要一些时间）
make -j$(nproc)

# 5. 安装（需要 sudo）
sudo make altinstall

# 6. 验证
python3.12 --version
```

## 方法四：macOS 系统

### 使用 Homebrew（推荐）

```bash
# 1. 安装 Homebrew（如果还没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装 Python 3.12
brew install python@3.12

# 3. 创建符号链接（如果需要）
brew link python@3.12

# 4. 验证
python3.12 --version
```

### 使用 pyenv（macOS）

```bash
# 1. 安装 pyenv
brew install pyenv

# 2. 配置环境变量（添加到 ~/.zshrc 或 ~/.bash_profile）
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# 3. 重新加载 shell
source ~/.zshrc

# 4. 安装 Python 3.12
pyenv install 3.12.3

# 5. 设置为全局版本
pyenv global 3.12.3
```

## 方法五：Windows 系统

### 使用官方安装程序

1. 访问 [Python 官网](https://www.python.org/downloads/)
2. 下载 Python 3.12.x Windows 安装程序
3. 运行安装程序，**勾选 "Add Python to PATH"**
4. 选择 "Install Now" 或自定义安装路径
5. 验证安装：
   ```cmd
   python --version
   ```

### 使用 Chocolatey

```powershell
# 以管理员身份运行 PowerShell
choco install python312
```

### 使用 pyenv-win

```powershell
# 1. 安装 pyenv-win
git clone https://github.com/pyenv-win/pyenv-win.git $HOME\.pyenv

# 2. 设置环境变量
[System.Environment]::SetEnvironmentVariable('PYENV_ROOT', "$HOME\.pyenv", 'User')
[System.Environment]::SetEnvironmentVariable('PYENV', "$HOME\.pyenv\bin", 'User')

# 3. 安装 Python 3.12
pyenv install 3.12.3
pyenv global 3.12.3
```

## 升级后的步骤

### 1. 重新安装 pip 和包

```bash
# 使用新的 Python 版本重新安装 pip
python3.12 -m ensurepip --upgrade
python3.12 -m pip install --upgrade pip

# 安装项目依赖
python3.12 -m pip install -r requirements.txt
```

### 2. 重新创建虚拟环境

```bash
# 删除旧的虚拟环境
rm -rf venv env

# 使用 Python 3.12 创建新的虚拟环境
python3.12 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 验证安装

```bash
python --version  # 应该显示 Python 3.12.x
python -m pip --version
```

## 常见问题

### Q: 升级后某些包不兼容怎么办？

A: 检查包的兼容性，某些包可能需要更新版本：
```bash
pip install --upgrade package_name
```

### Q: 如何同时保留 Python 3.11 和 3.12？

A: 使用 pyenv 或保留系统 Python 3.11，使用 `python3.12` 命令调用新版本。

### Q: 升级后项目报错怎么办？

A: 
1. 检查所有依赖是否兼容 Python 3.12
2. 查看项目的 CHANGELOG 或文档
3. 更新到最新版本的依赖包

### Q: 如何检查哪些包需要更新？

```bash
pip list --outdated
pip install --upgrade package_name
```

## 验证 CUA 框架兼容性

升级到 Python 3.12 后，验证 CUA 框架是否正常工作：

```bash
# 创建新的虚拟环境
python3.12 -m venv venv
source venv/bin/activate

# 安装 CUA
pip install cua-agent[all] cua-computer

# 运行简单测试
python3.12 -c "from agent import ComputerAgent; print('CUA 安装成功！')"
```

## 注意事项

1. **不要删除系统 Python 3.11**：某些系统工具可能依赖它
2. **使用虚拟环境**：为每个项目创建独立的虚拟环境
3. **备份重要项目**：升级前备份你的代码和虚拟环境
4. **测试兼容性**：在升级生产环境前，先在开发环境测试

## 推荐方案

- **Linux/Ubuntu**: 使用 `pyenv`（最灵活）或 `deadsnakes PPA`（简单快速）
- **macOS**: 使用 `Homebrew` 或 `pyenv`
- **Windows**: 使用官方安装程序或 `pyenv-win`
