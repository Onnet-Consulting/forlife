from datetime import datetime
import pytz

time = '2023-01-10 02:41:33'
datetime_object = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
utcmoment_naive = datetime_object
utcmoment = utcmoment_naive.replace(tzinfo=pytz.utc)
localFormat = "%Y-%m-%d %H:%M:%S"
tz = 'Asia/Ho_Chi_Minh'
create_Date = utcmoment.astimezone(pytz.timezone(tz))
data = create_Date.strftime(localFormat)
print(create_Date)
print((create_Date.month))