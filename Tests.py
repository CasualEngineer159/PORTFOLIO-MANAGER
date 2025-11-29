from Asset import *
from rich import print

apple = Stock("aapl")

date = datetime(2025,11,15).date()
#pp.pprint(apple.get_prices(date))

time_series = pd.date_range(start=date, end=get_last_business_day(), freq='D')
print(time_series)
