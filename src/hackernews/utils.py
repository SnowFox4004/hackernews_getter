from dateutil import parser
import dateutil

import datetime
from dateutil.tz import tzlocal
import time
import httpx


def parse_iso_timestamp(timestamp: str):
    return parser.isoparse(timestamp)


def structure_datetime(datetime: datetime.datetime):
    return datetime.strftime("%Y-%m-%d %H:%M:%S")


def iso_to_string(timestamp: str):
    return structure_datetime(parse_iso_timestamp(timestamp))


async def get_time_range_last_week():
    # timestamp of 1 week ago and now
    now = int(time.time())
    one_week_ago = now - 60 * 60 * 24 * 7
    return one_week_ago, now


async def get_time_range_last_month():
    # Get the current date
    today = datetime.date.today()

    # Calculate the first day of the current month
    first_day_current_month = today.replace(day=1)

    # Calculate the last day of last month (which is one day before first day of current month)
    last_day_last_month = first_day_current_month - datetime.timedelta(days=1)

    # Calculate the first day of last month
    first_day_last_month = last_day_last_month.replace(day=1)

    # Create datetime objects for the start and end of last month
    start_datetime = datetime.datetime.combine(first_day_last_month, datetime.time.min)
    end_datetime = datetime.datetime.combine(last_day_last_month, datetime.time.max)

    # Convert to timestamps
    start_timestamp = int(start_datetime.timestamp())
    end_timestamp = int(end_datetime.timestamp())

    return start_timestamp, end_timestamp


def convert_utc_to_local_v2(utc_timestamp):
    """
    使用dateutil库将UTC时间戳转换为本地时区时间

    Args:
        utc_timestamp (str): UTC时间戳

    Returns:
        datetime: 本地时区的datetime对象
    """
    # 解析时间戳（自动处理时区）
    utc_dt = parser.isoparse(utc_timestamp)

    # 转换为本地时区
    local_dt = utc_dt.astimezone(tzlocal())

    return local_dt
