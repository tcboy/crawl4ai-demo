"""
数据存储模块 - 保存热门文章到本地
"""
import os
import json
import time
from typing import List, Dict, Any
import config


class Storage:
    """数据存储类"""
    
    def __init__(self):
        self.data_dir = config.DATA_DIR
        self.articles_dir = config.ARTICLES_DIR
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保目录存在"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.articles_dir, exist_ok=True)
    
    def save_articles(self, articles: List[Dict[str, Any]], domain: str):
        """
        保存文章到本地
        
        Args:
            articles: 文章列表
            domain: 领域名称（用于文件命名）
        """
        if not articles:
            print("没有文章需要保存")
            return
        
        # 生成文件名（包含时间戳）
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_domain = "".join(c for c in domain if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_domain = safe_domain.replace(' ', '_')
        
        filename = f"{safe_domain}_{timestamp}.json"
        filepath = os.path.join(self.articles_dir, filename)
        
        # 准备保存的数据
        data = {
            "domain": domain,
            "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_articles": len(articles),
            "articles": articles
        }
        
        # 保存为JSON
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"成功保存 {len(articles)} 篇文章到: {filepath}")
        except Exception as e:
            print(f"保存文件时出错: {e}")
    
    def save_summary(self, summary: Dict[str, Any], domain: str):
        """
        保存抓取摘要
        
        Args:
            summary: 摘要信息
            domain: 领域名称
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_domain = "".join(c for c in domain if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_domain = safe_domain.replace(' ', '_')
        
        filename = f"{safe_domain}_summary_{timestamp}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f"摘要已保存到: {filepath}")
        except Exception as e:
            print(f"保存摘要时出错: {e}")
    
    def load_articles(self, domain: str = None) -> List[Dict[str, Any]]:
        """
        加载已保存的文章
        
        Args:
            domain: 领域名称（可选，用于过滤）
            
        Returns:
            文章列表
        """
        articles = []
        
        if not os.path.exists(self.articles_dir):
            return articles
        
        # 获取所有JSON文件
        json_files = [f for f in os.listdir(self.articles_dir) if f.endswith('.json')]
        
        for filename in json_files:
            if domain and domain not in filename:
                continue
            
            filepath = os.path.join(self.articles_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'articles' in data:
                        articles.extend(data['articles'])
            except Exception as e:
                print(f"加载文件 {filename} 时出错: {e}")
        
        return articles
