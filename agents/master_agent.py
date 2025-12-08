"""Master Agent - 负责任务规划拆解"""
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from utils.config import Config

class MasterAgent:
    """Master Agent - 负责任务规划"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=0.7,
            openai_api_key=Config.OPENAI_API_KEY,
            openai_api_base=Config.OPENAI_BASE_URL
        )
    
    def plan_task(self, user_query: str) -> Dict[str, Any]:
        """规划任务，拆解为子任务"""
        system_prompt = """你是一个任务规划专家。你的职责是将用户的需求拆解为具体的、可执行的子任务。

对于小红书搜索任务，你需要：
1. 理解用户想要搜索的领域/关键词
2. 确定搜索策略（关键词组合、筛选条件等）
3. 规划数据收集和存储方案
4. 确定质量标准（点赞数、收藏数阈值等）

请以JSON格式返回规划结果，包含以下字段：
- domain: 搜索领域
- keywords: 搜索关键词列表
- filters: 筛选条件（如最小点赞数、最小收藏数）
- max_results: 每个关键词最多收集的文章数
- strategy: 搜索策略描述
"""
        
        user_prompt = f"""
用户需求：{user_query}

请为这个任务制定详细的执行计划。
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            plan_text = response.content
            
            # 尝试解析JSON（如果LLM返回的是JSON）
            import json
            import re
            
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', plan_text, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                # 如果LLM没有返回JSON，使用默认结构
                plan = self._parse_plan_from_text(plan_text, user_query)
            
            return plan
            
        except Exception as e:
            print(f"规划任务时出错: {e}")
            # 返回默认计划
            return self._create_default_plan(user_query)
    
    def _parse_plan_from_text(self, text: str, user_query: str) -> Dict[str, Any]:
        """从文本中解析计划（备用方案）"""
        # 简单的关键词提取
        import re
        keywords = re.findall(r'["\']([^"\']+)["\']', text)
        if not keywords:
            # 从用户查询中提取
            keywords = [user_query]
        
        return {
            "domain": keywords[0] if keywords else "general",
            "keywords": keywords[:5],  # 最多5个关键词
            "filters": {
                "min_likes": 100,
                "min_collections": 50
            },
            "max_results": 20,
            "strategy": "搜索热门内容，按点赞和收藏数排序"
        }
    
    def _create_default_plan(self, user_query: str) -> Dict[str, Any]:
        """创建默认计划"""
        return {
            "domain": user_query,
            "keywords": [user_query],
            "filters": {
                "min_likes": 100,
                "min_collections": 50
            },
            "max_results": 20,
            "strategy": "直接搜索用户提供的关键词，收集热门内容"
        }
    
    def validate_plan(self, plan: Dict[str, Any]) -> bool:
        """验证计划的有效性"""
        required_fields = ["domain", "keywords", "filters", "max_results"]
        return all(field in plan for field in required_fields)
