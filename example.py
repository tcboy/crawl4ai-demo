"""
使用示例
"""
import asyncio
from main import XiaohongshuAgent


async def example():
    """示例：搜索Python编程相关内容"""
    
    # 创建Agent实例
    agent = XiaohongshuAgent()
    
    # 运行搜索任务
    await agent.run("Python编程")


if __name__ == "__main__":
    asyncio.run(example())
