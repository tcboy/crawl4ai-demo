#!/usr/bin/env python3
"""
检查 Python 版本并验证 CUA 框架兼容性
"""

import sys
import subprocess
import platform

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    print(f"🐍 Python 版本: {version.major}.{version.minor}.{version.micro}")
    print(f"   路径: {sys.executable}")
    print(f"   平台: {platform.platform()}")
    print()
    
    # 检查是否符合 CUA 要求
    if version.major == 3 and version.minor in [12, 13]:
        print("✅ Python 版本符合 CUA 框架要求（需要 3.12 或 3.13）")
    elif version.major == 3 and version.minor == 14:
        print("⚠️  Python 3.14 目前不被 CUA 支持，建议使用 3.12 或 3.13")
    elif version.major == 3 and version.minor == 11:
        print("⚠️  Python 3.11 不符合 CUA 要求，需要升级到 3.12 或 3.13")
        print("   请运行: bash upgrade_python.sh")
    else:
        print(f"⚠️  Python {version.major}.{version.minor} 可能不符合 CUA 要求")
    
    print()
    return version

def check_pip():
    """检查 pip 是否可用"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ pip 可用: {result.stdout.strip()}")
            return True
        else:
            print("❌ pip 不可用")
            return False
    except Exception as e:
        print(f"❌ 检查 pip 时出错: {e}")
        return False

def check_cua_installed():
    """检查 CUA 是否已安装"""
    try:
        import agent
        print("✅ cua-agent 已安装")
        return True
    except ImportError:
        print("❌ cua-agent 未安装")
        print("   安装命令: pip install cua-agent[all]")
        return False

def check_available_python_versions():
    """检查系统上可用的 Python 版本"""
    print("\n📋 系统上可用的 Python 版本:")
    versions = []
    
    # 检查常见的 Python 命令
    for cmd in ["python3.12", "python3.13", "python3.11", "python3.10"]:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                versions.append((cmd, version))
                print(f"   ✅ {cmd}: {version}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    
    if not versions:
        print("   (未找到其他 Python 版本)")
    
    return versions

def main():
    print("=" * 60)
    print("CUA 框架 Python 环境检查")
    print("=" * 60)
    print()
    
    # 检查当前 Python 版本
    version = check_python_version()
    
    # 检查 pip
    print("📦 检查 pip...")
    pip_available = check_pip()
    print()
    
    # 检查 CUA
    print("🔍 检查 CUA 框架...")
    cua_installed = check_cua_installed()
    print()
    
    # 检查其他可用版本
    available_versions = check_available_python_versions()
    print()
    
    # 总结
    print("=" * 60)
    print("📊 检查总结")
    print("=" * 60)
    
    all_ok = True
    
    if version.major == 3 and version.minor in [12, 13]:
        print("✅ Python 版本: 符合要求")
    else:
        print("❌ Python 版本: 需要升级到 3.12 或 3.13")
        all_ok = False
    
    if pip_available:
        print("✅ pip: 可用")
    else:
        print("❌ pip: 不可用")
        all_ok = False
    
    if cua_installed:
        print("✅ CUA: 已安装")
    else:
        print("⚠️  CUA: 未安装（可选）")
    
    print()
    
    if all_ok:
        print("🎉 环境检查通过！可以开始使用 CUA 框架了。")
    else:
        print("⚠️  请先解决上述问题。")
        print()
        print("💡 升级 Python 的方法:")
        print("   - Ubuntu/Debian: bash upgrade_python.sh")
        print("   - 其他系统: 查看 PYTHON_UPGRADE_GUIDE.md")

if __name__ == "__main__":
    main()
