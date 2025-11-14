import pandas as pd
import pprint as pp
import yfinance as yf
import requests
import json
import io
from pandas.tseries.offsets import BDay
from datetime import datetime

def get_last_business_day() -> datetime:
    today = datetime.now().date()
    return (today - BDay(1)).date()

class DownloadManager:
    
    def __init__(self):
        self._ticker = None

    def _load_daily_history(self) -> pd.DataFrame:
        """Načte historická data z CSV souboru zpět do pandas.DataFrame."""
        try:
            file_path = f'DATA/{self._ticker}.history.csv'

            # Načtení CSV:
            # 1. index_col='Date': Nastaví sloupec 'Date' jako index.
            # 2. parse_dates=True: Zajistí, že index bude interpretován jako datum (datetime).
            stock_history = pd.read_csv(
                file_path,
                index_col="Date",
                parse_dates=True
            )
            #print(f"✅ Historie pro {self._ticker} načtena z CSV.")
            return stock_history
        except FileNotFoundError:
            #print(f"❌ Chyba: Soubor historie nebyl nalezen na cestě: {file_path}")
            return pd.DataFrame()  # Vrátí prázdný DataFrame v případě chyby

    def _load_stock_info(self) -> dict:
        """Načte informace o akcii z JSON souboru zpět do slovníku."""
        try:
            file_path = f"DATA/{self._ticker}.info.json"
            with open(file_path, 'r', encoding='utf-8') as f:
                stock_info = json.load(f)
            #print(f"✅ Informace pro {self._ticker načteny z JSON.")
            return stock_info
        except FileNotFoundError:
            #print(f"❌ Chyba: Soubor informací nebyl nalezen na cestě: {file_path}")
            return {}  # Vrátí prázdný slovník v případě chyby
        except json.JSONDecodeError:
            #print(f"❌ Chyba: Soubor JSON je poškozený nebo nečitelný: {file_path}")
            return {}
    
    def _download_daily_history(self) -> pd.DataFrame:
        print(f"History download not implemented for {self._ticker}")
        return pd.DataFrame({})
        
    def _download_stock_info(self) -> dict:
        print(f"Info download not implemented for {self._ticker}")
        return {}
        
    def get_info(self, ticker) ->  dict:
        self._ticker = ticker
        info = self._load_stock_info()
        if not info:
            info = self._download_stock_info()
        return info
    def get_history(self, ticker) -> pd.DataFrame:
        self._ticker = ticker
        history = self._load_daily_history()
        if history.empty:
            history = self._download_daily_history()
        return history

class yfinanceManager(DownloadManager):
    
    def __init__(self):
        super().__init__()
        self._yahoo_ticker = None
        
    def get_info(self, ticker):
        self._yahoo_ticker = yf.Ticker(ticker)
        return super().get_info(ticker)
        
    def _download_daily_history(self) -> pd.DataFrame:
        stock_history = self._yahoo_ticker.history(period="max", interval="1d")
        stock_history.to_csv(f'DATA/{self._ticker}.history.csv')
        return stock_history

    def _download_stock_info(self) -> dict:
        print(f"stahujeme {self._ticker}")
        stock_info = self._yahoo_ticker.get_info()
        file_path = f"DATA/{self._ticker}.info.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(stock_info, f, indent=4)
        return stock_info
    
class AlphaVantage(DownloadManager):
    
    def __init__(self):
        super().__init__()
    
    def _download_daily_history(self) -> pd.DataFrame:
        print("Stahujeme z AlphaVantage")
        
        base_url = 'https://www.alphavantage.co/query'
        function = 'TIME_SERIES_DAILY'
        symbol = self._ticker
        apikey = '5H3BQBCDJJJ9TTFU'
        datatype = "csv"
        outputsize = "full"

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
        data = pd.read_csv(io.StringIO(r.text))
        
        pp.pprint(data.head())
        
        data = data.rename(columns={
            "timestamp": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume"
        })
        
        data.to_csv(f'DATA/{"XAUUSD"}.history.csv', index=False)
        return self._load_daily_history()
    
