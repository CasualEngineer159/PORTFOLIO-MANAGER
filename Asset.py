import matplotlib.pyplot as plt
from DownloadManager import *

yfinance_m = YfinanceManager()
aplha_vantage_m = AlphaVantage()


def plot_price(history, date, plot_name):
    plt.figure(figsize=(10, 6))

    history_to_plot = history.loc[date:, ["Close"]]

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

    def get_earliest_record_date(self) -> datetime:
        self._daily_history.sort_index()
        return self._daily_history.index[0]

    def plot_closing_price(self):
        plot_price(self._daily_history, self.get_earliest_record_date(), f"{self._name} closing price graph")

    def get_prices(self, start_date) -> pd.DataFrame:
        self._daily_history.sort_index()
        return self._daily_history.loc[start_date:].copy()


class Stock(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)
        #print(self._name)

class Commodity(Asset):
    def __init__(self, ticker):
        self.manager = aplha_vantage_m
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