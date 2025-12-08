"""主程序入口 - AI Agent系统"""
import asyncio
import sys
from pathlib import Path
from agents.master_agent import MasterAgent
from agents.search_agent import SearchAgent
from utils.config import Config

class XiaohongshuAgentSystem:
    """小红书AI Agent系统"""
    
    def __init__(self):
        self.master_agent = MasterAgent()
        self.search_agent = SearchAgent()
    
    async def run(self, user_query: str):
        """运行完整的Agent流程"""
        print("=" * 60)
        print("小红书热门内容搜索Agent系统")
        print("=" * 60)
        print(f"\n用户需求: {user_query}\n")
        
        # 步骤1: Master Agent规划任务
        print("【步骤1】Master Agent正在规划任务...")
        plan = self.master_agent.plan_task(user_query)
        
        if not self.master_agent.validate_plan(plan):
            print("错误: 任务规划无效")
            return
        
        print(f"\n任务规划完成:")
        print(f"  领域: {plan.get('domain')}")
        print(f"  关键词: {', '.join(plan.get('keywords', []))}")
        print(f"  筛选条件: 最小点赞数 {plan.get('filters', {}).get('min_likes', 0)}, "
              f"最小收藏数 {plan.get('filters', {}).get('min_collections', 0)}")
        print(f"  每个关键词最多收集: {plan.get('max_results', 20)} 篇文章")
        print(f"  策略: {plan.get('strategy', 'N/A')}\n")
        
        # 步骤2: Search Agent执行搜索
        print("【步骤2】Search Agent开始执行搜索任务...\n")
        
        try:
            result = await self.search_agent.execute_full_task(
                keywords=plan.get('keywords', []),
                domain=plan.get('domain', 'general'),
                max_results_per_keyword=plan.get('max_results', 20),
                filters=plan.get('filters')
            )
            
            # 步骤3: 显示结果
            print("\n" + "=" * 60)
            print("任务执行完成！")
            print("=" * 60)
            print(f"\n总共收集: {result['total_articles']} 篇文章")
            print(f"已保存到: {Config.DATA_DIR / result['domain']}")
            print(f"保存文件数: {len(result['saved_files'])} 个")
            
            # 显示热门文章Top 10
            if result['articles']:
                print("\n【热门文章 Top 10】")
                print("-" * 60)
                for i, article in enumerate(result['articles'][:10], 1):
                    title = article.get('title', '无标题')[:40]
                    likes = article.get('likes', 0)
                    collections = article.get('collections', 0)
                    print(f"{i}. {title}")
                    print(f"   点赞: {likes} | 收藏: {collections}")
                    print()
            
        except Exception as e:
            print(f"\n错误: 执行任务时出错: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # 清理资源
            await self.search_agent.close()
            print("\n系统已关闭，感谢使用！")

async def main():
    """主函数"""
    # 检查配置
    if not Config.OPENAI_API_KEY:
        print("错误: 请设置 OPENAI_API_KEY 环境变量")
        print("可以在 .env 文件中设置，或参考 .env.example")
        sys.exit(1)
    
    # 获取用户输入
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = input("请输入您要搜索的领域/关键词: ").strip()
        if not user_query:
            print("错误: 请输入有效的搜索关键词")
            sys.exit(1)
    
    # 创建并运行系统
    system = XiaohongshuAgentSystem()
    await system.run(user_query)

if __name__ == "__main__":
    # 创建必要的目录
    Path(".auth").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    # 运行主程序
    asyncio.run(main())
