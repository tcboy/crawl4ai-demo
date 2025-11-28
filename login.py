"""
登录脚本：打开浏览器，访问登录页面，等待用户手动登录后保存登录态
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

# 登录态存储文件路径
SESSION_FILE = Path("alipay_session.json")


async def login_and_save_session():
    """
    打开浏览器，访问登录页面，等待用户手动登录后保存会话
    """
    print("正在启动浏览器...")
    print("请在浏览器中完成登录操作，登录完成后程序会自动保存登录态")
    
    url = "https://pubbuservice.alipay.com/login.htm"
    
    print(f"\n正在访问: {url}")
    print("=" * 60)
    print("请在打开的浏览器窗口中完成登录操作")
    print("登录完成后，请在此终端按 Enter 键继续...")
    print("=" * 60)
    
    # 使用 Playwright 直接控制浏览器，确保窗口打开
    async with async_playwright() as p:
        # 启动浏览器，明确设置 headless=False
        print("正在启动浏览器（非无头模式）...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 访问登录页面
        print(f"正在访问: {url}")
        await page.goto(url)
        
        print("\n浏览器窗口应该已经打开。")
        print("请在浏览器窗口中完成登录操作。")
        print("登录完成后，请在此终端按 Enter 键继续...")
        
        # 等待用户输入确认登录完成
        input("\n登录完成后，请按 Enter 键继续保存登录态...")
        
        # 获取 cookies
        cookies = await context.cookies()
        
        # 关闭浏览器
        await browser.close()
        
        session_data = {
            "cookies": cookies,
            "url": url
        }
        
        # 保存到文件
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 登录态已保存到: {SESSION_FILE}")
        print(f"✓ Cookies 数量: {len(cookies)}")
        
        return session_data


if __name__ == "__main__":
    asyncio.run(login_and_save_session())
