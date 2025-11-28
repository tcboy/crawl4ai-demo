"""
爬取脚本：使用保存的登录态爬取需要登录后才能访问的页面
完全使用 Playwright 实现
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
    
    # 使用 Playwright 直接控制浏览器
    async with async_playwright() as p:
        # 启动浏览器
        print("正在启动浏览器...")
        browser = await p.chromium.launch(headless=headless)
        
        # 创建新的 context
        context = await browser.new_context()
        
        # 先访问目标域名以建立 context
        base_url = f"{parsed_url.scheme}://{cookie_domain}"
        page = await context.new_page()
        
        print(f"正在初始化浏览器 context: {base_url}")
        await page.goto(base_url)
        
        # 添加 cookies
        print("正在设置 cookies...")
        await context.add_cookies(cookies)
        print("✓ Cookies 设置成功")
        
        # 访问目标页面
        print(f"正在访问目标页面: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        print("✓ 页面已加载")
        
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
        
        # 再次等待网络空闲，确保所有异步请求完成
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
        
        # 获取所有链接
        try:
            links = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(link => link.href).filter(href => href);
                }
            """)
        except:
            links = []
        
        # 获取所有图片
        try:
            images = await page.evaluate("""
                () => {
                    const imgs = Array.from(document.querySelectorAll('img[src]'));
                    return imgs.map(img => img.src).filter(src => src);
                }
            """)
        except:
            images = []
        
        # 截图（可选）
        screenshot = None
        if not headless:
            try:
                screenshot = await page.screenshot(full_page=True)
                print("✓ 已保存截图")
            except Exception as e:
                print(f"截图保存失败: {e}")
        
        # 关闭浏览器
        await browser.close()
        
        print("\n✓ 爬取成功！")
        print(f"✓ 页面标题: {title}")
        print(f"✓ HTML 内容长度: {len(html)} 字符")
        print(f"✓ 文本内容长度: {len(body_text)} 字符")
        print(f"✓ 链接数量: {len(links)}")
        print(f"✓ 图片数量: {len(images)}")
        
        # 返回结果
        return {
            "success": True,
            "url": url,
            "html": html,
            "text": body_text,
            "title": title,
            "links": links,
            "images": images,
            "screenshot": screenshot
        }


async def main():
    """
    主函数：示例如何使用保存的登录态爬取页面
    """
    # 示例：爬取需要登录的页面
    target_url = input("请输入要爬取的页面URL（需要登录后才能访问）: ").strip()
    
    if not target_url:
        print("未提供URL，使用默认示例URL")
        target_url = "https://pubbuservice.alipay.com/"
    
    # 询问是否显示浏览器
    show_browser = input("是否显示浏览器窗口？(y/n，默认n): ").strip().lower() == 'y'
    
    # 执行爬取
    result = await scrape_with_session(target_url, headless=not show_browser)
    
    # 保存结果
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
        
        # 保存结构化数据（JSON）
        structured_data = {
            "url": result.get("url"),
            "title": result.get("title"),
            "text_length": len(text_content),
            "html_length": len(html_content),
            "links_count": len(result.get("links", [])),
            "images_count": len(result.get("images", [])),
            "links": result.get("links", []),
            "images": result.get("images", [])
        }
        
        json_file = Path("scrape_result.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, indent=2, ensure_ascii=False)
        print(f"✓ 结构化数据已保存到: {json_file}")


if __name__ == "__main__":
    asyncio.run(main())
