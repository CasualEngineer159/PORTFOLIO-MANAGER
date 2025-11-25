import csv
from DownloadManager import *

ticker = 'XAU/USD'

with open("API.json", 'r', encoding='utf-8') as f:
    API = json.load(f)

url = ("https://api.twelvedata.com/time_series?"
       f"apikey={API["Twelvedata"]}&"
       f"symbol={ticker}&"
       "interval=1day&"
       "format=CSV&"
       "previous_close=false&"
       "timezone=Europe/Prague&"
       "start_date=1980-11-10&"
       )

# Dotaz na API
r = requests.get(url)
stock_history = pd.read_csv(io.StringIO(r.text))

ticker = ticker.replace('/','')

stock_history.to_csv(f'DATA/{ticker}.test.history.csv')
