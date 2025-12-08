"""
Sub Agent - 使用Playwright进行网页操作和数据抓取
"""
from playwright.async_api import async_playwright, Page, Browser
from typing import List, Dict, Any, Optional
import asyncio
import time
import json
import config
from bs4 import BeautifulSoup
import re


class SubAgent:
    """子Agent，负责具体的网页操作和数据抓取"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def initialize(self):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=config.HEADLESS,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = await context.new_page()
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
    
    async def search_xiaohongshu(self, keyword: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        在小红书搜索关键词并抓取文章
        
        Args:
            keyword: 搜索关键词
            max_pages: 最大翻页数
            
        Returns:
            文章列表
        """
        if not self.page:
            await self.initialize()
        
        articles = []
        
        try:
            # 访问小红书搜索页面
            search_url = f"{config.XIAOHONGSHU_BASE_URL}/search_result?keyword={keyword}"
            print(f"正在访问搜索页面: {search_url}")
            
            await self.page.goto(search_url, wait_until="networkidle", timeout=config.TIMEOUT)
            await asyncio.sleep(3)  # 等待页面加载
            
            # 处理可能的登录弹窗（如果有）
            await self._handle_login_popup()
            
            # 滚动页面以加载更多内容
            await self._scroll_page()
            
            # 抓取当前页面的文章
            page_articles = await self._extract_articles()
            articles.extend(page_articles)
            
            print(f"第1页抓取到 {len(page_articles)} 篇文章")
            
            # 翻页抓取
            for page_num in range(2, max_pages + 1):
                try:
                    # 尝试点击下一页或滚动加载更多
                    has_more = await self._load_more_content()
                    if not has_more:
                        print(f"没有更多内容，停止翻页")
                        break
                    
                    await asyncio.sleep(2)  # 等待内容加载
                    await self._scroll_page()
                    
                    page_articles = await self._extract_articles()
                    if page_articles:
                        articles.extend(page_articles)
                        print(f"第{page_num}页抓取到 {len(page_articles)} 篇文章")
                    else:
                        print(f"第{page_num}页没有抓取到内容，停止翻页")
                        break
                        
                except Exception as e:
                    print(f"翻页到第{page_num}页时出错: {e}")
                    break
            
            # 去重（基于标题和作者）
            articles = self._deduplicate_articles(articles)
            
            print(f"总共抓取到 {len(articles)} 篇不重复的文章")
            
        except Exception as e:
            print(f"搜索过程中出错: {e}")
        
        return articles
    
    async def _handle_login_popup(self):
        """处理登录弹窗"""
        try:
            # 尝试关闭可能的登录弹窗
            close_selectors = [
                'button[class*="close"]',
                '.close-btn',
                '[aria-label="关闭"]',
                'button:has-text("关闭")'
            ]
            
            for selector in close_selectors:
                try:
                    close_btn = await self.page.wait_for_selector(selector, timeout=2000)
                    if close_btn:
                        await close_btn.click()
                        await asyncio.sleep(1)
                        break
                except:
                    continue
        except:
            pass
    
    async def _scroll_page(self, scroll_times: int = 3):
        """滚动页面以加载更多内容"""
        for _ in range(scroll_times):
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.5)
    
    async def _load_more_content(self) -> bool:
        """尝试加载更多内容"""
        try:
            # 尝试找到"加载更多"或"查看更多"按钮
            load_more_selectors = [
                'button:has-text("加载更多")',
                'button:has-text("查看更多")',
                '.load-more',
                '[class*="load-more"]'
            ]
            
            for selector in load_more_selectors:
                try:
                    btn = await self.page.wait_for_selector(selector, timeout=2000)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(2)
                        return True
                except:
                    continue
            
            # 如果没有找到按钮，尝试滚动到底部触发自动加载
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            return True
            
        except Exception as e:
            print(f"加载更多内容时出错: {e}")
            return False
    
    async def _extract_articles(self) -> List[Dict[str, Any]]:
        """从当前页面提取文章信息"""
        articles = []
        
        try:
            # 获取页面HTML
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 小红书文章通常在这些选择器中
            # 注意：实际的选择器需要根据小红书的实际HTML结构调整
            article_selectors = [
                '.note-item',
                '[class*="note"]',
                '[class*="card"]',
                'article',
                '.feed-item'
            ]
            
            found_articles = []
            for selector in article_selectors:
                elements = soup.select(selector)
                if elements:
                    found_articles = elements
                    break
            
            # 如果找不到特定选择器，尝试通过链接特征查找
            if not found_articles:
                # 查找包含小红书文章链接的元素
                links = soup.find_all('a', href=re.compile(r'/explore/|/discovery/'))
                found_articles = [link.parent for link in links if link.parent]
            
            for element in found_articles[:20]:  # 限制每页最多20篇
                try:
                    article = await self._parse_article_element(element)
                    if article:
                        articles.append(article)
                except Exception as e:
                    print(f"解析文章元素时出错: {e}")
                    continue
            
            # 如果BeautifulSoup解析失败，尝试使用JavaScript提取
            if not articles:
                articles = await self._extract_with_javascript()
            
        except Exception as e:
            print(f"提取文章时出错: {e}")
        
        return articles
    
    async def _parse_article_element(self, element) -> Optional[Dict[str, Any]]:
        """解析单个文章元素"""
        try:
            article = {}
            
            # 提取标题
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', '.title', '[class*="title"]'])
            article['title'] = title_elem.get_text(strip=True) if title_elem else "无标题"
            
            # 提取链接
            link_elem = element.find('a', href=True)
            if link_elem:
                href = link_elem.get('href', '')
                if not href.startswith('http'):
                    href = config.XIAOHONGSHU_BASE_URL + href
                article['url'] = href
            else:
                article['url'] = ""
            
            # 提取作者
            author_elem = element.find(['.author', '[class*="author"]', '[class*="user"]'])
            article['author'] = author_elem.get_text(strip=True) if author_elem else "未知作者"
            
            # 提取点赞数
            likes_text = ""
            likes_elem = element.find(string=re.compile(r'点赞|like|👍'))
            if likes_elem:
                parent = likes_elem.parent
                likes_text = parent.get_text() if parent else ""
            else:
                likes_elems = element.find_all(string=re.compile(r'\d+'))
                for elem in likes_elems:
                    if 'k' in elem.lower() or 'w' in elem.lower() or elem.isdigit():
                        likes_text = elem
                        break
            
            article['likes'] = self._parse_number(likes_text)
            
            # 提取收藏数
            collections_text = ""
            collections_elem = element.find(string=re.compile(r'收藏|collect|⭐'))
            if collections_elem:
                parent = collections_elem.parent
                collections_text = parent.get_text() if parent else ""
            else:
                # 尝试从数字中推断
                numbers = re.findall(r'\d+[kw]?', element.get_text())
                if len(numbers) > 1:
                    collections_text = numbers[1]
            
            article['collections'] = self._parse_number(collections_text)
            
            # 提取内容预览
            content_elem = element.find(['.content', '.desc', '[class*="content"]', 'p'])
            article['content_preview'] = content_elem.get_text(strip=True)[:200] if content_elem else ""
            
            # 提取图片
            img_elem = element.find('img', src=True)
            article['cover_image'] = img_elem.get('src', '') if img_elem else ""
            
            # 添加时间戳
            article['crawled_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 只有包含有效信息的文章才返回
            if article.get('title') and article.get('title') != "无标题":
                return article
            
        except Exception as e:
            print(f"解析文章元素详细出错: {e}")
        
        return None
    
    async def _extract_with_javascript(self) -> List[Dict[str, Any]]:
        """使用JavaScript在浏览器中提取文章信息"""
        articles = []
        
        try:
            # 执行JavaScript提取数据
            js_code = """
            () => {
                const articles = [];
                const cards = document.querySelectorAll('[class*="note"], [class*="card"], article');
                
                cards.forEach((card, index) => {
                    if (index >= 20) return;
                    
                    const title = card.querySelector('h1, h2, h3, h4, [class*="title"]')?.textContent?.trim() || '';
                    const link = card.querySelector('a')?.href || '';
                    const author = card.querySelector('[class*="author"], [class*="user"]')?.textContent?.trim() || '';
                    const img = card.querySelector('img')?.src || '';
                    const text = card.textContent || '';
                    
                    // 尝试提取数字（点赞、收藏）
                    const numbers = text.match(/\\d+[kw]?/g) || [];
                    const likes = numbers[0] ? parseInt(numbers[0].replace(/[kw]/i, '')) * (numbers[0].toLowerCase().includes('k') ? 1000 : numbers[0].toLowerCase().includes('w') ? 10000 : 1) : 0;
                    const collections = numbers[1] ? parseInt(numbers[1].replace(/[kw]/i, '')) * (numbers[1].toLowerCase().includes('k') ? 1000 : numbers[1].toLowerCase().includes('w') ? 10000 : 1) : 0;
                    
                    if (title) {
                        articles.push({
                            title: title,
                            url: link,
                            author: author,
                            likes: likes,
                            collections: collections,
                            cover_image: img,
                            content_preview: text.substring(0, 200)
                        });
                    }
                });
                
                return articles;
            }
            """
            
            articles = await self.page.evaluate(js_code)
            
        except Exception as e:
            print(f"JavaScript提取失败: {e}")
        
        return articles
    
    def _parse_number(self, text: str) -> int:
        """解析数字文本（支持k、w等单位）"""
        if not text:
            return 0
        
        text = text.strip().lower()
        # 提取数字
        match = re.search(r'(\d+\.?\d*)[kw]?', text)
        if match:
            num = float(match.group(1))
            if 'w' in text or '万' in text:
                return int(num * 10000)
            elif 'k' in text or '千' in text:
                return int(num * 1000)
            else:
                return int(num)
        return 0
    
    def _deduplicate_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重文章"""
        seen = set()
        unique_articles = []
        
        for article in articles:
            # 使用标题和作者作为唯一标识
            key = (article.get('title', ''), article.get('author', ''))
            if key not in seen and key[0]:  # 确保标题不为空
                seen.add(key)
                unique_articles.append(article)
        
        return unique_articles
