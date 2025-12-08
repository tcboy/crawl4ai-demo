"""
配置文件
"""
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

# 小红书配置
XIAOHONGSHU_BASE_URL = "https://www.xiaohongshu.com"

# 数据存储配置
DATA_DIR = os.getenv("DATA_DIR", "./data")
ARTICLES_DIR = os.path.join(DATA_DIR, "articles")

# 爬虫配置
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "50"))  # 最多抓取的文章数
MIN_LIKES = int(os.getenv("MIN_LIKES", "100"))  # 最少点赞数
MIN_COLLECTIONS = int(os.getenv("MIN_COLLECTIONS", "50"))  # 最少收藏数

# Playwright配置
HEADLESS = os.getenv("HEADLESS", "True").lower() == "true"
TIMEOUT = int(os.getenv("TIMEOUT", "30000"))  # 30秒超时
