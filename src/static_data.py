from enum import Enum


class REQUEST_TYPE(Enum):
    DIRECT = "d"
    TWEET = "t"
    CACHE = "c"
    BOT = "b"