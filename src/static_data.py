from enum import Enum


class REQUEST_TYPE(Enum):
    DIRECT = "d"
    TWEET = "t"
    CACHE = "c"
    BOT = "b"


TWITTER_CONFIG_PATH_TO_NAME = {
    "twitter.json": "Main",
    "twitter_backup.json": "Pickle MHB",
    "twitter_backup_2.json": "Ghasemzade",
    "twitter_backup_3.json": "Mohsen's Bot",
    "twitter_backup_4.json": "Esi",
    "twitter_backup_5.json": "SharifDaily",
    "twitter_backup_6.json": "MHB's Bot"
}