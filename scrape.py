"""
爬取脚本：使用保存的登录态爬取需要登录后才能访问的页面
"""
import asyncio
import json
from pathlib import Path
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


async def scrape_with_session(url: str, headless: bool = True):
    """
    使用保存的登录态爬取指定页面
    
    Args:
        url: 要爬取的页面URL
        headless: 是否使用无头模式（默认True，不显示浏览器）
    """
    # 加载登录态
    print("正在加载登录态...")
    session_data = await load_session()
    cookies = session_data.get("cookies", [])
    
    if not cookies:
        raise ValueError("登录态文件中没有找到 cookies")
    
    print(f"✓ 已加载 {len(cookies)} 个 cookies")
    
    # 使用 Playwright 直接控制浏览器，确保等待JS执行
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=headless)
        
        # 创建新的 context
        context = await browser.new_context()
        
        # 设置 cookies
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        cookie_domain = parsed_url.netloc
        
        # 确保 cookies 有正确的域名和路径
        for cookie in cookies:
            if 'domain' not in cookie:
                cookie['domain'] = cookie_domain
            if 'path' not in cookie:
                cookie['path'] = '/'
        
        # 先访问目标域名以建立 context，然后设置 cookies
        base_url = f"{parsed_url.scheme}://{cookie_domain}"
        page = await context.new_page()
        await page.goto(base_url)
        
        # 添加 cookies（必须在访问页面后设置）
        await context.add_cookies(cookies)
        
        # 刷新页面以应用 cookies
        await page.reload(wait_until="domcontentloaded")
        
        print(f"\n正在爬取: {url}")
        print("=" * 60)
        
        # 访问目标页面
        print("正在加载页面...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # 等待网络空闲（确保 AJAX 请求完成）
        print("等待网络请求完成...")
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            print(f"网络空闲等待超时，继续执行: {e}")
        
        # 额外等待，确保 JavaScript 执行完成和动态内容加载
        print("等待 JavaScript 执行完成...")
        await page.wait_for_timeout(3000)  # 等待 3 秒，确保动态内容加载
        
        # 尝试等待页面主要内容出现（可选，根据实际情况调整）
        # 例如：等待 body 标签有内容
        try:
            await page.wait_for_selector("body", state="attached", timeout=5000)
            # 等待 body 有实际内容
            await page.wait_for_function(
                "() => document.body && document.body.innerText.length > 0",
                timeout=5000
            )
        except Exception as e:
            print(f"等待页面内容时出现警告: {e}")
            # 继续执行，即使没有找到特定元素
        
        # 获取页面内容
        html = await page.content()
        title = await page.title()
        
        # 获取页面文本内容（可选）
        try:
            body_text = await page.evaluate("() => document.body.innerText")
        except:
            body_text = ""
        
        # 截图（可选）
        screenshot = None
        if not headless:
            screenshot = await page.screenshot(full_page=True)
        
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
    result = await scrape_with_session(target_url, headless=not show_browser)
    
    # 保存结果（可选）
    if result.get("success"):
        output_file = Path("scrape_result.html")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.get("html", ""))
        print(f"\n✓ HTML 结果已保存到: {output_file}")
        
        # 同时保存文本内容
        text_file = Path("scrape_result.txt")
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(result.get("text", ""))
        print(f"✓ 文本结果已保存到: {text_file}")


if __name__ == "__main__":
    asyncio.run(main())
