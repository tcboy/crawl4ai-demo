"""
爬取脚本：使用保存的登录态爬取需要登录后才能访问的页面
使用 crawl4ai 进行爬取和结构化整理
"""
import asyncio
import json
from pathlib import Path
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
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


async def scrape_with_session(url: str, headless: bool = True, extract_schema: dict = None):
    """
    使用保存的登录态爬取指定页面，并使用 crawl4ai 进行结构化整理
    
    Args:
        url: 要爬取的页面URL
        headless: 是否使用无头模式（默认True，不显示浏览器）
        extract_schema: 结构化提取的 schema（可选），用于 LLM 提取策略
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
    
    # 使用 crawl4ai 进行爬取
    async with AsyncWebCrawler(verbose=True, headless=headless) as crawler:
        # 先访问目标域名以建立 context 并设置 cookies
        base_url = f"{parsed_url.scheme}://{cookie_domain}"
        print(f"正在初始化浏览器 context: {base_url}")
        
        try:
            # 先访问基础 URL 建立 context
            await crawler.arun(url=base_url)
            
            # 获取 browser context 并设置 cookies
            context = None
            if hasattr(crawler, 'browser') and crawler.browser:
                browser_obj = crawler.browser
                
                # 尝试多种方式获取 context
                if hasattr(browser_obj, 'contexts') and browser_obj.contexts:
                    context = browser_obj.contexts[0]
                elif hasattr(browser_obj, 'page') and browser_obj.page:
                    context = browser_obj.page.context
                elif hasattr(browser_obj, 'context'):
                    context = browser_obj.context
                elif hasattr(browser_obj, '_browser'):
                    # 尝试通过内部 browser 对象
                    browser = browser_obj._browser
                    if hasattr(browser, 'contexts') and browser.contexts:
                        context = browser.contexts[0]
                
                if context:
                    print("正在设置 cookies...")
                    await context.add_cookies(cookies)
                    print("✓ Cookies 设置成功")
                else:
                    print("警告: 无法获取 browser context")
        except Exception as e:
            print(f"警告: 设置 cookies 时出错: {e}")
            print("继续尝试爬取...")
        
        # 准备提取策略（如果提供了 schema）
        extraction_strategy = None
        if extract_schema:
            print("使用 LLM 提取策略进行结构化整理...")
            try:
                extraction_strategy = LLMExtractionStrategy(
                    schema=extract_schema,
                    extraction_type="schema",
                    instruction="请从页面中提取结构化数据，确保提取所有相关信息。"
                )
            except Exception as e:
                print(f"创建提取策略时出错: {e}")
                print("将使用默认提取方式...")
        
        # 使用 crawl4ai 爬取页面
        print("正在加载页面并等待 JavaScript 执行...")
        
        # 访问目标页面
        result = await crawler.arun(
            url=url,
            extraction_strategy=extraction_strategy
        )
        
        # 获取 page 对象并手动等待 JavaScript 执行完成
        page = None
        try:
            if hasattr(crawler, 'browser') and crawler.browser:
                browser_obj = crawler.browser
                if hasattr(browser_obj, 'contexts') and browser_obj.contexts:
                    contexts = browser_obj.contexts
                    if contexts and len(contexts) > 0:
                        pages = contexts[0].pages
                        if pages and len(pages) > 0:
                            page = pages[-1]
                elif hasattr(browser_obj, 'page') and browser_obj.page:
                    page = browser_obj.page
        except Exception as e:
            print(f"获取 page 对象时出错: {e}")
        
        # 等待 JavaScript 执行完成
        if page:
            print("等待 JavaScript 执行完成...")
            try:
                # 等待网络空闲
                await page.wait_for_load_state("networkidle", timeout=20000)
                print("✓ 网络请求已完成")
                
                # 额外等待，确保动态内容加载
                await page.wait_for_timeout(3000)
                print("✓ 动态内容加载完成")
                
                # 如果 HTML 为空，重新获取
                if not result.html or len(result.html) < 100:
                    print("重新获取页面内容...")
                    html = await page.content()
                    if html:
                        result.html = html
            except Exception as e:
                print(f"等待页面加载时出现警告: {e}")
        
        if result.success:
            print("\n✓ 爬取成功！")
            
            # 获取页面内容
            html = result.html if hasattr(result, 'html') else None
            markdown = result.markdown if hasattr(result, 'markdown') else None
            title = result.metadata.get('title', 'N/A') if hasattr(result, 'metadata') else 'N/A'
            
            # 获取结构化数据（如果使用了提取策略）
            extracted_data = None
            if extraction_strategy and hasattr(result, 'extracted_content'):
                extracted_data = result.extracted_content
            elif hasattr(result, 'extracted_content'):
                extracted_data = result.extracted_content
            
            content_length = len(html or markdown or "")
            print(f"✓ 页面标题: {title}")
            print(f"✓ HTML 内容长度: {len(html or '')} 字符")
            print(f"✓ Markdown 内容长度: {len(markdown or '')} 字符")
            if extracted_data:
                print(f"✓ 结构化数据已提取")
            
            # 返回结果
            return {
                "success": True,
                "url": url,
                "html": html,
                "markdown": markdown,
                "title": title,
                "extracted_data": extracted_data,
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
    主函数：示例如何使用保存的登录态爬取页面并进行结构化整理
    """
    # 示例：爬取需要登录的页面
    target_url = input("请输入要爬取的页面URL（需要登录后才能访问）: ").strip()
    
    if not target_url:
        print("未提供URL，使用默认示例URL")
        target_url = "https://pubbuservice.alipay.com/"
    
    # 询问是否显示浏览器
    show_browser = input("是否显示浏览器窗口？(y/n，默认n): ").strip().lower() == 'y'
    
    # 询问是否需要结构化提取
    use_extraction = input("是否需要结构化提取？(y/n，默认n): ").strip().lower() == 'y'
    
    extract_schema = None
    if use_extraction:
        print("\n请输入结构化提取的 schema（JSON 格式），或按 Enter 使用默认 schema:")
        schema_input = input().strip()
        
        if schema_input:
            try:
                extract_schema = json.loads(schema_input)
            except json.JSONDecodeError:
                print("JSON 格式错误，使用默认 schema")
                extract_schema = None
        
        # 默认 schema 示例
        if not extract_schema:
            extract_schema = {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "页面标题"},
                    "content": {"type": "string", "description": "页面主要内容"},
                    "links": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "页面中的所有链接"
                    },
                    "text": {"type": "string", "description": "页面的纯文本内容"}
                },
                "required": ["title", "content"]
            }
            print("使用默认 schema 进行提取")
    
    # 执行爬取
    result = await scrape_with_session(
        target_url, 
        headless=not show_browser,
        extract_schema=extract_schema
    )
    
    # 保存结果
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
        
        # 保存结构化数据
        extracted_data = result.get("extracted_data")
        if extracted_data:
            json_file = Path("scrape_result_structured.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            print(f"✓ 结构化数据已保存到: {json_file}")


if __name__ == "__main__":
    asyncio.run(main())
