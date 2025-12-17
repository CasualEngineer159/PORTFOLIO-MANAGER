import pandas as pd
import yfinance as yf
import json
from pandas.tseries.offsets import BDay
from datetime import datetime

# ==============================================================================
# POMOCNÉ FUNKCE PRO PRÁCI S DATY
# ==============================================================================

# Vrátí datum posledního pracovního dne
def get_last_business_day() -> datetime:
    # Získání dnešního data
    today = datetime.now().date()

    # Odečtení jednoho pracovního dne
    return (today - BDay(1)).date()


# Vyplní chybějící dny v časové řadě předchozími hodnotami
def fill_gaps(stock_history: pd.DataFrame) -> pd.DataFrame:
    # Vytvoření úplné datové řady od začátku historie do dneška
    full_date_range = pd.date_range(
        start=stock_history.index.min(),
        end=datetime.now().date(),
        freq='D'
    )
    full_date_range.name = 'Date'

    # Doplnění prázdných polí Close předchozí hodnotou
    stock_history_filled = stock_history[['Close']].reindex(full_date_range).ffill()

    # Doplnění a zachování sloupce Low
    daily_min = stock_history[["Low"]].reindex(full_date_range).ffill()
    stock_history_filled['Low'] = daily_min

    # Doplnění a zachování sloupce High
    daily_max = stock_history[["High"]].reindex(full_date_range).ffill()
    stock_history_filled['High'] = daily_max

    # Vrátí doplněná data
    return stock_history_filled


# ==============================================================================
# VNITŘNÍ FUNKCE PRO ČIŠTĚNÍ DAT (NORMALIZACE)
# ==============================================================================

# Odstraní řádky, které mají duplicitní zavírací cenu po sobě
def _delete_duplicit_data(stock_history: pd.DataFrame) -> pd.DataFrame:
    # Vytvoření masky duplicitních hodnot
    duplicate_mask = (stock_history["Close"] == stock_history["Close"].shift())

    # Odfiltrování duplicit pomocí inverzní masky
    stock_history_clean = stock_history[~duplicate_mask].copy()

    # Vrátí vyčištěná data
    return stock_history_clean


# Upraví index prvního záznamu, aby těsně navazoval na druhý (řešení mezer po filtraci)
def _close_initial_gap(stock_history: pd.DataFrame) -> pd.DataFrame:
    # Získání indexů prvních dvou prvků
    old_first_index = stock_history.index[0]
    second_index = stock_history.index[1]

    # Výpočet nového data pro první prvek
    new_first_index = second_index - pd.Timedelta(days=1)

    # Přejmenování indexu
    stock_history.rename(index={old_first_index: new_first_index}, inplace=True)

    # Vrátí upravený dataframe
    return stock_history


# Odstraní záznamy, kde se Low rovná High (chybná nebo "plochá" data)
def _delete_flat_data(stock_history: pd.DataFrame) -> pd.DataFrame:
    # Vytvoření masky pro plochá data
    flat_mask = (stock_history["Low"] == stock_history["High"])

    # Odfiltrování plochých dat
    stock_history_clean = stock_history[~flat_mask].copy()

    # Vrátí vyčištěná data
    return stock_history_clean


# Identifikuje a odstraní nesmyslné výkyvy v datech (outliery)
def _delete_outliers(stock_history: pd.DataFrame) -> pd.DataFrame:
    # Nastavení limitů pro růst a pád
    growth_threshold = 1.0
    fall_threshold = -0.5

    # Výpočet denní procentuální změny
    daily_returns = stock_history['Close'].pct_change()

    # Identifikace extrémních hodnot
    outlier_mask_growth = (daily_returns > growth_threshold)
    outlier_mask_fall = (daily_returns < fall_threshold)

    # Získání indexů těchto hodnot
    outlier_index_growth = stock_history[outlier_mask_growth].index.tolist()
    outlier_index_fall = stock_history[outlier_mask_fall].index.tolist()

    # Spárování začátků a konců chyb
    pairs = list(zip(outlier_index_growth, outlier_index_fall))

    # Pokud nejsou nalezeny chyby, vrátíme původní data
    if not pairs:
        return stock_history

    # Odstranění chybných bloků dat
    for start_date, end_date in pairs:
        index_to_delete = stock_history.loc[start_date:(end_date - pd.Timedelta(days=1))].index
        stock_history = stock_history.drop(index_to_delete)

    # Vrátí data bez outlierů
    return stock_history


