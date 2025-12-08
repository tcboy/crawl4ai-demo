"""配置文件管理"""
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    """应用配置"""
    
    # OpenAI配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # 小红书账号配置
    XHS_USERNAME = os.getenv("XHS_USERNAME", "")
    XHS_PASSWORD = os.getenv("XHS_PASSWORD", "")
    
    # 数据存储配置
    DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
    DATA_DIR.mkdir(exist_ok=True)
    
    # 浏览器配置
    HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
    BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))
    
    # 小红书URL
    XHS_BASE_URL = "https://www.xiaohongshu.com"
    XHS_LOGIN_URL = "https://www.xiaohongshu.com/user/login"
    XHS_SEARCH_URL = "https://www.xiaohongshu.com/search_result"
