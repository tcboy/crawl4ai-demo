"""使用示例脚本"""
import asyncio
from agents.master_agent import MasterAgent
from agents.search_agent import SearchAgent

async def example_usage():
    """示例：如何使用各个组件"""
    
    # 示例1: 使用Master Agent规划任务
    print("=" * 60)
    print("示例1: Master Agent任务规划")
    print("=" * 60)
    
    master = MasterAgent()
    plan = master.plan_task("Python编程教程")
    print(f"规划结果: {plan}\n")
    
    # 示例2: 使用Search Agent执行搜索
    print("=" * 60)
    print("示例2: Search Agent执行搜索")
    print("=" * 60)
    
    search_agent = SearchAgent()
    try:
        await search_agent.initialize()
        
        # 执行单个关键词搜索
        articles = await search_agent.execute_search_task(
            keyword="Python",
            max_results=5,
            filters={"min_likes": 100, "min_collections": 50}
        )
        
        print(f"\n找到 {len(articles)} 篇文章")
        for i, article in enumerate(articles[:3], 1):
            print(f"{i}. {article.get('title', 'N/A')}")
            print(f"   点赞: {article.get('likes', 0)}, 收藏: {article.get('collections', 0)}")
        
        # 保存文章
        saved_files = await search_agent.save_articles(articles, "example")
        print(f"\n已保存 {len(saved_files)} 个文件")
        
    finally:
        await search_agent.close()

if __name__ == "__main__":
    asyncio.run(example_usage())
