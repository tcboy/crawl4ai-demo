"""
简单的 CUA Agent 示例

这个示例展示了如何使用 CUA 框架创建一个基本的 AI Agent，
它可以理解屏幕内容并执行操作。
"""

import asyncio
import os
from dotenv import load_dotenv
from agent import ComputerAgent
from computer import Computer

# 加载环境变量
load_dotenv()


async def main():
    """运行简单的 agent 示例"""
    print("🚀 启动 CUA Agent 示例...\n")
    
    try:
        # 方式 1: 使用本地计算机（macOS）
        # 注意：这需要本地有 macOS 环境
        computer = Computer(
            os_type="macos",
            verbosity="INFO",
        )
        
        # 方式 2: 使用云端 Linux 计算机（取消注释以使用）
        # computer = Computer(
        #     os_type="linux",
        #     api_key=os.getenv("CUA_API_KEY"),
        #     name=os.getenv("CUA_CONTAINER_NAME"),
        #     provider_type="cloud",
        # )
        
        # 创建 ComputerAgent
        # 你可以使用不同的模型，这里使用 OpenAI 的预览模型
        agent = ComputerAgent(
            model="openai/computer-use-preview",  # 或使用 "anthropic/claude-sonnet-4-5-20250929"
            tools=[computer],
            max_trajectory_budget=5.0,  # 最大轨迹预算
        )
        
        # 定义任务
        messages = [
            {
                "role": "user",
                "content": "截取一张屏幕截图，然后告诉我你看到了什么"
            }
        ]
        
        print("📝 任务: 截取屏幕截图并描述内容\n")
        
        # 运行 agent
        async for result in agent.run(messages):
            # 处理输出
            for item in result.get("output", []):
                # 打印消息
                if item.get("type") == "message":
                    content = item.get("content", [])
                    for content_part in content:
                        if content_part.get("type") == "output_text":
                            print(f"🤖 Agent: {content_part.get('text')}\n")
                
                # 打印计算机操作
                elif item.get("type") == "computer_call":
                    action = item.get("action", {})
                    action_type = action.get("type", "")
                    print(f"⚙️  执行操作: {action_type}")
                
                # 打印推理过程
                elif item.get("type") == "reasoning":
                    summary = item.get("summary", [])
                    for summary_item in summary:
                        if summary_item.get("type") == "summary_text":
                            print(f"💭 推理: {summary_item.get('text')}")
        
        print("\n✅ 任务完成！")
        
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
