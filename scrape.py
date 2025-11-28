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
        print("正在加载页面...")
        
        # 获取 page 对象 - 在访问页面之前获取
        page = None
        
        # 调试：打印 crawler 对象的结构
        print("调试信息：检查 crawler 对象结构...")
        try:
            print(f"crawler 类型: {type(crawler)}")
            print(f"crawler 属性: {[attr for attr in dir(crawler) if not attr.startswith('__')]}")
            if hasattr(crawler, 'browser'):
                print(f"crawler.browser 类型: {type(crawler.browser)}")
                print(f"crawler.browser 属性: {[attr for attr in dir(crawler.browser) if not attr.startswith('__')]}")
        except Exception as e:
            print(f"调试信息获取失败: {e}")
        
        # 尝试多种方式获取 page 对象
        try:
            # 方式1: 通过 browser 属性
            if hasattr(crawler, 'browser') and crawler.browser:
                browser_obj = crawler.browser
                
                # 尝试不同的属性路径
                if hasattr(browser_obj, 'page') and browser_obj.page:
                    page = browser_obj.page
                elif hasattr(browser_obj, 'contexts') and browser_obj.contexts:
                    contexts = browser_obj.contexts
                    if contexts and len(contexts) > 0:
                        context = contexts[0]
                        if hasattr(context, 'pages'):
                            pages = context.pages
                            if pages and len(pages) > 0:
                                page = pages[-1]
                elif hasattr(browser_obj, 'context'):
                    context = browser_obj.context
                    if hasattr(context, 'pages'):
                        pages = context.pages
                        if pages and len(pages) > 0:
                            page = pages[-1]
                
                # 如果还没有，尝试通过 browser 的 _browser 属性（内部实现）
                if not page and hasattr(browser_obj, '_browser'):
                    browser = browser_obj._browser
                    if hasattr(browser, 'contexts'):
                        contexts = browser.contexts
                        if contexts and len(contexts) > 0:
                            pages = contexts[0].pages
                            if pages and len(pages) > 0:
                                page = pages[-1]
            
            # 方式2: 通过 _browser 属性（如果存在）
            if not page and hasattr(crawler, '_browser'):
                browser = crawler._browser
                if hasattr(browser, 'contexts'):
                    contexts = browser.contexts
                    if contexts and len(contexts) > 0:
                        pages = contexts[0].pages
                        if pages and len(pages) > 0:
                            page = pages[-1]
            
            # 方式3: 先访问一个页面来初始化 browser
            if not page:
                print("尝试初始化 browser 以获取 page 对象...")
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
                
        except Exception as e:
            print(f"获取 page 对象时出错: {e}")
            import traceback
            traceback.print_exc()
        
        # 访问目标页面
        print("正在访问目标页面...")
        result = await crawler.arun(url=url)
        
        # 再次尝试获取 page 对象（访问后可能更容易获取）
        if not page:
            print("访问后再次尝试获取 page 对象...")
            try:
                if hasattr(crawler, 'browser') and crawler.browser:
                    browser_obj = crawler.browser
                    print(f"找到 browser 对象，类型: {type(browser_obj)}")
                    
                    # 尝试所有可能的属性
                    if hasattr(browser_obj, 'contexts') and browser_obj.contexts:
                        contexts = browser_obj.contexts
                        print(f"找到 contexts，数量: {len(contexts)}")
                        if contexts and len(contexts) > 0:
                            pages = contexts[0].pages
                            print(f"找到 pages，数量: {len(pages) if pages else 0}")
                            if pages and len(pages) > 0:
                                page = pages[-1]
                                print(f"✓ 成功获取 page 对象")
                    elif hasattr(browser_obj, 'page') and browser_obj.page:
                        page = browser_obj.page
                        print(f"✓ 通过 browser.page 获取到 page 对象")
                    elif hasattr(browser_obj, 'context'):
                        context = browser_obj.context
                        if hasattr(context, 'pages'):
                            pages = context.pages
                            if pages and len(pages) > 0:
                                page = pages[-1]
                                print(f"✓ 通过 browser.context.pages 获取到 page 对象")
            except Exception as e:
                print(f"访问后获取 page 对象时出错: {e}")
                import traceback
                traceback.print_exc()
        
        # 等待 JavaScript 执行完成
        print("等待 JavaScript 执行完成...")
        if page:
            print("找到 page 对象，开始等待页面完全加载...")
            try:
                # 等待 DOM 加载
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                print("✓ DOM 内容已加载")
                
                # 等待网络空闲（确保 AJAX 请求完成）
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
                
                # 再次等待网络空闲，确保所有异步请求完成
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass
                
            except Exception as e:
                print(f"等待页面加载时出现错误: {e}")
                # 即使出错也继续，至少等待基本加载
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                    await page.wait_for_timeout(3000)
                except:
                    pass
        else:
            print("警告: 无法获取 page 对象，使用默认等待时间...")
            print("等待 10 秒以确保 JavaScript 执行完成...")
            await asyncio.sleep(10)  # 增加等待时间
        
        if result.success:
            print("\n✓ 爬取成功！")
            
            # 获取页面内容
            html = result.html if hasattr(result, 'html') else None
            markdown = result.markdown if hasattr(result, 'markdown') else None
            title = result.metadata.get('title', 'N/A') if hasattr(result, 'metadata') else 'N/A'
            
            # 如果 HTML 为空或过短，从 page 对象重新获取
            if not html or len(html) < 100:
                print("警告: HTML 内容为空或过短，尝试从 page 对象获取...")
                
                # 再次尝试获取 page 对象
                if not page:
                    try:
                        if hasattr(crawler, 'browser') and crawler.browser:
                            browser_obj = crawler.browser
                            if hasattr(browser_obj, 'contexts') and browser_obj.contexts:
                                contexts = browser_obj.contexts
                                if contexts and len(contexts) > 0:
                                    pages = contexts[0].pages
                                    if pages and len(pages) > 0:
                                        page = pages[-1]
                    except Exception as e:
                        print(f"重新获取 page 对象时出错: {e}")
                
                if page:
                    try:
                        html = await page.content()
                        title = await page.title()
                        print(f"✓ 从 page 对象获取到内容，长度: {len(html)} 字符")
                    except Exception as e:
                        print(f"从 page 对象获取内容时出错: {e}")
                else:
                    print("无法获取 page 对象，尝试其他方式...")
                    # 尝试通过 result 对象获取
                    if hasattr(result, 'page') and result.page:
                        try:
                            page = result.page
                            html = await page.content()
                            title = await page.title()
                            print(f"✓ 从 result.page 获取到内容，长度: {len(html)} 字符")
                        except Exception as e:
                            print(f"从 result.page 获取内容时出错: {e}")
            
            # 如果仍然为空，尝试获取渲染后的 HTML
            if not html or len(html) < 100:
                print("尝试获取渲染后的 HTML...")
                if page:
                    try:
                        # 获取渲染后的完整 HTML（包括 JavaScript 生成的内容）
                        html = await page.evaluate("() => document.documentElement.outerHTML")
                        print(f"✓ 获取到渲染后的 HTML，长度: {len(html)} 字符")
                    except Exception as e:
                        print(f"获取渲染后 HTML 时出错: {e}")
                elif hasattr(result, 'page') and result.page:
                    try:
                        html = await result.page.evaluate("() => document.documentElement.outerHTML")
                        print(f"✓ 从 result.page 获取到渲染后的 HTML，长度: {len(html)} 字符")
                    except Exception as e:
                        print(f"从 result.page 获取渲染后 HTML 时出错: {e}")
            
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
