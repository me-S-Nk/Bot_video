import time
from collections import defaultdict
from config import SPAM_TIME_WINDOW, SPAM_MAX_REQUESTS
from functools import lru_cache

user_logs = defaultdict(list)

@lru_cache(maxsize=1024)
def is_spam(user_id: int) -> bool:
    now = time.time()
    window = user_logs[user_id]
    user_logs[user_id] = [t for t in window if now - t <= SPAM_TIME_WINDOW]

    if len(user_logs[user_id]) >= SPAM_MAX_REQUESTS:
        return True

    user_logs[user_id].append(now)
    return False