# Provede kompletní proces normalizace dat
def _normalize_history(stock_history: pd.DataFrame) -> pd.DataFrame:
    # Sjednocení formátu indexu na UTC datetime
    stock_history.index = pd.to_datetime(stock_history.index, utc=True)

    # Převedení indexu pouze na datumy
    stock_history.index = stock_history.index.date

    # Seřazení podle data
    stock_history = stock_history.sort_index()

    # Postupné čištění dat
    stock_history = _delete_outliers(stock_history)
    stock_history = _delete_duplicit_data(stock_history)
    stock_history = _delete_flat_data(stock_history)
    stock_history = _close_initial_gap(stock_history)

    # Výpočet sloupce s denní výnosností
    daily_returns = stock_history['Close'].pct_change()
    daily_returns.name = 'return'
    stock_history['return'] = daily_returns

    # Nastavení názvu indexu
    stock_history.index.name = 'Date'

    # Vrátí normalizovaná data
    return stock_history


# ==============================================================================
# HLAVNÍ MANAŽER PRO STAHOVÁNÍ A UKLÁDÁNÍ DAT
# ==============================================================================

class DownloadManager:

    def __init__(self):
        # Inicializace vnitřního tickeru
        self._ticker = None

    def get_ticker(self, ticker: str) -> str:
        # Vrátí název tickeru
        return ticker

    # Načte historii dat z lokálního CSV souboru
    def _load_daily_history(self) -> pd.DataFrame:
        try:
            # Definice cesty k souboru
            file_path = f'../DATA/ASSET_HISTORY/{self._ticker}.history.csv'

            # Načtení dat s nastavením indexu na datum
            stock_history = pd.read_csv(
                file_path,
                index_col="Date",
                parse_dates=True
            )

            # Úprava indexu na čisté datum
            stock_history.index = stock_history.index.date

            # Vrátí načtená data
            return stock_history
        except (FileNotFoundError, pd.errors.EmptyDataError):
            # Vrátí prázdný DataFrame v případě chyby
            return pd.DataFrame()

    # Načte meta informace o aktivu z JSON souboru
    def _load_stock_info(self) -> dict:
        try:
            # Definice cesty k souboru
            file_path = f"../DATA/ASSET_INFO/{self._ticker}.info.json"

            # Otevření a načtení JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                stock_info = json.load(f)

            # Vrátí načtené informace
            return stock_info
        except (FileNotFoundError, json.JSONDecodeError):
            # Vrátí prázdný slovník v případě chyby
            return {}

    # Abstraktní metoda pro stahování historie (přepisována v potomcích)
    def _download_daily_history(self) -> pd.DataFrame:
        return pd.DataFrame({})

    # Abstraktní metoda pro stahování informací (přepisována v potomcích)
    def _download_stock_info(self) -> dict:
        return {}

    # Veřejná metoda pro získání informací (zkusí disk, pak internet)
    def get_info(self, ticker: str) -> dict:
        self._ticker = ticker
        info = self._load_stock_info()
        if not info:
            info = self._download_stock_info()
        return info

    # Veřejná metoda pro získání historie (zkusí disk, pak internet pokud jsou data stará)
    def get_history(self, ticker: str) -> pd.DataFrame:
        self._ticker = ticker
        history = self._load_daily_history()

        # Kontrola, zda jsou data aktuální vzhledem k poslednímu pracovnímu dni
        if history.empty or get_last_business_day() > history.index.max():
            history = self._download_daily_history()

        return history


# ==============================================================================
# IMPLEMENTACE KONKRÉTNÍCH API POSKYTOVATELŮ
# ==============================================================================

class YfinanceManager(DownloadManager):

    def __init__(self):
        super().__init__()
        self._yahoo_ticker_obj = None

    # Rozšířená metoda pro získání informací přes Yahoo Finance
    def get_info(self, ticker: str):
        self._yahoo_ticker_obj = yf.Ticker(ticker)
        return super().get_info(ticker)

    # Stáhne historická data z Yahoo Finance
    def _download_daily_history(self) -> pd.DataFrame:
        # Stažení maximální historie
        stock_history = self._yahoo_ticker_obj.history(period="max", interval="1d")

        # Provedení normalizace
        stock_history = _normalize_history(stock_history)

        # Uložení do CSV pro budoucí použití
        file_name = self.get_ticker(self._ticker)
        stock_history.to_csv(f'../DATA/ASSET_HISTORY/{file_name}.history.csv')

        # Vrátí stažená data
        return stock_history

    # Stáhne meta informace z Yahoo Finance
    def _download_stock_info(self) -> dict:
        # Stažení info slovníku
        stock_info = self._yahoo_ticker_obj.get_info()

        # Uložení do JSON
        file_path = f"../DATA/ASSET_INFO/{self._ticker}.info.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(stock_info, f, indent=4)

        # Vrátí stažené informace
        return stock_info

    # Vrátí oficiální symbol tickeru
    def get_ticker(self, ticker: str) -> str:
        return yf.Ticker(ticker).ticker
