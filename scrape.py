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
    
    # 创建爬虫实例
    async with AsyncWebCrawler(verbose=True, headless=headless) as crawler:
        # 先访问一个页面以初始化 browser context，然后设置 cookies
        # 获取 cookies 的域名信息
        cookie_domain = None
        if cookies:
            # 从 cookies 中提取域名，或使用目标 URL 的域名
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            cookie_domain = parsed_url.netloc
        
        # 设置 cookies - 通过 Playwright 的 context 设置
        try:
            # 先访问目标域名的主页以建立 context
            if cookie_domain:
                base_url = f"{parsed_url.scheme}://{cookie_domain}"
                await crawler.arun(url=base_url)
            
            # 设置 cookies
            if hasattr(crawler, 'browser') and crawler.browser:
                if hasattr(crawler.browser, 'contexts') and crawler.browser.contexts:
                    # 确保 cookies 有正确的域名
                    for cookie in cookies:
                        if 'domain' not in cookie and cookie_domain:
                            cookie['domain'] = cookie_domain
                    await crawler.browser.contexts[0].add_cookies(cookies)
                elif hasattr(crawler.browser, 'page') and crawler.browser.page:
                    for cookie in cookies:
                        if 'domain' not in cookie and cookie_domain:
                            cookie['domain'] = cookie_domain
                    await crawler.browser.page.context.add_cookies(cookies)
        except Exception as e:
            print(f"警告: 设置 cookies 时出错: {e}")
            print("继续尝试爬取...")
        
        print(f"\n正在爬取: {url}")
        print("=" * 60)
        
        # 爬取页面
        result = await crawler.arun(url=url)
        
        if result.success:
            print("\n✓ 爬取成功！")
            title = result.metadata.get('title', 'N/A') if hasattr(result, 'metadata') else 'N/A'
            content = result.markdown or result.html or ''
            print(f"✓ 页面标题: {title}")
            print(f"✓ 内容长度: {len(content)} 字符")
            
            # 返回结果
            return {
                "success": True,
                "url": url,
                "html": result.html if hasattr(result, 'html') else None,
                "markdown": result.markdown if hasattr(result, 'markdown') else None,
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
        output_file = Path("scrape_result.html")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.get("html", ""))
        print(f"\n✓ 结果已保存到: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
