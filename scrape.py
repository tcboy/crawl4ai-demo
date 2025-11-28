"""
爬取脚本：使用保存的登录态爬取需要登录后才能访问的页面
使用 Firecrawl 进行爬取
"""
import asyncio
import json
from pathlib import Path
from firecrawl import FirecrawlApp
from playwright.async_api import async_playwright

# 登录态存储文件路径
SESSION_FILE = Path("alipay_session.json")


async def load_session():
    """
    从文件加载保存的登录态
    """
    if not SESSION_FILE.exists():
        raise FileNotFoundError(
            f"未找到登录态文件: {SESSION_FILE}\n"
            "请先运行 login.py 完成登录并保存登录态"
        )
    
    with open(SESSION_FILE, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    return session_data


async def scrape_with_session(url: str, headless: bool = True, use_firecrawl: bool = True):
    """
    使用保存的登录态爬取指定页面
    
    Args:
        url: 要爬取的页面URL
        headless: 是否使用无头模式（默认True，不显示浏览器）
        use_firecrawl: 是否使用 Firecrawl（默认True），如果 False 则使用 Playwright
    """
    # 加载登录态
    print("正在加载登录态...")
    session_data = await load_session()
    cookies = session_data.get("cookies", [])
    
    if not cookies:
        raise ValueError("登录态文件中没有找到 cookies")
    
    print(f"✓ 已加载 {len(cookies)} 个 cookies")
    
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    cookie_domain = parsed_url.netloc
    
    # 确保 cookies 有正确的域名和路径
    for cookie in cookies:
        if 'domain' not in cookie:
            cookie['domain'] = cookie_domain
        if 'path' not in cookie:
            cookie['path'] = '/'
    
    print(f"\n正在爬取: {url}")
    print("=" * 60)
    
    if use_firecrawl:
        # 使用 Firecrawl 进行爬取
        print("使用 Firecrawl 进行爬取...")
        
        # 注意：Firecrawl 可能需要 API key，如果没有可以尝试不使用
        # 或者使用 Playwright 方式
        try:
            # 尝试使用 Firecrawl（可能需要 API key）
            app = FirecrawlApp()
            
            # Firecrawl 可能不支持直接设置 cookies
            # 所以我们需要先使用 Playwright 设置 cookies，然后获取内容
            # 或者使用 Firecrawl 的浏览器模式
            
            print("警告: Firecrawl 可能不支持直接设置 cookies")
            print("改用 Playwright 方式以确保 cookies 正确设置...")
            use_firecrawl = False
            
        except Exception as e:
            print(f"Firecrawl 初始化失败: {e}")
            print("改用 Playwright 方式...")
            use_firecrawl = False
    
    if not use_firecrawl:
        # 使用 Playwright 直接控制浏览器
        print("使用 Playwright 进行爬取...")
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(headless=headless)
            
            # 创建新的 context
            context = await browser.new_context()
            
            # 先访问目标域名以建立 context
            base_url = f"{parsed_url.scheme}://{cookie_domain}"
            page = await context.new_page()
            await page.goto(base_url)
            
            # 添加 cookies
            await context.add_cookies(cookies)
            
            print("正在访问目标页面...")
            # 访问目标页面
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # 等待网络空闲（确保 AJAX 请求完成）
            print("等待网络请求完成...")
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
                print("✓ 网络请求已完成")
            except Exception as e:
                print(f"网络空闲等待超时，继续执行: {e}")
            
            # 额外等待，确保 JavaScript 执行完成和动态内容加载
            print("等待 JavaScript 执行完成（5秒）...")
            await page.wait_for_timeout(5000)
            
            # 等待页面有实际内容
            print("检查页面内容...")
            max_retries = 3
            for i in range(max_retries):
                try:
                    # 等待 body 有内容
                    await page.wait_for_function(
                        "() => document.body && document.body.innerText.trim().length > 0",
                        timeout=5000
                    )
                    print(f"✓ 页面内容已加载（尝试 {i+1}/{max_retries}）")
                    break
                except Exception as e:
                    if i < max_retries - 1:
                        print(f"等待内容加载中... ({i+1}/{max_retries})")
                        await page.wait_for_timeout(2000)
                    else:
                        print(f"警告: 页面内容可能未完全加载: {e}")
            
            # 再次等待网络空闲
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass
            
            # 获取页面内容
            print("正在获取页面内容...")
            html = await page.content()
            title = await page.title()
            
            # 获取页面文本内容
            try:
                body_text = await page.evaluate("() => document.body.innerText")
            except:
                body_text = ""
            
            # 截图（可选）
            screenshot = None
            if not headless:
                try:
                    screenshot = await page.screenshot(full_page=True)
                except:
                    pass
            
            # 关闭浏览器
            await browser.close()
            
            print("\n✓ 爬取成功！")
            print(f"✓ 页面标题: {title}")
            print(f"✓ HTML 内容长度: {len(html)} 字符")
            print(f"✓ 文本内容长度: {len(body_text)} 字符")
            
            # 返回结果
            return {
                "success": True,
                "url": url,
                "html": html,
                "text": body_text,
                "title": title,
                "screenshot": screenshot
            }


async def main():
    """
    主函数：示例如何使用保存的登录态爬取页面
    """
    # 示例：爬取需要登录的页面
    # 请根据实际需要修改URL
    target_url = input("请输入要爬取的页面URL（需要登录后才能访问）: ").strip()
    
    if not target_url:
        print("未提供URL，使用默认示例URL")
        target_url = "https://pubbuservice.alipay.com/"  # 示例URL，请根据实际情况修改
    
    # 询问是否显示浏览器
    show_browser = input("是否显示浏览器窗口？(y/n，默认n): ").strip().lower() == 'y'
    
    # 执行爬取
    result = await scrape_with_session(target_url, headless=not show_browser, use_firecrawl=False)
    
    # 保存结果（可选）
    if result.get("success"):
        # 保存 HTML
        html_content = result.get("html", "")
        if html_content:
            output_file = Path("scrape_result.html")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\n✓ HTML 结果已保存到: {output_file}")
        
        # 保存文本内容
        text_content = result.get("text", "")
        if text_content:
            text_file = Path("scrape_result.txt")
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            print(f"✓ 文本结果已保存到: {text_file}")


if __name__ == "__main__":
    asyncio.run(main())
