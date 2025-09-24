from dateutil import parser
import datetime
from dateutil.tz import tzlocal


def parse_iso_timestamp(timestamp: str):
    return parser.isoparse(timestamp)


def structure_datetime(datetime: datetime.datetime):
    return datetime.strftime("%Y-%m-%d %H:%M:%S")


def iso_to_string(timestamp: str):
    return structure_datetime(parse_iso_timestamp(timestamp))


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
