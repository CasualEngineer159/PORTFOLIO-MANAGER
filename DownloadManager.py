import pandas as pd
import pprint as pp
import yfinance as yf
import requests
import json
import io
from pandas.tseries.offsets import BDay
from datetime import datetime
import numpy as np

from scipy.stats import zscore


def get_last_business_day() -> datetime:
    today = datetime.now().date()
    return (today - BDay(1)).date()

# Vrátí vyfiltrovanou historii dat, filtruje na základě hodnot sloupce "Close"
def _delete_duplicit_data(stock_history) -> pd.DataFrame:

    # Vytoření masky duplicitů - pokud se po posunu hodnot o jedno nahoru pozice v seznamu rovnají, bude na této pozici v masce True)
    duplicit_mask = (stock_history["Close"] == stock_history["Close"].shift())

    # Nastavení nového vyčištěného seznamu invertování masky (v novém seznamu budou jen pole kde je v masce False, neboli žádné duplicity)
    stock_history_clean = stock_history[~duplicit_mask].copy()

    # Vrátí vyfiltrovanou historii
    return stock_history_clean

# Přimknutí první hodnoty v seznamu k další následující pro příklad že by tam při filtraci vznikla mezera
def _close_initial_gap(stock_history) -> pd.DataFrame:

    # Načtení datumů prvních dnou hodnot
    stary_index_prvniho = stock_history.index[0]
    index_druheho = stock_history.index[1]

    # Výpočet nového datumu
    novy_index_prvniho = index_druheho - pd.Timedelta(days=1)

    # Přenastavení indexu první hodnoty
    stock_history.rename(index={stary_index_prvniho: novy_index_prvniho}, inplace=True)

    # Přimknutí první hodnoty v seznamu k další následující pro příklad že by tam při filtraci vznikla mezera
    return stock_history

# Vrátí opravený dataframe kde jen s honotami kde se Low a High nerovnají
def _delete_flat_data(stock_history) -> pd.DataFrame:

    # Vytvoření masky kde se Low rovná High
    flat_mask = (stock_history["Low"] == stock_history["High"])

    # Vytvoření opravené ho dataframe pomocí inverze masky
    stock_history_clean = stock_history[~flat_mask].copy()

    # Vrátí opravený dataframe kde jen s honotami kde se Low a High nerovnají
    return stock_history_clean

# Vrátí dataframe se smazanými outliery
def _delete_outliers(stock_history) -> pd.DataFrame:

    # Nastavení thresholdů
    growth_threshold = 1.0
    fall_threshold = -0.5

    # Výpočet procentuální změny mezi daty
    daily_returns = stock_history['Close'].pct_change()

    # Vytvoření masek které najdou hodnoty změny nevyhovující thresholdům
    outlier_mask_growth = (daily_returns > growth_threshold)
    outlier_mask_fall = (daily_returns < fall_threshold)

    # Vytvoření listů indexů pomocí masek
    outlier_index_growth = stock_history[outlier_mask_growth].index.tolist()
    outlier_index_fall = stock_history[outlier_mask_fall].index.tolist()

    print(f"\nIndexy, kde je chyba podle z threshold: {outlier_index_growth}")
    print(f"\nIndexy, kde je chyba podle z threshold: {outlier_index_fall}")

    # Vytvoření párů pro vymazání
    pairs = list(zip(outlier_index_growth, outlier_index_fall))
    print(f"\nNalezeny tyto chybné bloky (páry): {pairs}")

    # Pokud je list pairs prázdný, vrátíme předčasně
    if not pairs:
        return stock_history

    # Iterací vymažeme páry dat
    for start_date, end_date in pairs:

        index_to_delete = stock_history.loc[start_date:(end_date - pd.Timedelta(days=1))].index

        stock_history = stock_history.drop(index_to_delete)

    # Vrátí dataframe se smazanými outliery
    return stock_history

# Vrátí plně upravená data připravené k použití v grafu
def _normalize_history(stock_history) -> pd.DataFrame:

    # Převedení datových indexů do struktury pandas DataFrame
    stock_history.index = pd.to_datetime(stock_history.index, utc=True)

    # Převedení indexu jen na datumy bez času
    stock_history.index = stock_history.index.date

    # Seřazení dat dne indexu (data)
    stock_history = stock_history.sort_index()
    
    # Smazání outlierů
    stock_history = _delete_outliers(stock_history)

    # Smazání opakujících se dat
    stock_history = _delete_duplicit_data(stock_history)

    # Smazání plochých dat (Low = High)
    stock_history = _delete_flat_data(stock_history)

    # Odstranění mezery mezi prvním a druhým záznamem (vzniké filtrací)
    stock_history = _close_initial_gap(stock_history)

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
    daily_returns.name = 'return'
    stock_history_filled['return'] = daily_returns

    # Zachování doplněného sloupce min
    daily_min = stock_history[["Low"]].reindex(full_date_range).ffill()
    daily_min.name = 'Low'
    stock_history_filled['Low'] = daily_min

    # Zachování doplněného sloupce max
    daily_max = stock_history[["High"]].reindex(full_date_range).ffill()
    daily_max.name = 'High'
    stock_history_filled['High'] = daily_max

    # Vrátí plně upravená data připravené k použití v grafu
    return stock_history_filled


class DownloadManager:
    
    def __init__(self):
        self._ticker = None
        
    def get_ticker(self, ticker) -> str:
        return ticker

    def _load_daily_history(self) -> pd.DataFrame:
        # Načte historická data z CSV souboru zpět do pandas.DataFrame.
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
        # Načte informace o akcii z JSON souboru zpět do slovníku.
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
        #print(f"History download not implemented for {self._ticker}")
        return pd.DataFrame({})
        
    def _download_stock_info(self) -> dict:
        #print(f"Info download not implemented for {self._ticker}")
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
        #print(f"Poslední BDay: {get_last_business_day()}, poslední datum staženo: {history.index.max().date()}")
        if history.empty or get_last_business_day() > history.index.max().date():
            #print("Tady probíhá stahování")
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
        
        pp.pprint(stock_history.head())

        # Úprava dat
        stock_history = _normalize_history(stock_history)

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
    
    def get_ticker(self, ticker):
        return yf.Ticker(ticker).ticker
    
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
        stock_history = _normalize_history(stock_history)

        # Zápis do souboru
        stock_history.to_csv(f'DATA/{self._ticker}.history.csv')

        return self._load_daily_history()

    def _download_daily_history_(self) -> pd.DataFrame:
        print("načítáme starý soubor")
        file_path = f'DATA/XAUUSD.history.previous.csv'

        # Načtení CSV:
        # 1. index_col='Date': Nastaví sloupec 'Date' jako index.
        # 2. parse_dates=True: Zajistí, že index bude interpretován jako datum (datetime).
        stock_history = pd.read_csv(
            file_path,
            index_col="Date",
            parse_dates=True
        )
        # print(f"✅ Historie pro {self._ticker} načtena z CSV.")
        # Zápis do souboru
        stock_history = _normalize_history(stock_history)
        stock_history.to_csv(f'DATA/{self._ticker}.history.csv')
        return stock_history

    
