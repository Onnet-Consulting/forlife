import datetime

dt1 = datetime.datetime(2020, 7, 21, 6, 12, 30, 551)
print(dt1)

dt2 = dt1 + datetime.timedelta(days=1)
print(dt2)

dt3 = dt1 + datetime.timedelta(days=-1)
print(dt3)
