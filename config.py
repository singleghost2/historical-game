import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# 大模型配置
LLM_CONFIG = {
    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",  # 自定义后端URL
    "api_key": "sk-bd980d3bef204feebfd81c18ab99f567",  # API密钥
    "model": "deepseek-v3",  # 模型名称
    "temperature": 0.7,  # 温度参数
    "max_tokens": 8000,  # 最大token数
} 