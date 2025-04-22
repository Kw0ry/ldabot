import redis
from config import config

class Database:
    def __init__(self):
        self.redis = redis.StrictRedis(
            host=config.redis_host,  # Используем свойство вместо атрибута
            port=config.redis_port,
            db=config.redis_db,
            decode_responses=True
        )

    def save_event(self, event_id, event_data):
        self.redis.hset(f"event:{event_id}", mapping=event_data)
        self.redis.sadd("pending_events", event_id)

    def get_event(self, event_id):
        return self.redis.hgetall(f"event:{event_id}")

    def move_event(self, event_id, from_set, to_set):
        self.redis.srem(from_set, event_id)
        self.redis.sadd(to_set, event_id)

    def get_pending_events(self):
        return [self.get_event(eid) for eid in self.redis.smembers("pending_events")]

    def save_user(self, user_id, user_data):
        self.redis.hset(f"user:{user_id}", mapping=user_data)

db = Database()