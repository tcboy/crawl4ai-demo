"""
直接使用 Computer SDK 的示例

这个示例展示了如何直接使用 Computer SDK 来控制计算机，
而不使用 Agent。这对于需要精确控制的操作很有用。
"""

import asyncio
from computer import Computer


async def main():
    """直接使用 Computer SDK 的示例"""
    print("🖥️  启动 Computer SDK 示例...\n")
    
    try:
        # 创建计算机实例
        computer = Computer(
            os_type="macos",
            verbosity="INFO",
        )
        
        # 启动计算机
        await computer.run()
        
        # 1. 截取屏幕截图
        print("📸 截取屏幕截图...")
        screenshot = await computer.interface.screenshot()
        
        # 保存截图
        with open("screenshot.png", "wb") as f:
            f.write(screenshot)
        print("✅ 截图已保存到 screenshot.png\n")
        
        # 2. 获取屏幕尺寸
        screen_size = await computer.interface.get_screen_size()
        print(f"📐 屏幕尺寸: {screen_size}\n")
        
        # 3. 鼠标操作示例
        print("🖱️  执行鼠标操作...")
        await computer.interface.move_cursor(500, 500)
        await computer.interface.left_click()
        print("✅ 鼠标点击完成\n")
        
        # 4. 键盘操作示例
        print("⌨️  执行键盘操作...")
        await computer.interface.type_text("Hello from CUA!")
        await computer.interface.press_key("enter")
        print("✅ 键盘输入完成\n")
        
        # 5. 剪贴板操作示例
        print("📋 执行剪贴板操作...")
        await computer.interface.set_clipboard("CUA Framework Test")
        clipboard_content = await computer.interface.copy_to_clipboard()
        print(f"✅ 剪贴板内容: {clipboard_content}\n")
        
        # 6. 运行命令示例（Linux/macOS）
        print("💻 执行命令...")
        result = await computer.interface.run_command("echo 'Hello from CUA!'")
        print(f"✅ 命令输出: {result}\n")
        
        # 7. 获取可访问性树（UI 结构）
        print("🌳 获取可访问性树...")
        accessibility_tree = await computer.interface.get_accessibility_tree()
        print(f"✅ 可访问性树已获取（长度: {len(accessibility_tree)} 字符）\n")
        
        print("🎉 所有操作完成！")
        
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        if 'computer' in locals():
            await computer.stop()


if __name__ == "__main__":
    asyncio.run(main())
