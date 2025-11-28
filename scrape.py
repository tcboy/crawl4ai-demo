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
        
        # 优先使用 Playwright 直接获取完整内容
        print("使用 Playwright 直接访问页面以获取完整内容...")
        
        # 获取 page 对象
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
                elif hasattr(browser_obj, '_browser'):
                    browser = browser_obj._browser
                    if hasattr(browser, 'contexts') and browser.contexts:
                        contexts = browser.contexts
                        if contexts and len(contexts) > 0:
                            pages = contexts[0].pages
                            if pages and len(pages) > 0:
                                page = pages[-1]
        except Exception as e:
            print(f"获取 page 对象时出错: {e}")
        
        # 如果获取不到 page，先访问一次以创建 page
        if not page:
            print("未找到 page 对象，先访问页面以创建...")
            try:
                temp_result = await crawler.arun(url=base_url)
                # 再次尝试获取
                if hasattr(crawler, 'browser') and crawler.browser:
                    browser_obj = crawler.browser
                    if hasattr(browser_obj, 'contexts') and browser_obj.contexts:
                        contexts = browser_obj.contexts
                        if contexts and len(contexts) > 0:
                            pages = contexts[0].pages
                            if pages and len(pages) > 0:
                                page = pages[-1]
            except:
                pass
        
        # 使用 Playwright 直接访问页面并获取完整内容
        html = None
        title = None
        markdown = None
        
        if page:
            print("找到 page 对象，使用 Playwright 访问页面...")
            try:
                # 直接使用 page 对象访问
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                print("✓ 页面已加载")
                
                # 等待网络空闲
                print("等待网络请求完成...")
                await page.wait_for_load_state("networkidle", timeout=20000)
                print("✓ 网络请求已完成")
                
                # 额外等待，确保动态内容加载
                print("等待动态内容加载（5秒）...")
                await page.wait_for_timeout(5000)
                
                # 等待页面有实际内容
                print("检查页面内容...")
                max_retries = 3
                for i in range(max_retries):
                    try:
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
                
                # 直接从 page 获取完整内容
                print("正在获取页面内容（使用 Playwright）...")
                html = await page.content()
                title = await page.title()
                
                # 获取 markdown（使用 crawl4ai 的转换功能）
                try:
                    from crawl4ai import Markdownify
                    markdownify = Markdownify()
                    markdown = markdownify.markdownify(html)
                    print("✓ 已转换为 Markdown")
                except Exception as e:
                    print(f"Markdown 转换失败: {e}，使用文本提取...")
                    try:
                        markdown = await page.evaluate("() => document.body.innerText")
                    except:
                        pass
                
                print(f"✓ 获取到完整内容，HTML 长度: {len(html)} 字符")
                
            except Exception as e:
                print(f"使用 Playwright 访问时出错: {e}")
                import traceback
                traceback.print_exc()
        
        # 如果 Playwright 获取失败，回退到 crawl4ai
        extracted_data = None
        if not html or len(html) < 100:
            print("Playwright 获取内容失败，回退到使用 crawl4ai...")
            result = await crawler.arun(url=url, extraction_strategy=extraction_strategy)
            if result.success:
                html = result.html if hasattr(result, 'html') else None
                markdown = result.markdown if hasattr(result, 'markdown') else None
                title = result.metadata.get('title', 'N/A') if hasattr(result, 'metadata') else 'N/A'
                extracted_data = result.extracted_content if hasattr(result, 'extracted_content') else None
            else:
                # 创建失败的结果
                class MockResult:
                    def __init__(self):
                        self.success = False
                        self.error_message = result.error_message if hasattr(result, 'error_message') else "未知错误"
                result = MockResult()
        else:
            # 使用 crawl4ai 对获取到的 HTML 进行结构化提取
            if extract_schema and html:
                print("使用 crawl4ai 对内容进行结构化整理...")
                try:
                    # 使用 crawl4ai 的提取策略处理 HTML
                    if extraction_strategy:
                        # 创建一个临时的 result 对象用于提取
                        from crawl4ai.models import CrawlResult
                        temp_result = CrawlResult(
                            url=url,
                            html=html,
                            markdown=markdown,
                            metadata={"title": title} if title else {}
                        )
                        
                        # 执行提取
                        extracted_data = await extraction_strategy.extract(temp_result)
                        if extracted_data:
                            print("✓ 结构化数据提取成功")
                        else:
                            extracted_data = None
                    else:
                        extracted_data = None
                except Exception as e:
                    print(f"结构化提取时出错: {e}")
                    import traceback
                    traceback.print_exc()
                    extracted_data = None
            else:
                extracted_data = None
            
            # 创建 result 对象
            class MockResult:
                def __init__(self):
                    self.success = True
                    self.html = html
                    self.markdown = markdown
                    self.metadata = {"title": title} if title else {}
                    self.extracted_content = extracted_data
                    self.screenshot = None
            
            result = MockResult()
        
        if result.success:
            print("\n✓ 爬取成功！")
            
            # 获取页面内容
            html = result.html if hasattr(result, 'html') else None
            markdown = result.markdown if hasattr(result, 'markdown') else None
            title = result.metadata.get('title', 'N/A') if hasattr(result, 'metadata') else 'N/A'
            
            # 获取结构化数据（如果使用了提取策略）
            extracted_data = None
            if hasattr(result, 'extracted_content'):
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
