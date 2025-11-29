import pprint

import pandas as pd

from Asset import *
from rich import print

class Portfolio:

    def __init__(self, name: str, currency: str):
        self._name = name
        self._currency = currency
        self._position_dict = {}
        self._portfolio_prices = pd.DataFrame()

    def new_transaction(self, amount: int, date: datetime, asset: Asset, price: float = None):

        # Odstranění času z data
        date = date.date()

        # Pokud daný asset nemá v portfoliu pozici, vytvoří novou
        if asset not in self._position_dict.keys():
            self._position_dict[asset] = Position(asset)

        # Vytvoření transakce v dané pozici
        self._position_dict[asset].new_transaction(amount, date, price)



class Position:
    def __init__(self, asset: Asset):
        self._asset = asset
        self._transaction_list = []

    # Vytvoření nového objektu transakce a zařazení do listu transakcí
    def new_transaction(self, amount: int, date: datetime, price: float = None):
        self._transaction_list.append(Transaction(self._asset, date, price, amount))


class Transaction:

    def __init__(self, asset: Asset, date: datetime, price: float, amount: int):
        self._asset = asset
        self._date = date
        self._price = price
        self._amount = amount

        dates = pd.date_range(start=date, end=get_last_business_day, freq='D')

        self._history = self._asset.get_prices(date)
        self._history = self._history.reindex(dates)
        self._first_record_date = self._asset.get_earliest_record_date()

        self._record_to_date = self._get_record_to_date()
        print(self._record_to_date)

        self._throw_warnings()

        self._transaction_prices = pd.DataFrame()
        self._transaction_prices = self._transaction_prices.reindex(dates)

    def _get_record_to_date(self) -> pd.DataFrame:
        nearest_row = self._history.index.asof(self._date)
        return self._history.loc[nearest_row]

    def _throw_warnings(self):
        if self._date < self._first_record_date:
            print(f"[red]!!!Pozor, v datu {self._date} transakce {self._asset.get_name()} ještě není záznam cen!!![/red] první datum záznamu: {self._first_record_date}")
        ...

    def _create_base(self):
        self._transaction_prices["Base"] = self._amount * self._price

    def _create_change(self):

        # Vytvoření řady změny se začátkem v datu transakce
        returns = self._history.loc[self._date:, "return"]
        returns = returns.reindex(index=self._transaction_prices.index)
        returns = returns.fillna(0) + 1

        # Výpočet procentuálního rozdílu nákupní ceny od poslední obchodované toho dne
        intraday_change = (self._history.iloc[0]["Close"] - self._price) / self._price + 1

        # Nastavení intraday change na den nákupu
        returns.iloc[0] = intraday_change

        # Převedení na kumulativní produkt
        returns = returns.cumprod()

        self._transaction_prices["Change"] = returns

    def _create_profit(self):
        self._transaction_prices["Profit"] = self._transaction_prices["Base"] * self._transaction_prices["Change"]

    def get_transaction(self):
        self._create_base()
        self._create_change()
        self._create_profit()
        return self._transaction_prices

apple = Stock('AAPL')

portfolio = Portfolio("test", "EUR")
portfolio.new_transaction(3, datetime(1970,10,12) ,apple ,110)
#portfolio.new_transaction(2, datetime(2020,10,15) ,apple ,110)
#print(portfolio._position_dict)
#pp.pprint(portfolio._position_dict[apple]._transaction_list)
#pp.pprint(portfolio._position_dict[apple]._transaction_list[0].get_transaction())
#pp.pprint(portfolio._position_dict[apple]._transaction_list[1].get_transaction())