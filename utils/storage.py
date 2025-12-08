"""数据存储模块"""
import json
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from utils.config import Config

class DataStorage:
    """数据存储管理器"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Config.DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
    
    def save_article(self, article: Dict[str, Any], domain: str) -> str:
        """保存单篇文章到本地"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain_dir = self.data_dir / domain
        domain_dir.mkdir(exist_ok=True)
        
        # 生成文件名（使用文章ID或标题）
        article_id = article.get("article_id", article.get("note_id", ""))
        title = article.get("title", "untitled")
        # 清理文件名中的非法字符
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))[:50]
        filename = f"{article_id}_{safe_title}.json" if article_id else f"{timestamp}_{safe_title}.json"
        
        filepath = domain_dir / filename
        
        # 添加保存时间戳
        article["saved_at"] = datetime.now().isoformat()
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(article, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    async def save_article_async(self, article: Dict[str, Any], domain: str) -> str:
        """异步保存单篇文章"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain_dir = self.data_dir / domain
        domain_dir.mkdir(exist_ok=True)
        
        article_id = article.get("article_id", article.get("note_id", ""))
        title = article.get("title", "untitled")
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))[:50]
        filename = f"{article_id}_{safe_title}.json" if article_id else f"{timestamp}_{safe_title}.json"
        
        filepath = domain_dir / filename
        article["saved_at"] = datetime.now().isoformat()
        
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(json.dumps(article, ensure_ascii=False, indent=2))
        
        return str(filepath)
    
    def save_batch(self, articles: List[Dict[str, Any]], domain: str) -> List[str]:
        """批量保存文章"""
        saved_files = []
        for article in articles:
            filepath = self.save_article(article, domain)
            saved_files.append(filepath)
        return saved_files
    
    def load_articles(self, domain: str) -> List[Dict[str, Any]]:
        """加载某个领域的所有文章"""
        domain_dir = self.data_dir / domain
        if not domain_dir.exists():
            return []
        
        articles = []
        for filepath in domain_dir.glob("*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    article = json.load(f)
                    articles.append(article)
            except Exception as e:
                print(f"加载文件 {filepath} 失败: {e}")
        
        return articles
