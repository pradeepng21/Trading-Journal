import os
import sys
import datetime
import pytz
from urllib.parse import quote
from loguru import logger

IST = pytz.timezone("Asia/Calcutta")

# USERNAME = "trading_user"
# PASSWORD = quote("Trading@123")
# HOST = "localhost"
# PORT = 3306
# NAME = "trading_journal"
# DATABASE_URL = (
#     f"mysql+mysqlconnector://{USERNAME}:{PASSWORD}"
#     f"@{HOST}:{PORT}/{NAME}"
# )
KITE_URL = "https://api.kite.trade/instruments"

DATABASE_URL = "mysql+pymysql://root:12345678@localhost:3306/trading_journal"
SECRET_KEY = "change_this_secret_key"

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

# DATABASE_URL = "mysql+pymysql://root:password@localhost/trading_journal"

today_date = datetime.datetime.now(IST).strftime("%Y-%m-%d")

main_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
folder_name = main_directory + "/log"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)

logger.remove()
logger.add(sys.stdout, level="DEBUG")

logger.add(
    os.path.join(main_directory, "log", f"trading_journal_{today_date}.log"),
    rotation="1 day",
    compression="zip",
    enqueue=True,
    level="DEBUG",
)

logger.debug(f" {'-'*10}{'>'*10}{' '*10} app started.....{' '*10}{'<'*10}{'-'*10} ")