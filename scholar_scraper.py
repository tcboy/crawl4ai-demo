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
    
    def __init__(self, proxy: Optional[str] = None):
        """
        初始化爬虫
        
        Args:
            proxy: socks5代理地址，格式: socks5://host:port
        """
        self.proxy = proxy
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def init_browser(self):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        
        # 配置浏览器选项
        launch_options = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-setuid-sandbox"]
        }
        
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
    
    async def search_scholar(self, author_name: str) -> List[Dict]:
        """
        搜索指定作者的论文
        
        Args:
            author_name: 作者姓名
            
        Returns:
            论文列表，每个论文包含标题、摘要、引用次数等信息
        """
        if not self.page:
            await self.init_browser()
        
        try:
            # 访问Google Scholar
            print(f"正在访问 Google Scholar...")
            await self.page.goto("https://scholar.google.com/", wait_until="networkidle", timeout=30000)
            
            # 等待搜索框出现
            print(f"正在搜索作者: {author_name}")
            search_box = await self.page.wait_for_selector('input[name="q"]', timeout=10000)
            
            # 输入搜索关键词（使用作者名搜索）
            await search_box.fill(f'author:"{author_name}"')
            await search_box.press("Enter")
            
            # 等待搜索结果加载
            await self.page.wait_for_selector('div.gs_ri', timeout=15000)
            
            # 等待页面稳定
            await asyncio.sleep(2)
            
            # 提取论文信息
            papers = await self.extract_papers()
            
            return papers
            
        except Exception as e:
            print(f"搜索过程中出现错误: {str(e)}")
            raise
    
    async def extract_papers(self) -> List[Dict]:
        """
        从搜索结果页面提取论文信息
        
        Returns:
            论文信息列表
        """
        papers = []
        
        try:
            # 查找所有论文条目
            paper_elements = await self.page.query_selector_all('div.gs_ri')
            
            print(f"找到 {len(paper_elements)} 篇论文")
            
            for idx, element in enumerate(paper_elements[:10]):  # 只取前10篇
                try:
                    paper_info = {}
                    
                    # 提取标题
                    title_elem = await element.query_selector('h3.gs_rt a, h3.gs_rt')
                    if title_elem:
                        title = await title_elem.inner_text()
                        paper_info['title'] = title.strip()
                    else:
                        paper_info['title'] = "未知标题"
                    
                    # 提取作者和发表信息
                    author_elem = await element.query_selector('div.gs_a')
                    if author_elem:
                        author_info = await author_elem.inner_text()
                        paper_info['authors_info'] = author_info.strip()
                    else:
                        paper_info['authors_info'] = "未知"
                    
                    # 提取摘要
                    abstract_elem = await element.query_selector('div.gs_rs')
                    if abstract_elem:
                        abstract = await abstract_elem.inner_text()
                        paper_info['abstract'] = abstract.strip()
                    else:
                        paper_info['abstract'] = "无摘要"
                    
                    # 提取引用次数
                    cited_elem = await element.query_selector('a[href*="cites"]')
                    if cited_elem:
                        cited_text = await cited_elem.inner_text()
                        # 提取数字
                        import re
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
  python scholar_scraper.py "John Smith"
  python scholar_scraper.py "John Smith" --proxy socks5://127.0.0.1:1080
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
    
    args = parser.parse_args()
    
    scraper = ScholarScraper(proxy=args.proxy)
    
    try:
        # 搜索论文
        papers = await scraper.search_scholar(args.author_name)
        
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
