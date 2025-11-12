import pandas as pd
import pprint as pp
import yfinance as yf
import requests
import json
import io
from pandas.tseries.offsets import BDay
from datetime import datetime
import matplotlib.pyplot as plt

def get_last_business_day() -> datetime:
    today = datetime.now().date()
    return (today - BDay(1)).date()

class Asset:

    def __init__(self, ticker):
        self._yahoo_ticker = yf.Ticker(ticker)
        self._stock_info = self._load_stock_info()
        self._daily_history = self._load_daily_history()

        if not self._stock_info:
            self._stock_info = self._download_stock_info()
        if self._daily_history.empty or get_last_business_day() > self._daily_history.index.max().date():
            self._daily_history = self._download_daily_history()

        self.name = self._stock_info.get("longName", self._yahoo_ticker.ticker)
        print(self.name)

    def plot_closing_price(self):

        plt.figure(figsize=(10, 6))
        # Vykreslení zavírací ceny, kde index (datum) je na ose X
        self._daily_history['Close'].plot(ax=plt.gca())

        plt.title(f'Vývoj zavírací ceny - {self.name}', fontsize=16)
        plt.xlabel('Datum', fontsize=12)
        plt.ylabel('Zavírací cena', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()

    def _load_daily_history(self) -> pd.DataFrame:
        """Načte historická data z CSV souboru zpět do pandas.DataFrame."""
        try:
            file_path = f'DATA/{self._yahoo_ticker.ticker}.history.csv'

            # Načtení CSV:
            # 1. index_col='Date': Nastaví sloupec 'Date' jako index.
            # 2. parse_dates=True: Zajistí, že index bude interpretován jako datum (datetime).
            stock_history = pd.read_csv(
                file_path,
                index_col='Date',
                parse_dates=True
            )
            #print(f"✅ Historie pro {self._yahoo_ticker.ticker} načtena z CSV.")
            return stock_history
        except FileNotFoundError:
            #print(f"❌ Chyba: Soubor historie nebyl nalezen na cestě: {file_path}")
            return pd.DataFrame()  # Vrátí prázdný DataFrame v případě chyby

    def _load_stock_info(self) -> dict:
        """Načte informace o akcii z JSON souboru zpět do slovníku."""
        try:
            file_path = f"DATA/{self._yahoo_ticker.ticker}.info.json"
            with open(file_path, 'r', encoding='utf-8') as f:
                stock_info = json.load(f)
            #print(f"✅ Informace pro {self._yahoo_ticker.ticker} načteny z JSON.")
            return stock_info
        except FileNotFoundError:
            #print(f"❌ Chyba: Soubor informací nebyl nalezen na cestě: {file_path}")
            return {}  # Vrátí prázdný slovník v případě chyby
        except json.JSONDecodeError:
            #print(f"❌ Chyba: Soubor JSON je poškozený nebo nečitelný: {file_path}")
            return {}

    def _download_daily_history(self) -> pd.DataFrame:
        stock_history = self._yahoo_ticker.history(period="max", interval="1d")
        stock_history.to_csv(f'DATA/{self._yahoo_ticker.ticker}.history.csv')
        return stock_history

    def _download_stock_info(self) -> dict:
        stock_info = self._yahoo_ticker.get_info()
        file_path = f"DATA/{self._yahoo_ticker.ticker}.info.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(stock_info, f, indent=4)
        return stock_info

class Stock(Asset):
    def __init__(self, ticker):
        super().__init__(ticker)

class Commodity(Asset):
    def __init__(self, ticker):
        super().__init__(ticker)

class Crypto(Asset):
    def __init__(self, ticker):
        super().__init__(ticker)

class ETF(Asset):
    def __init__(self, ticker):
        super().__init__(ticker)

snp = ETF("VUSA.AS")
apple = Stock("AAPL")
bitcoin = Crypto("BTC-USD")
gold = Commodity("GC=F")
etherium = Crypto("ETH-EUR")
#etherium.plot_closing_price()

base_url = 'https://www.alphavantage.co/query'
function = 'TIME_SERIES_DAILY'
symbol = 'XAUUSD'
apikey = '5H3BQBCDJJJ9TTFU'
datatype = "json"
outputsize = "compact"

# Složení URL
params = {
    'function': function,   
    'symbol': symbol,
    'apikey': apikey,
    "datatype" : datatype,
    "outputsize" : outputsize
}

# Dotaz na API


r = requests.get(base_url, params=params)
data = r.json()

pp.pprint(data)

#data = pd.read_csv(io.StringIO(r.text))
#data.to_csv(f'DATA/{"XAUUSD"}.history.csv', index=False)