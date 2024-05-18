class BaseException(Exception):
    def __init__(self, message: str, *args: object) -> None:
        self.message = message
        super().__init__(*args)


class RateLimitException(BaseException):
    def __init__(self, *args: object, message=None) -> None:
        message = message if message else "Fetching requeired data failed because of rate limit"
        super().__init__(message, *args)

class PrivateAccountException(BaseException):
    def __init__(self, *args: object, message=None) -> None:
        message = message if message else "Provided account is private"
        super().__init__(message, *args)

class NoTweetUserException(BaseException):
    def __init__(self, *args: object, message=None) -> None:
        message = message if message else "The user has no tweets"
        super().__init__(message, *args)
