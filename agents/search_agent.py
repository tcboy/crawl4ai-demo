"""Search Agent - 负责执行搜索任务"""
from typing import List, Dict, Any, Optional
from tools.xiaohongshu_scraper import XiaohongshuScraper
from utils.storage import DataStorage
from utils.config import Config

class SearchAgent:
    """Search Agent - 执行具体的搜索任务"""
    
    def __init__(self):
        self.scraper: Optional[XiaohongshuScraper] = None
        self.storage = DataStorage()
    
    async def initialize(self):
        """初始化爬虫工具"""
        self.scraper = XiaohongshuScraper()
        await self.scraper.init_browser()
        
        # 尝试加载已保存的登录状态
        from pathlib import Path
        auth_file = Path(".auth/xhs_state.json")
        if auth_file.exists():
            if await self.scraper.load_auth_state():
                print("已使用保存的登录状态")
                return
        
        # 如果没有保存的状态，尝试登录
        print("需要登录小红书账号...")
        await self.scraper.login()
    
    async def execute_search_task(
        self, 
        keyword: str, 
        max_results: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """执行搜索任务"""
        if not self.scraper:
            await self.initialize()
        
        print(f"\n开始搜索关键词: {keyword}")
        print(f"目标结果数: {max_results}")
        
        # 执行搜索
        articles = await self.scraper.search(keyword, max_results=max_results * 2)  # 多搜索一些以便筛选
        
        # 应用筛选条件
        if filters:
            articles = self._apply_filters(articles, filters)
        
        # 按热度排序
        articles = self._sort_by_popularity(articles)
        
        # 限制结果数量
        articles = articles[:max_results]
        
        print(f"搜索完成，找到 {len(articles)} 篇符合条件的文章")
        return articles
    
    def _apply_filters(self, articles: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """应用筛选条件"""
        filtered = []
        
        min_likes = filters.get("min_likes", 0)
        min_collections = filters.get("min_collections", 0)
        
        for article in articles:
            likes = article.get("likes", 0)
            collections = article.get("collections", 0)
            
            if likes >= min_likes and collections >= min_collections:
                filtered.append(article)
            else:
                print(f"文章 '{article.get('title', '')[:30]}' 不符合筛选条件 (点赞: {likes}, 收藏: {collections})")
        
        return filtered
    
    def _sort_by_popularity(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按热度排序（点赞数 + 收藏数）"""
        def popularity_score(article):
            likes = article.get("likes", 0)
            collections = article.get("collections", 0)
            comments = article.get("comments", 0)
            # 综合热度 = 点赞 * 1 + 收藏 * 1.5 + 评论 * 0.5
            return likes + collections * 1.5 + comments * 0.5
        
        return sorted(articles, key=popularity_score, reverse=True)
    
    async def save_articles(self, articles: List[Dict[str, Any]], domain: str) -> List[str]:
        """保存文章到本地"""
        saved_files = []
        for article in articles:
            try:
                filepath = self.storage.save_article(article, domain)
                saved_files.append(filepath)
                print(f"已保存: {article.get('title', '')[:30]}... -> {filepath}")
            except Exception as e:
                print(f"保存文章失败: {e}")
        
        return saved_files
    
    async def execute_full_task(
        self,
        keywords: List[str],
        domain: str,
        max_results_per_keyword: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行完整的搜索任务（多个关键词）"""
        all_articles = []
        
        for keyword in keywords:
            try:
                articles = await self.execute_search_task(
                    keyword=keyword,
                    max_results=max_results_per_keyword,
                    filters=filters
                )
                all_articles.extend(articles)
            except Exception as e:
                print(f"搜索关键词 '{keyword}' 时出错: {e}")
                continue
        
        # 去重（基于文章ID）
        unique_articles = {}
        for article in all_articles:
            article_id = article.get("article_id") or article.get("note_id")
            if article_id and article_id not in unique_articles:
                unique_articles[article_id] = article
            elif not article_id:
                # 如果没有ID，使用标题作为唯一标识
                title = article.get("title", "")
                if title and title not in [a.get("title") for a in unique_articles.values()]:
                    unique_articles[f"no_id_{len(unique_articles)}"] = article
        
        final_articles = list(unique_articles.values())
        
        # 再次按热度排序
        final_articles = self._sort_by_popularity(final_articles)
        
        # 保存所有文章
        saved_files = await self.save_articles(final_articles, domain)
        
        return {
            "total_articles": len(final_articles),
            "saved_files": saved_files,
            "articles": final_articles,
            "domain": domain
        }
    
    async def close(self):
        """关闭资源"""
        if self.scraper:
            await self.scraper.close()
