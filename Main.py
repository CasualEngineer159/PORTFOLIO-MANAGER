import requests
import pprint as pp
import yfinance as yf
import os

class ApiManager:
    def __init__(self, ):
        pass

# Dynamické proměnné
base_url = 'https://www.alphavantage.co/query'
function = 'TIME_SERIES_DAILY_ADJUSTED'
symbol = 'IBM'
apikey = '5H3BQBCDJJJ9TTFU'

# Složení URL
params = {
    'function': function,
    'symbol': symbol,
    'apikey': apikey
}

# Dotaz na API
r = requests.get(base_url, params=params)
data = r.json()

pp.pprint(data)

apple= yf.Ticker("VUSA.AS")

apple_history = apple.history(period="max", interval="1d")
apple_history.to_csv('DATA/apple.csv')