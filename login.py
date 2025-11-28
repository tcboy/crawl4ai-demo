"""
登录脚本：打开浏览器，访问登录页面，等待用户手动登录后保存登录态
"""
import asyncio
import json
from pathlib import Path
from crawl4ai import AsyncWebCrawler

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
    
    async with AsyncWebCrawler(verbose=True, headless=False) as crawler:
        # 访问登录页面，使用非无头模式
        result = await crawler.arun(url=url)
        
        # 等待用户输入确认登录完成
        input("\n登录完成后，请按 Enter 键继续保存登录态...")
        
        # 获取并保存会话信息（cookies）
        # 通过 Playwright 的 browser context 获取 cookies
        cookies = []
        try:
            # 尝试通过 crawler 的内部 browser 对象获取 cookies
            if hasattr(crawler, 'browser') and crawler.browser:
                if hasattr(crawler.browser, 'contexts') and crawler.browser.contexts:
                    cookies = await crawler.browser.contexts[0].cookies()
                elif hasattr(crawler.browser, 'page') and crawler.browser.page:
                    cookies = await crawler.browser.page.context.cookies()
        except Exception as e:
            print(f"警告: 无法通过 browser 对象获取 cookies: {e}")
        
        # 如果仍然没有 cookies，尝试从结果中获取
        if not cookies and hasattr(result, 'cookies'):
            cookies = result.cookies
        
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
