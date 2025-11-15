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

    def _normalize_history(self, stock_history) -> pd.DataFrame:

        # Převedení datových indexů do struktury pandas DataFrame
        stock_history.index = pd.to_datetime(stock_history.index, utc=True)

        # Převedení indexu jen na datumy bez času
        stock_history.index = stock_history.index.date

        # Vytvoření úplné datové řady pro danou hystorii
        full_date_range = pd.date_range(
            start=stock_history.index.min(),
            end=datetime.now().date(),
            freq='D'  # Frekvence 'D' znamená denní
        )
        full_date_range.name = 'Date'

        # Doplnění prázdných polí sloupce "Close" předchozí hodnotou
        close_prices = stock_history[['Close']]
        stock_history_filled = close_prices.reindex(full_date_range).ffill()

        # Vytvoření sloupce s denním procentuálním přírůstkem
        daily_returns = stock_history_filled['Close'].pct_change()
        daily_returns.name = 'Daily_Return'
        stock_history_filled['Daily_Return'] = daily_returns

        return stock_history_filled

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

    # Vrátí informace o Assetu
    def get_info(self, ticker) ->  dict:
        self._ticker = ticker
        info = self._load_stock_info()
        if not info:
            info = self._download_stock_info()
        return info

    # Vrátí historii Assetu
    def get_history(self, ticker) -> pd.DataFrame:
        self._ticker = ticker
        history = self._load_daily_history()
        if history.empty or get_last_business_day() > history.index.max().date():
            history = self._download_daily_history()

        return history

class YfinanceManager(DownloadManager):
    
    def __init__(self):
        super().__init__()
        self._yahoo_ticker = None

    def get_info(self, ticker):
        self._yahoo_ticker = yf.Ticker(ticker)
        return super().get_info(ticker)
        
    def _download_daily_history(self) -> pd.DataFrame:
        print(f"stahujeme historii {self._ticker}")

        # Stažení dat z Yahoo
        stock_history = self._yahoo_ticker.history(period="max", interval="1d")

        # Úprava dat
        stock_history = self._normalize_history(stock_history)

        # Zápis do souboru
        stock_history.to_csv(f'DATA/{self._ticker}.history.csv')
        return stock_history

    def _download_stock_info(self) -> dict:
        print(f"stahujeme info {self._ticker}")

        # Stažení dat z Yahoo
        stock_info = self._yahoo_ticker.get_info()

        # Zápis do souboru
        file_path = f"DATA/{self._ticker}.info.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(stock_info, f, indent=4)
        return stock_info
    
class AlphaVantage(DownloadManager):
    
    def __init__(self):
        super().__init__()

        # Načtení API klíče z tajného json souboru
        with open("API.json", 'r', encoding='utf-8') as f:
            self.API = json.load(f)

    def _download_daily_history(self) -> pd.DataFrame:
        print("Stahujeme z AlphaVantage")

        # Vytvoření url pro API dotaz
        base_url = 'https://www.alphavantage.co/query'
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': self._ticker,
            'apikey': self.API['AlphaVantage'],
            "datatype" : "csv",
            "outputsize" : "full"
        }

        # Dotaz na API
        r = requests.get(base_url, params=params)
        stock_history = pd.read_csv(io.StringIO(r.text))

        # Sjednocení názvů sloupců
        stock_history = stock_history.rename(columns={
            "timestamp": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume"
        })

        # Nastavení indexu
        stock_history = stock_history.set_index('Date')

        # Úprava dat
        stock_history = self._normalize_history(stock_history)

        # Zápis do souboru
        stock_history.to_csv(f'DATA/{self._ticker}.history.csv')

        return self._load_daily_history()
    
