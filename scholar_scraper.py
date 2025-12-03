#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Scholar 论文搜索机器人
使用Playwright自动搜索指定人名的论文、摘要和引用次数
支持socks5代理
"""

import asyncio
import argparse
import json
import sys
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext


class ScholarScraper:
    """Google Scholar 搜索爬虫类"""
    
    def __init__(self, proxy: Optional[str] = None, headless: bool = False):
        """
        初始化爬虫
        
        Args:
            proxy: socks5代理地址，格式: socks5://host:port
            headless: 是否使用无头模式（False表示显示浏览器窗口）
        """
        self.proxy = proxy
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def init_browser(self):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        
        # 配置浏览器选项
        launch_options = {
            "headless": self.headless,
            "args": ["--no-sandbox", "--disable-setuid-sandbox"]
        }
        
        # 如果不是无头模式，添加一些额外的窗口选项
        if not self.headless:
            launch_options["slow_mo"] = 500  # 减慢操作速度，方便观察
            print("浏览器窗口将显示，方便调试...")
        
        self.browser = await playwright.chromium.launch(**launch_options)
        
        # 创建浏览器上下文
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # 如果提供了代理，在context级别设置代理
        # Playwright支持socks5代理，格式: socks5://host:port
        if self.proxy:
            context_options["proxy"] = {"server": self.proxy}
            print(f"使用代理: {self.proxy}")
        
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
    
    async def search_scholar(self, author_name: str, debug: bool = False) -> List[Dict]:
        """
        搜索指定作者的论文
        
        Args:
            author_name: 作者姓名
            debug: 是否启用调试模式（保存截图和HTML）
            
        Returns:
            论文列表，每个论文包含标题、摘要、引用次数等信息
        """
        if not self.page:
            await self.init_browser()
        
        try:
            # 访问Google Scholar
            print(f"正在访问 Google Scholar...")
            await self.page.goto("https://scholar.google.com/", wait_until="domcontentloaded", timeout=60000)
            
            # 等待页面加载完成
            await asyncio.sleep(3)
            
            # 调试：保存页面截图和HTML
            if debug:
                await self.page.screenshot(path="debug_scholar_homepage.png")
                html_content = await self.page.content()
                with open("debug_scholar_homepage.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("调试信息已保存: debug_scholar_homepage.png 和 debug_scholar_homepage.html")
            
            # 尝试多个可能的搜索框选择器
            print(f"正在查找搜索框...")
            search_box = None
            search_selectors = [
                'input[name="q"]',
                'input[type="text"][name="q"]',
                'input.gs_in_txt',
                'input#gs_hdr_tsi',
                'textarea[name="q"]',
                'input[aria-label*="搜索"]',
                'input[aria-label*="Search"]',
            ]
            
            for selector in search_selectors:
                try:
                    search_box = await self.page.wait_for_selector(selector, timeout=5000, state="visible")
                    if search_box:
                        print(f"找到搜索框，使用选择器: {selector}")
                        break
                except:
                    continue
            
            if not search_box:
                # 如果还是找不到，尝试查找所有input元素
                print("尝试查找所有输入框...")
                all_inputs = await self.page.query_selector_all('input[type="text"], textarea')
                print(f"找到 {len(all_inputs)} 个输入框")
                if all_inputs:
                    # 使用第一个输入框
                    search_box = all_inputs[0]
                    print("使用第一个找到的输入框")
                else:
                    # 最后尝试：直接导航到搜索结果页面
                    print("无法找到搜索框，尝试直接访问搜索结果页面...")
                    search_url = f"https://scholar.google.com/scholar?q=author:\"{author_name}\""
                    await self.page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(3)
                    
                    if debug:
                        await self.page.screenshot(path="debug_search_results.png")
                        html_content = await self.page.content()
                        with open("debug_search_results.html", "w", encoding="utf-8") as f:
                            f.write(html_content)
                    
                    # 直接提取论文
                    papers = await self.extract_papers()
                    return papers
            
            # 输入搜索关键词（使用作者名搜索）
            print(f"正在搜索作者: {author_name}")
            await search_box.fill(f'author:"{author_name}"')
            await asyncio.sleep(1)
            await search_box.press("Enter")
            
            # 等待搜索结果加载
            print("等待搜索结果加载...")
            try:
                await self.page.wait_for_selector('div.gs_ri, div.gs_r', timeout=20000)
            except:
                # 尝试其他可能的结果选择器
                await asyncio.sleep(3)
            
            # 等待页面稳定
            await asyncio.sleep(2)
            
            if debug:
                await self.page.screenshot(path="debug_search_results.png")
                html_content = await self.page.content()
                with open("debug_search_results.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("调试信息已保存: debug_search_results.png 和 debug_search_results.html")
            
            # 提取论文信息
            papers = await self.extract_papers()
            
            return papers
            
        except Exception as e:
            print(f"搜索过程中出现错误: {str(e)}")
            # 保存错误时的页面状态
            try:
                await self.page.screenshot(path="error_screenshot.png")
                html_content = await self.page.content()
                with open("error_page.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("错误页面已保存: error_screenshot.png 和 error_page.html")
            except:
                pass
            raise
    
    async def extract_papers(self) -> List[Dict]:
        """
        从搜索结果页面提取论文信息
        
        Returns:
            论文信息列表
        """
        papers = []
        
        try:
            # 尝试多个可能的论文条目选择器
            paper_elements = []
            paper_selectors = [
                'div.gs_ri',
                'div.gs_r',
                'div[data-rp]',
                'div.gs_scl',
            ]
            
            for selector in paper_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    paper_elements = elements
                    print(f"使用选择器 '{selector}' 找到 {len(paper_elements)} 篇论文")
                    break
            
            if not paper_elements:
                print("警告: 未找到论文条目，尝试查找所有可能的论文容器...")
                # 尝试查找所有包含论文信息的div
                all_divs = await self.page.query_selector_all('div')
                print(f"页面共有 {len(all_divs)} 个div元素")
            
            if not paper_elements:
                print("未找到任何论文条目")
                return papers
            
            for idx, element in enumerate(paper_elements[:10]):  # 只取前10篇
                try:
                    paper_info = {}
                    
                    # 提取标题 - 尝试多个选择器
                    title_elem = None
                    title_selectors = [
                        'h3.gs_rt a',
                        'h3.gs_rt',
                        'h3 a',
                        'a[data-clk-atid]',
                        '.gs_rt a',
                    ]
                    for selector in title_selectors:
                        title_elem = await element.query_selector(selector)
                        if title_elem:
                            break
                    
                    if title_elem:
                        title = await title_elem.inner_text()
                        paper_info['title'] = title.strip()
                    else:
                        paper_info['title'] = "未知标题"
                    
                    # 提取作者和发表信息 - 尝试多个选择器
                    author_elem = None
                    author_selectors = [
                        'div.gs_a',
                        '.gs_a',
                        'div[class*="gs_a"]',
                    ]
                    for selector in author_selectors:
                        author_elem = await element.query_selector(selector)
                        if author_elem:
                            break
                    
                    if author_elem:
                        author_info = await author_elem.inner_text()
                        paper_info['authors_info'] = author_info.strip()
                    else:
                        paper_info['authors_info'] = "未知"
                    
                    # 提取摘要 - 尝试多个选择器
                    abstract_elem = None
                    abstract_selectors = [
                        'div.gs_rs',
                        '.gs_rs',
                        'div[class*="gs_rs"]',
                    ]
                    for selector in abstract_selectors:
                        abstract_elem = await element.query_selector(selector)
                        if abstract_elem:
                            break
                    
                    if abstract_elem:
                        abstract = await abstract_elem.inner_text()
                        paper_info['abstract'] = abstract.strip()
                    else:
                        paper_info['abstract'] = "无摘要"
                    
                    # 提取引用次数 - 尝试多个选择器
                    import re
                    cited_elem = None
                    cited_selectors = [
                        'a[href*="cites"]',
                        'a[href*="scholar?cites"]',
                        '.gs_fl a',
                    ]
                    for selector in cited_selectors:
                        cited_elem = await element.query_selector(selector)
                        if cited_elem:
                            break
                    
                    if cited_elem:
                        cited_text = await cited_elem.inner_text()
                        # 提取数字
                        cited_match = re.search(r'(\d+)', cited_text)
                        if cited_match:
                            paper_info['cited_by'] = int(cited_match.group(1))
                        else:
                            paper_info['cited_by'] = 0
                    else:
                        paper_info['cited_by'] = 0
                    
                    # 提取年份（如果存在）
                    year_elem = await element.query_selector('span.gs_oph')
                    if year_elem:
                        year_text = await year_elem.inner_text()
                        paper_info['year'] = year_text.strip()
                    else:
                        paper_info['year'] = "未知"
                    
                    papers.append(paper_info)
                    print(f"已提取第 {idx + 1} 篇论文: {paper_info['title'][:50]}...")
                    
                except Exception as e:
                    print(f"提取第 {idx + 1} 篇论文时出错: {str(e)}")
                    continue
            
        except Exception as e:
            print(f"提取论文信息时出错: {str(e)}")
        
        return papers
    
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Google Scholar 论文搜索机器人",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scholar_scraper.py "John Smith"  # 默认显示浏览器窗口
  python scholar_scraper.py "John Smith" --proxy socks5://127.0.0.1:1080
  python scholar_scraper.py "John Smith" --headless  # 无头模式（不显示窗口）
  python scholar_scraper.py "John Smith" --debug  # 启用调试模式（保存截图）
  python scholar_scraper.py "John Smith" --proxy socks5://127.0.0.1:1080 --output results.json
        """
    )
    
    parser.add_argument(
        "author_name",
        type=str,
        help="要搜索的作者姓名"
    )
    
    parser.add_argument(
        "--proxy",
        type=str,
        default=None,
        help="socks5代理地址，格式: socks5://host:port"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出JSON文件路径（可选）"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式（保存页面截图和HTML）"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="使用无头模式（不显示浏览器窗口，默认显示窗口）"
    )
    
    args = parser.parse_args()
    
    scraper = ScholarScraper(proxy=args.proxy, headless=args.headless)
    
    try:
        # 搜索论文
        papers = await scraper.search_scholar(args.author_name, debug=args.debug)
        
        if not papers:
            print("未找到任何论文")
            return
        
        # 输出结果
        print("\n" + "="*80)
        print(f"找到 {len(papers)} 篇论文")
        print("="*80 + "\n")
        
        for idx, paper in enumerate(papers, 1):
            print(f"论文 {idx}:")
            print(f"  标题: {paper.get('title', '未知')}")
            print(f"  作者信息: {paper.get('authors_info', '未知')}")
            print(f"  年份: {paper.get('year', '未知')}")
            print(f"  引用次数: {paper.get('cited_by', 0)}")
            print(f"  摘要: {paper.get('abstract', '无摘要')[:200]}...")
            print("-" * 80)
        
        # 如果指定了输出文件，保存为JSON
        if args.output:
            output_data = {
                "author": args.author_name,
                "total_papers": len(papers),
                "papers": papers
            }
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {args.output}")
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
