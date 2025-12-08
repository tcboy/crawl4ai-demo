"""
主程序入口 - AI Agent系统
"""
import asyncio
import sys
from master_agent import MasterAgent
from sub_agent import SubAgent
from storage import Storage
import config


class XiaohongshuAgent:
    """小红书文章抓取Agent系统"""
    
    def __init__(self):
        self.master_agent = MasterAgent()
        self.sub_agent = SubAgent()
        self.storage = Storage()
    
    async def run(self, domain: str):
        """
        运行完整的抓取流程
        
        Args:
            domain: 要搜索的领域
        """
        print(f"\n{'='*60}")
        print(f"开始搜索领域: {domain}")
        print(f"{'='*60}\n")
        
        try:
            # 步骤1: Master Agent规划任务
            print("【步骤1】Master Agent正在规划任务...")
            plan = self.master_agent.plan_task(domain)
            print(f"任务规划完成:")
            print(f"  - 搜索关键词: {', '.join(plan.get('search_keywords', []))}")
            print(f"  - 筛选标准: 最少{plan['filter_criteria']['min_likes']}点赞, {plan['filter_criteria']['min_collections']}收藏")
            print(f"  - 子任务数: {len(plan.get('sub_tasks', []))}")
            print()
            
            # 步骤2: 初始化Sub Agent
            print("【步骤2】初始化Sub Agent...")
            await self.sub_agent.initialize()
            print("Sub Agent初始化完成\n")
            
            # 步骤3: 执行子任务
            all_articles = []
            sub_tasks = plan.get('sub_tasks', [])
            
            if not sub_tasks:
                # 如果没有子任务，使用默认关键词搜索
                keywords = plan.get('search_keywords', [domain])
                for keyword in keywords:
                    print(f"【步骤3】使用关键词 '{keyword}' 搜索...")
                    articles = await self.sub_agent.search_xiaohongshu(
                        keyword,
                        max_pages=plan['strategy'].get('max_pages', 5)
                    )
                    all_articles.extend(articles)
                    print(f"关键词 '{keyword}' 搜索完成，获得 {len(articles)} 篇文章\n")
            else:
                # 执行规划的子任务
                for i, task in enumerate(sub_tasks, 1):
                    keyword = task.get('keyword', domain)
                    pages = task.get('pages', 5)
                    
                    print(f"【步骤3.{i}】执行子任务: {task.get('description', '')}")
                    print(f"  关键词: {keyword}, 页数: {pages}")
                    
                    articles = await self.sub_agent.search_xiaohongshu(keyword, max_pages=pages)
                    all_articles.extend(articles)
                    
                    print(f"子任务 {i} 完成，获得 {len(articles)} 篇文章\n")
            
            # 步骤4: Master Agent评估结果
            print("【步骤4】Master Agent正在评估结果...")
            evaluation = self.master_agent.evaluate_results(all_articles)
            print(f"评估完成:")
            print(f"  - 总文章数: {evaluation['total']}")
            print(f"  - 筛选后文章数: {evaluation['filtered']}")
            print()
            
            # 步骤5: 保存数据
            if evaluation['articles']:
                print("【步骤5】保存文章到本地...")
                self.storage.save_articles(evaluation['articles'], domain)
                
                # 保存摘要
                summary = {
                    "domain": domain,
                    "plan": plan,
                    "evaluation": evaluation,
                    "top_articles": evaluation['articles'][:10]  # 前10篇
                }
                self.storage.save_summary(summary, domain)
                print()
                
                # 显示前几篇热门文章
                print("【热门文章预览】")
                print("-" * 60)
                for i, article in enumerate(evaluation['articles'][:5], 1):
                    print(f"\n{i}. {article.get('title', '无标题')}")
                    print(f"   作者: {article.get('author', '未知')}")
                    print(f"   点赞: {article.get('likes', 0)}, 收藏: {article.get('collections', 0)}")
                    print(f"   链接: {article.get('url', '')}")
                print()
            else:
                print("【步骤5】没有符合条件的文章需要保存\n")
            
            # 清理
            await self.sub_agent.close()
            
            print(f"{'='*60}")
            print("任务完成！")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n错误: {e}")
            import traceback
            traceback.print_exc()
            await self.sub_agent.close()
            sys.exit(1)


async def main():
    """主函数"""
    # 检查配置
    if not config.OPENAI_API_KEY:
        print("错误: 请设置 OPENAI_API_KEY 环境变量")
        print("可以在 .env 文件中设置，或参考 .env.example")
        sys.exit(1)
    
    # 获取搜索领域
    if len(sys.argv) > 1:
        domain = sys.argv[1]
    else:
        domain = input("请输入要搜索的领域（例如：Python编程、健身、美食）: ").strip()
        if not domain:
            print("错误: 领域不能为空")
            sys.exit(1)
    
    # 创建并运行Agent
    agent = XiaohongshuAgent()
    await agent.run(domain)


if __name__ == "__main__":
    asyncio.run(main())
