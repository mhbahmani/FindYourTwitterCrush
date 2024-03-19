RESULT_TWEET_TEXTS = [
    'خدمت شما😉',
    'به این صورت😉',
    'به این شکل😉',
    'اینم از این😉',
    'بفرما😉'
]

MOST_LIKING_USERS_TITLE = """کدوم کاربرها بیش از بقیه توییت‌هات رو لایک کردن؟"""

MOST_LIKED_USERS_TITLE = """تو سال گذشته توییت‌های کدوم کاربرا رو بیش‌تر از بقیه لایک کردی؟"""

PRIVATE_OUTPUT_MESSAGE = "(این لینک موقته و از دسترس خارج می‌شه. عکس رو دانلود کنید تا پیش خودتون داشته باشید)"

START_MSG = """
سلام!

یوزر نیم توییتر یا لینک پروفایل توییترت رو تو یه پیام برام بفرست، تا بهت کارنامه‌ی اعمالتو نشون بدم :)
مثلا اینطوری:
https://twitter.com/mh_bahmani

فعلا فقط این که کیارو بیشتر لایک کردی رو میشه دید. بعدا این که کیا بیشتر تو رو لایک کردن هم بهت می‌گم.
حواست باشه که فعلا یه درخواست بیشتر نمی‌تونی بدی.
"""

ALREADY_STARTED_MSG = """قبلا استارت رو یه بار زدی

لینک پروفایل توییترت رو تو یه پیام برام بفرست، تا بهت کارنامه‌ی اعمالتو نشون بدم :)
مثلا اینطوری:
https://twitter.com/mh_bahmani
"""

error_template = """
تو یه پیام، لینک صفحه‌ی profileت رو برام بفرست. یه چیزی مثل این لینک:
https://twitter.com/mh_bahmani
"""
request_accepted_msg = "درخواستت رفت تو صف. به محض این که آماده بشه، برات می‌فرستمش ✨😌"
already_got_your_request_msg = """
درخواستت رو قبلا گرفتم و تو صف گذاشتم. یه مقدار صبر کن، هر وقت که حاضر شد، برات می‌فرستم.
"""
too_many_requests_msg = """
بیشتر از {} درخواست رو نمی‌تونی بدی و به سقف تعداد درخواست‌هاست رسیدی. فعلا صبر کن تا این سقف رو بیشتر کنم و بتونی دوباره درخواست بدی"""

USERNAME_NOT_FOUND_MSG = """
هیچ یوزری با یوزرنیم {} پیدا نکردم. اگه اکانتت پرایوته، باید پابلیکش کنی و اگه یوزرنیمتو اشتباه فرستادی، درستش کن و دوباره امتحان کن.

می‌تونی لینک پروفایل توییترت رو هم برام بفرستی، یه لینک مثل این لینک:
https://twitter.com/mh_bahmani
"""

PROFILE_NOT_FOUND_MSG = """
تو لینکی که فرستادی هیچ یوزری پیدا نکردم🤔
یه بار دیگه چک کن ببین لینک درسته و بعد دوباره امتحان کن. یا یوزرنیم یا لینک پروفایلت رو برام بفرست.
"""

NO_USERNAME_OF_LINK_PROVIDED_MSG = """
هیچ یوزرنیم یا لینکی توی پیامت پیدا نکردم🤔
باید یوزر نیم توییتر یا لینک پروفایل توییترت رو برام بفرستی. مثلا اینطوری:
https://twitter.com/mh_bahmani"""

SUPPORT_MSG = """
حالا که خروجی‌تو گرفتی، این توییتو لایک کن که بقیه هم بیان و از بات استفاده کنن😌
https://twitter.com/mh_bahmani/status/1769757048814686227

حتما هم کارنامه‌تو توییت کن تا همه ببینیم😊
"""

ACCESS_DENIED_MSG = """
بات هنوز به صورت عمومی در دسترس نیست و الان فقط کسایی که منو [mh_bahmani](https://twitter.com/mh_bahmani) فالو می‌کنن و منم فالوشون می‌کنم می‌تونن ازش استفاده کنن. هر وقت بات در دسترس قرار گرفت، خبرت می‌کنم."""

PRIVATE_ACCOUNT_ERROR_MSG = """
🚫 اکانت {} پرایوته و بدیهیه که من نمی‌تونم لایک‌ها و توییت‌هاشو ببینم :)
اکانتتو از پرایوت در بیار و دوباره امتحان کن."""