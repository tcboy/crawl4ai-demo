"""小红书爬虫工具 - 基于Playwright"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from bs4 import BeautifulSoup
from utils.config import Config

class XiaohongshuScraper:
    """小红书爬虫工具类"""
    
    def __init__(self, headless: bool = None, timeout: int = None):
        self.headless = headless if headless is not None else Config.HEADLESS
        self.timeout = timeout or Config.BROWSER_TIMEOUT
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
    
    async def init_browser(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # 创建上下文，模拟真实用户
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai'
        )
        
        self.page = await self.context.new_page()
        # 隐藏webdriver特征
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
    
    async def login(self, username: str = None, password: str = None) -> bool:
        """登录小红书"""
        username = username or Config.XHS_USERNAME
        password = password or Config.XHS_PASSWORD
        
        if not username or not password:
            print("警告: 未提供账号密码，将尝试以游客模式访问")
            return False
        
        try:
            if not self.page:
                await self.init_browser()
            
            print(f"正在访问登录页面: {Config.XHS_LOGIN_URL}")
            await self.page.goto(Config.XHS_LOGIN_URL, wait_until="networkidle", timeout=self.timeout)
            await asyncio.sleep(2)
            
            # 等待登录表单出现
            try:
                # 尝试找到账号密码登录方式
                account_login_btn = self.page.locator("text=账号密码登录").or_(self.page.locator("text=密码登录"))
                if await account_login_btn.count() > 0:
                    await account_login_btn.first.click()
                    await asyncio.sleep(1)
            except:
                pass
            
            # 输入用户名
            username_input = self.page.locator('input[type="text"]').or_(self.page.locator('input[placeholder*="手机号"]')).or_(self.page.locator('input[placeholder*="账号"]'))
            await username_input.first.fill(username)
            await asyncio.sleep(0.5)
            
            # 输入密码
            password_input = self.page.locator('input[type="password"]')
            await password_input.first.fill(password)
            await asyncio.sleep(0.5)
            
            # 点击登录按钮
            login_btn = self.page.locator("button:has-text('登录')").or_(self.page.locator("button[type='submit']"))
            await login_btn.first.click()
            
            # 等待登录完成（可能需要验证码）
            print("等待登录完成...")
            await asyncio.sleep(5)
            
            # 检查是否登录成功（通过检查URL或页面元素）
            current_url = self.page.url
            if "login" not in current_url.lower():
                self.is_logged_in = True
                print("登录成功！")
                # 保存登录状态
                await self.context.storage_state(path=".auth/xhs_state.json")
                return True
            else:
                # 可能需要手动处理验证码
                print("可能需要处理验证码，请在浏览器中手动完成登录...")
                print("等待30秒，请手动完成登录...")
                await asyncio.sleep(30)
                
                current_url = self.page.url
                if "login" not in current_url.lower():
                    self.is_logged_in = True
                    await self.context.storage_state(path=".auth/xhs_state.json")
                    print("登录成功！")
                    return True
                
                return False
                
        except Exception as e:
            print(f"登录过程中出错: {e}")
            return False
    
    async def load_auth_state(self) -> bool:
        """加载已保存的登录状态"""
        try:
            from pathlib import Path
            auth_file = Path(".auth/xhs_state.json")
            if auth_file.exists() and self.playwright:
                # 如果已有context，先关闭
                if self.context:
                    await self.context.close()
                
                self.context = await self.browser.new_context(
                    storage_state=str(auth_file),
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='zh-CN',
                    timezone_id='Asia/Shanghai'
                )
                self.page = await self.context.new_page()
                # 隐藏webdriver特征
                await self.page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                self.is_logged_in = True
                print("已加载保存的登录状态")
                return True
        except Exception as e:
            print(f"加载登录状态失败: {e}")
        return False
    
    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """搜索小红书内容"""
        if not self.page:
            await self.init_browser()
            # 尝试加载已保存的登录状态
            if not await self.load_auth_state():
                await self.login()
        
        try:
            # 构建搜索URL
            search_url = f"{Config.XHS_SEARCH_URL}?keyword={keyword}"
            print(f"正在搜索: {keyword}")
            print(f"访问URL: {search_url}")
            
            await self.page.goto(search_url, wait_until="networkidle", timeout=self.timeout)
            await asyncio.sleep(3)
            
            articles = []
            scroll_count = 0
            max_scrolls = 10  # 最多滚动10次
            
            while len(articles) < max_results and scroll_count < max_scrolls:
                # 等待内容加载
                await asyncio.sleep(2)
                
                # 获取页面内容
                content = await self.page.content()
                soup = BeautifulSoup(content, 'lxml')
                
                # 解析文章卡片（小红书使用特定的class）
                # 注意：小红书的DOM结构可能会变化，需要根据实际情况调整
                note_cards = self.page.locator('[class*="note-item"]').or_(
                    self.page.locator('[class*="note-card"]')
                ).or_(
                    self.page.locator('a[href*="/explore/"]')
                )
                
                card_count = await note_cards.count()
                print(f"找到 {card_count} 个内容卡片")
                
                # 提取每个卡片的信息
                for i in range(min(card_count, max_results - len(articles))):
                    try:
                        card = note_cards.nth(i)
                        
                        # 获取链接
                        link_elem = card.locator('a').first
                        href = await link_elem.get_attribute('href') if await link_elem.count() > 0 else None
                        if href and not href.startswith('http'):
                            href = f"{Config.XHS_BASE_URL}{href}"
                        
                        # 获取标题
                        title_elem = card.locator('[class*="title"]').or_(card.locator('h3')).or_(card.locator('h2'))
                        title = await title_elem.first.inner_text() if await title_elem.count() > 0 else "无标题"
                        
                        # 获取封面图
                        img_elem = card.locator('img').first
                        cover_img = await img_elem.get_attribute('src') if await img_elem.count() > 0 else None
                        
                        # 获取点赞数、收藏数等
                        like_elem = card.locator('[class*="like"]').or_(card.locator('text=/\\d+/'))
                        like_text = await like_elem.first.inner_text() if await like_elem.count() > 0 else "0"
                        likes = self._parse_count(like_text)
                        
                        # 获取作者信息
                        author_elem = card.locator('[class*="author"]').or_(card.locator('[class*="user"]'))
                        author = await author_elem.first.inner_text() if await author_elem.count() > 0 else "未知"
                        
                        # 提取文章ID
                        article_id = href.split('/')[-1] if href else None
                        
                        article = {
                            "article_id": article_id,
                            "note_id": article_id,
                            "title": title.strip(),
                            "author": author.strip(),
                            "url": href,
                            "cover_img": cover_img,
                            "likes": likes,
                            "collections": 0,  # 收藏数需要进入详情页获取
                            "keyword": keyword,
                            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # 避免重复
                        if not any(a.get("article_id") == article_id for a in articles):
                            articles.append(article)
                            print(f"已提取文章: {title[:30]}... (点赞: {likes})")
                    
                    except Exception as e:
                        print(f"提取第 {i} 个卡片时出错: {e}")
                        continue
                
                # 滚动加载更多
                if len(articles) < max_results:
                    await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    scroll_count += 1
                    await asyncio.sleep(2)
            
            # 获取详细数据（点赞、收藏等）
            print(f"开始获取详细信息...")
            detailed_articles = []
            for article in articles[:max_results]:
                try:
                    detailed = await self.get_article_detail(article["url"])
                    if detailed:
                        article.update(detailed)
                    detailed_articles.append(article)
                except Exception as e:
                    print(f"获取文章详情失败 {article.get('title')}: {e}")
                    detailed_articles.append(article)
            
            return detailed_articles[:max_results]
            
        except Exception as e:
            print(f"搜索过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def get_article_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """获取文章详细信息"""
        try:
            if not url:
                return None
            
            # 在新标签页打开
            detail_page = await self.context.new_page()
            await detail_page.goto(url, wait_until="networkidle", timeout=self.timeout)
            await asyncio.sleep(2)
            
            content = await detail_page.content()
            soup = BeautifulSoup(content, 'lxml')
            
            # 提取详细内容
            detail = {}
            
            # 获取正文内容
            content_elem = detail_page.locator('[class*="content"]').or_(
                detail_page.locator('[class*="note-content"]')
            ).or_(
                detail_page.locator('article')
            )
            if await content_elem.count() > 0:
                detail["content"] = await content_elem.first.inner_text()
            
            # 获取点赞数
            like_elem = detail_page.locator('[class*="like"]').or_(
                detail_page.locator('text=/点赞/')
            )
            if await like_elem.count() > 0:
                like_text = await like_elem.first.inner_text()
                detail["likes"] = self._parse_count(like_text)
            
            # 获取收藏数
            collect_elem = detail_page.locator('[class*="collect"]').or_(
                detail_page.locator('text=/收藏/')
            )
            if await collect_elem.count() > 0:
                collect_text = await collect_elem.first.inner_text()
                detail["collections"] = self._parse_count(collect_text)
            
            # 获取评论数
            comment_elem = detail_page.locator('[class*="comment"]').or_(
                detail_page.locator('text=/评论/')
            )
            if await comment_elem.count() > 0:
                comment_text = await comment_elem.first.inner_text()
                detail["comments"] = self._parse_count(comment_text)
            
            await detail_page.close()
            return detail
            
        except Exception as e:
            print(f"获取文章详情失败 {url}: {e}")
            return None
    
    def _parse_count(self, text: str) -> int:
        """解析数量文本（如 "1.2万" -> 12000）"""
        if not text:
            return 0
        
        import re
        # 提取数字
        numbers = re.findall(r'[\d.]+', text)
        if not numbers:
            return 0
        
        num = float(numbers[0])
        
        # 处理单位
        if '万' in text or 'w' in text.lower():
            num *= 10000
        elif '千' in text or 'k' in text.lower():
            num *= 1000
        
        return int(num)
    
    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def __aenter__(self):
        await self.init_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
