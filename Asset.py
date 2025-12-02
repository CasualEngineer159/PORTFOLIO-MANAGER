import matplotlib.pyplot as plt
from DownloadManager import *

yfinance_m = YfinanceManager()
aplha_vantage_m = AlphaVantage()
twelve_data_m = TwelveData()

def create_dataframe_from_date(date) -> pd.DataFrame:
    _dates = pd.date_range(start=date, end=get_last_business_day(), freq='D')
    df = pd.DataFrame()
    df = df.reindex(_dates)
    df.index.name = "Date"
    df["Base"] = np.nan
    df["Profit"] = np.nan
    df["Price"] = np.nan
    df["Growth"] = np.nan
    df["Mask"] = True
    return df

def plot_price(history, date, plot_name, column):
    plt.figure(figsize=(10, 6))

    history_to_plot = history.loc[date:, [column]]

    # Reindexuje pro správné vykreselní
    history_to_plot = history_to_plot.asfreq('D')

    # Vykreslení zavírací ceny, kde index (datum) je na ose X
    history_to_plot.plot(ax=plt.gca())

    plt.title(f'{plot_name}', fontsize=16)
    plt.xlabel('Datum', fontsize=12)
    plt.ylabel('Zavírací cena', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    filename = f"GRAPHS/{plot_name}.png"
    plt.savefig(filename)

    # Zavřeme figure z paměti, aby se nezobrazila
    plt.close()


class Asset:

    def __init__(self, ticker):
        self._ticker = ticker
        self._stock_info = self.manager.get_info(ticker)
        self._daily_history = self.manager.get_history(ticker)
        self._name = self._stock_info.get("longName", self._ticker)
        
    def get_ticker(self) -> str:
        return self.manager.get_ticker(self._ticker)

    def get_name(self) -> str:
        return self._name

    def get_currency(self) -> str:
        return self._stock_info.get("currency", "USD")

    def get_earliest_record_date(self) -> datetime:
        self._daily_history.sort_index()
        return self._daily_history.index[0]

    def plot_closing_price(self):
        plot_price(self._daily_history, self.get_earliest_record_date(), f"{self._name} closing price graph")

    def get_prices(self, start_date) -> pd.DataFrame:
        self._daily_history.sort_index()
        nearest_row = self._daily_history.index.asof(start_date)
        if pd.isna(nearest_row):
            return self._daily_history.copy()
        return self._daily_history.loc[nearest_row:].copy()

    def get_venue(self):
        return self._stock_info.get("fullExchangeName", None)

class Stock(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)
        #print(self._name)

class Commodity(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)
        #print(self._name)

class Crypto(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)
        #print(self._name)


class ETF(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)
        #print(self._name)

class Futures(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)
        self._name = self._stock_info.get("shortName", self._ticker)
        #print(self._name)

class Forex(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)

    def get_prices(self, start_date) -> pd.DataFrame:
        self._daily_history.sort_index()
        self._daily_history = fill_gaps(self._daily_history)
        return self._daily_history.loc[start_date:].copy()

    def get_rate(self, date) -> float:
        return get_closest_value(self._daily_history, date,"Close")

forex_dict = {}
def forex_creator(from_currency, to_currency) -> Forex:
    ticker = from_currency + to_currency + "=X"
    if ticker in forex_dict.keys():
        return forex_dict[ticker]
    forex = Forex(ticker)
    forex_dict[ticker] = forex
    return forex

asset_dict = {}
def asset_creator(ticker) -> Stock:
    if ticker in asset_dict.keys():
        return asset_dict[ticker]
    stock = Stock(ticker)
    asset_dict[ticker] = stock
    return stock

def get_closest_value(df, wanted_date, column):
    df = df.sort_index()
    idx = df.index.asof(wanted_date)
    if pd.isna(idx):
        idx = df.index[0]
    return df[column].loc[idx]
