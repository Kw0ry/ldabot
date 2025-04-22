import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    @property
    def bot_token(self):
        return os.getenv("BOT_TOKEN", "7706032185:AAFF7LzJyAlrwp1IdAhum0GwtXWdPQTQcog")
    
    @property
    def admin_ids(self):
        raw_ids = os.getenv("ADMIN_IDS", "7724035951").split('#')[0].strip()
        return [int(i.strip()) for i in raw_ids.split(',') if i.strip().isdigit()]
    
    @property
    def channel_id(self):
        return int(os.getenv("CHANNEL_ID", "-1002629002336"))
    
    @property
    def redis_host(self):
        return os.getenv("REDS_HOST", "localhost")
    
    @property
    def redis_port(self):
        return int(os.getenv("REDIS_PORT", "6379"))
    
    @property
    def redis_db(self):
        return int(os.getenv("REDIS_DB", "0"))
    
    @property
    def celery_broker_url(self):
        return os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    
    @property
    def celery_result_backend(self):
        return os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

config = Config()