import pandas as pd
import pprint as pp
import yfinance as yf
import json
from pandas.tseries.offsets import BDay
from datetime import datetime
import matplotlib.pyplot as plt

def get_last_business_day() -> datetime:
    today = datetime.now().date()
    return (today - BDay(1)).date()

class Asset:

    def __init__(self, ticker):
        self.ticker = ticker
        self.yahoo_ticker = yf.Ticker(ticker)
        self.stock_info = self.load_stock_info()
        self.daily_history = self.load_daily_history()

        if not self.stock_info:
            self.stock_info = self.download_stock_info()
        if self.daily_history.empty or get_last_business_day() > self.daily_history.index.max().date():
            self.daily_history = self.download_daily_history()

        self.name = self.stock_info["shortName"]
        #print(self.name)

    def plot_closing_price(self):

        plt.figure(figsize=(10, 6))
        # Vykreslení zavírací ceny, kde index (datum) je na ose X
        self.daily_history['Close'].plot(ax=plt.gca())

        plt.title(f'Vývoj zavírací ceny - {self.name}', fontsize=16)
        plt.xlabel('Datum', fontsize=12)
        plt.ylabel('Zavírací cena', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()

    def load_daily_history(self) -> pd.DataFrame:
        """Načte historická data z CSV souboru zpět do pandas.DataFrame."""
        try:
            file_path = f'DATA/{self.yahoo_ticker.ticker}.history.csv'

            # Načtení CSV:
            # 1. index_col='Date': Nastaví sloupec 'Date' jako index.
            # 2. parse_dates=True: Zajistí, že index bude interpretován jako datum (datetime).
            stock_history = pd.read_csv(
                file_path,
                index_col='Date',
                parse_dates=True
            )
            print(f"✅ Historie pro {self.yahoo_ticker.ticker} načtena z CSV.")
            return stock_history
        except FileNotFoundError:
            print(f"❌ Chyba: Soubor historie nebyl nalezen na cestě: {file_path}")
            return pd.DataFrame()  # Vrátí prázdný DataFrame v případě chyby

    def load_stock_info(self) -> dict:
        """Načte informace o akcii z JSON souboru zpět do slovníku."""
        try:
            file_path = f"DATA/{self.ticker}.info.json"
            with open(file_path, 'r', encoding='utf-8') as f:
                stock_info = json.load(f)
            print(f"✅ Informace pro {self.ticker} načteny z JSON.")
            return stock_info
        except FileNotFoundError:
            print(f"❌ Chyba: Soubor informací nebyl nalezen na cestě: {file_path}")
            return {}  # Vrátí prázdný slovník v případě chyby
        except json.JSONDecodeError:
            print(f"❌ Chyba: Soubor JSON je poškozený nebo nečitelný: {file_path}")
            return {}

    def download_daily_history(self) -> pd.DataFrame:
        stock_history = self.yahoo_ticker.history(period="max", interval="1d")
        stock_history.to_csv(f'DATA/{self.yahoo_ticker.ticker}.history.csv')
        return stock_history

    def download_stock_info(self) -> dict:
        stock_info = self.yahoo_ticker.get_info()
        file_path = f"DATA/{self.ticker}.info.json"
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
gold.plot_closing_price()
apple.plot_closing_price()