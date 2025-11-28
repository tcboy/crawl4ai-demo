"""
爬取脚本：使用保存的登录态爬取需要登录后才能访问的页面
"""
import asyncio
import json
from pathlib import Path
from crawl4ai import AsyncWebCrawler

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
    
    # 使用 crawl4ai 进行爬取
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
    
    # 创建爬虫实例
    async with AsyncWebCrawler(verbose=True, headless=headless) as crawler:
        # 设置 cookies - 通过 Playwright 的 context 设置
        try:
            # 先访问目标域名以建立 context
            base_url = f"{parsed_url.scheme}://{cookie_domain}"
            print(f"正在初始化浏览器 context: {base_url}")
            await crawler.arun(url=base_url)
            
            # 获取 browser context 并设置 cookies
            if hasattr(crawler, 'browser') and crawler.browser:
                # 尝试多种方式获取 context
                context = None
                if hasattr(crawler.browser, 'contexts') and crawler.browser.contexts:
                    context = crawler.browser.contexts[0]
                elif hasattr(crawler.browser, 'page') and crawler.browser.page:
                    context = crawler.browser.page.context
                elif hasattr(crawler.browser, 'context'):
                    context = crawler.browser.context
                
                if context:
                    print("正在设置 cookies...")
                    await context.add_cookies(cookies)
                    print("✓ Cookies 设置成功")
                else:
                    print("警告: 无法获取 browser context，尝试其他方式...")
        except Exception as e:
            print(f"警告: 设置 cookies 时出错: {e}")
            print("继续尝试爬取...")
        
        # 使用 crawl4ai 爬取页面，配置等待 JavaScript 执行
        print("正在加载页面并等待 JavaScript 执行...")
        
        # 尝试使用 crawl4ai 的配置选项
        try:
            # 方式1: 尝试传递配置参数
            result = await crawler.arun(
                url=url,
                wait_for="networkidle",  # 等待网络空闲
                delay_before_return_html=3.0,  # 额外等待 3 秒
            )
        except TypeError:
            try:
                # 方式2: 使用 config 参数
                result = await crawler.arun(
                    url=url,
                    config={
                        "wait_for": "networkidle",
                        "delay_before_return_html": 3.0,
                    }
                )
            except TypeError:
                # 方式3: 直接调用，然后手动等待
                result = await crawler.arun(url=url)
                
                # 如果结果有 page 对象，手动等待
                if hasattr(result, 'page') and result.page:
                    try:
                        await result.page.wait_for_load_state("networkidle", timeout=15000)
                        await result.page.wait_for_timeout(3000)
                    except:
                        pass
        
        if result.success:
            print("\n✓ 爬取成功！")
            
            # 获取页面内容
            html = result.html if hasattr(result, 'html') else None
            markdown = result.markdown if hasattr(result, 'markdown') else None
            title = result.metadata.get('title', 'N/A') if hasattr(result, 'metadata') else 'N/A'
            
            # 如果 HTML 为空，尝试从 page 对象获取
            if not html or len(html) < 100:
                print("警告: HTML 内容为空或过短，尝试从 page 对象获取...")
                try:
                    if hasattr(crawler, 'browser') and crawler.browser:
                        page = None
                        if hasattr(crawler.browser, 'page') and crawler.browser.page:
                            page = crawler.browser.page
                        elif hasattr(crawler.browser, 'contexts') and crawler.browser.contexts:
                            pages = crawler.browser.contexts[0].pages
                            if pages:
                                page = pages[-1]
                        
                        if page:
                            # 等待页面加载完成
                            await page.wait_for_load_state("networkidle", timeout=10000)
                            await page.wait_for_timeout(3000)
                            html = await page.content()
                            title = await page.title()
                except Exception as e:
                    print(f"从 page 对象获取内容时出错: {e}")
            
            content_length = len(html or markdown or "")
            print(f"✓ 页面标题: {title}")
            print(f"✓ HTML 内容长度: {len(html or '')} 字符")
            print(f"✓ Markdown 内容长度: {len(markdown or '')} 字符")
            print(f"✓ 总内容长度: {content_length} 字符")
            
            # 返回结果
            return {
                "success": True,
                "url": url,
                "html": html,
                "markdown": markdown,
                "title": title,
                "metadata": result.metadata if hasattr(result, 'metadata') else {},
                "screenshot": result.screenshot if hasattr(result, 'screenshot') else None
            }
        else:
            error_msg = result.error_message if hasattr(result, 'error_message') else "未知错误"
            print(f"\n✗ 爬取失败: {error_msg}")
            return {
                "success": False,
                "url": url,
                "error": error_msg
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
        # 保存 HTML
        html_content = result.get("html", "")
        if html_content:
            output_file = Path("scrape_result.html")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\n✓ HTML 结果已保存到: {output_file}")
        
        # 保存 Markdown
        markdown_content = result.get("markdown", "")
        if markdown_content:
            md_file = Path("scrape_result.md")
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"✓ Markdown 结果已保存到: {md_file}")


if __name__ == "__main__":
    asyncio.run(main())
