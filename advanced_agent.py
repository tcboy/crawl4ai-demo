"""
高级 CUA Agent 示例

这个示例展示了如何使用 CUA Agent 执行多个连续任务，
并维护对话历史。
"""

import asyncio
import os
from dotenv import load_dotenv
from agent import ComputerAgent
from computer import Computer

# 加载环境变量
load_dotenv()


async def main():
    """运行高级 agent 示例，执行多个任务"""
    print("🚀 启动高级 CUA Agent 示例...\n")
    
    try:
        # 创建计算机实例
        computer = Computer(
            os_type="macos",
            verbosity="INFO",
        )
        
        # 创建 Agent，使用组合模型（Moondream3 + GPT-4o）
        # 这种方式使用专门的 UI 检测模型 + 强大的推理模型
        agent = ComputerAgent(
            # 组合模型：Moondream3 用于 UI 元素检测，GPT-4o 用于规划和推理
            model="moondream3+openai/gpt-4o",
            # 或者使用单一模型：
            # model="openai/computer-use-preview",
            # model="anthropic/claude-sonnet-4-5-20250929",
            tools=[computer],
            max_trajectory_budget=10.0,
            only_n_most_recent_images=3,  # 只保留最近 3 张截图以节省 token
        )
        
        # 定义一系列任务
        tasks = [
            "打开浏览器",
            "在浏览器中搜索 'CUA framework'",
            "告诉我搜索结果的前三个链接",
        ]
        
        # 维护对话历史
        history = []
        
        for i, task in enumerate(tasks, 1):
            print(f"\n{'='*60}")
            print(f"📋 任务 {i}/{len(tasks)}: {task}")
            print(f"{'='*60}\n")
            
            # 添加用户消息到历史
            history.append({"role": "user", "content": task})
            
            # 运行 agent
            async for result in agent.run(history, stream=False):
                # 将 agent 输出添加到历史
                history += result.get("output", [])
                
                # 打印输出
                for item in result.get("output", []):
                    # 消息输出
                    if item.get("type") == "message":
                        content = item.get("content", [])
                        for content_part in content:
                            if content_part.get("type") == "output_text":
                                print(f"🤖 Agent: {content_part.get('text')}\n")
                    
                    # 推理过程
                    elif item.get("type") == "reasoning":
                        summary = item.get("summary", [])
                        for summary_item in summary:
                            if summary_item.get("type") == "summary_text":
                                print(f"💭 推理: {summary_item.get('text')}")
                    
                    # 计算机操作
                    elif item.get("type") == "computer_call":
                        action = item.get("action", {})
                        action_type = action.get("type", "")
                        action_text = action.get("text", "")
                        print(f"⚙️  操作: {action_type} - {action_text}")
                    
                    # 使用统计
                    elif "usage" in result:
                        usage = result["usage"]
                        print(f"\n📊 Token 使用: {usage.get('total_tokens', 0)} tokens")
                        print(f"💰 成本: ${usage.get('response_cost', 0):.4f}")
            
            print(f"\n✅ 任务 {i} 完成！\n")
        
        print("\n" + "="*60)
        print("🎉 所有任务完成！")
        print("="*60)
        
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        if 'computer' in locals():
            await computer.stop()


if __name__ == "__main__":
    asyncio.run(main())
