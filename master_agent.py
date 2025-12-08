"""
Master Agent - 负责任务规划和拆解
"""
from typing import List, Dict, Any
from openai import OpenAI
import json
import config


class MasterAgent:
    """主控Agent，负责任务规划拆解"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL
        )
        self.model = config.OPENAI_MODEL
    
    def plan_task(self, domain: str) -> Dict[str, Any]:
        """
        规划任务，将搜索任务拆解为子任务
        
        Args:
            domain: 要搜索的领域
            
        Returns:
            包含任务规划信息的字典
        """
        prompt = f"""你是一个任务规划专家。用户想要在小红书搜索"{domain}"领域的热门知识文章，并保存点赞收藏量高的内容。

请将任务拆解为以下步骤：
1. 确定搜索关键词（可能需要多个相关关键词）
2. 确定筛选标准（点赞数、收藏数阈值）
3. 确定抓取策略（如何翻页、如何识别热门内容）

请以JSON格式返回任务规划，格式如下：
{{
    "domain": "{domain}",
    "search_keywords": ["关键词1", "关键词2", ...],
    "filter_criteria": {{
        "min_likes": 100,
        "min_collections": 50
    }},
    "strategy": {{
        "max_pages": 5,
        "articles_per_page": 10,
        "sort_by": "popularity"
    }},
    "sub_tasks": [
        {{
            "task_id": 1,
            "description": "使用关键词1搜索并抓取前N页内容",
            "keyword": "关键词1",
            "pages": 3
        }},
        ...
    ]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的任务规划助手，擅长将复杂任务拆解为可执行的子任务。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            plan = json.loads(response.choices[0].message.content)
            return plan
            
        except Exception as e:
            print(f"任务规划失败: {e}")
            # 返回默认规划
            return self._default_plan(domain)
    
    def _default_plan(self, domain: str) -> Dict[str, Any]:
        """默认任务规划"""
        return {
            "domain": domain,
            "search_keywords": [domain],
            "filter_criteria": {
                "min_likes": config.MIN_LIKES,
                "min_collections": config.MIN_COLLECTIONS
            },
            "strategy": {
                "max_pages": 5,
                "articles_per_page": 10,
                "sort_by": "popularity"
            },
            "sub_tasks": [
                {
                    "task_id": 1,
                    "description": f"搜索'{domain}'相关内容",
                    "keyword": domain,
                    "pages": 5
                }
            ]
        }
    
    def evaluate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        评估抓取结果，筛选出高质量内容
        
        Args:
            results: 抓取到的文章列表
            
        Returns:
            评估结果，包含筛选后的文章列表
        """
        if not results:
            return {
                "total": 0,
                "filtered": 0,
                "articles": []
            }
        
        # 按点赞数和收藏数排序
        sorted_results = sorted(
            results,
            key=lambda x: (x.get("likes", 0) + x.get("collections", 0)),
            reverse=True
        )
        
        # 应用筛选标准
        filtered = [
            article for article in sorted_results
            if article.get("likes", 0) >= config.MIN_LIKES
            and article.get("collections", 0) >= config.MIN_COLLECTIONS
        ]
        
        # 限制数量
        filtered = filtered[:config.MAX_ARTICLES]
        
        return {
            "total": len(results),
            "filtered": len(filtered),
            "articles": filtered
        }
