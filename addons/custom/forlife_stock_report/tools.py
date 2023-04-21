from datetime import datetime
import pytz


def convert_to_utc_datetime(current_tz, str_datetime):
    return current_tz.localize(datetime.strptime(str_datetime, "%Y-%m-%d %H:%M:%S"), is_dst=None).astimezone(
        pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
