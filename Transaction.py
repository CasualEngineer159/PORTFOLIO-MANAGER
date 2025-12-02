from Asset import *
from enum import IntEnum
from rich import print
from typing import Tuple

class TransactionType(IntEnum):
    LONG = 1
    FRACTION_LONG = 2
    SHORT = 3

class Transaction:

    def __init__(self,
                 asset: Asset,
                 date: datetime,
                 amount_owned : float,
                 amount: int = None,
                 price: float = None
                 ):

        self._asset = asset
        self._date = date
        self._amount_owned = amount_owned
        self._amount = amount
        self._price = price
        self._transaction_prices = create_dataframe_from_date(self._date)

        # Nastavení parametrů -> různé dle typu transakce
        self._set_parameters()

        # Kontrola správnosti transakce
        self._check_transaction()

        # Kontrola a upravení množství
        self._check_amount(amount_owned)

        # Výpočet průběhu transakce
        self._create_base()
        self._create_change()
        self._create_profit()
        self._create_price()
        self._create_mask()

        #print(f"Následuje výpis průběhu transakce:")
        #print(self._transaction_prices)

    def _set_parameters(self):
        ...

    def get_amount(self) -> float:
        return self._amount

    def _check_amount(self, amount_owned):
        # Kontrola zda se nedostáváme s počtem do mínusu
        if amount_owned + self._amount < 0:
            self._amount = -amount_owned
        print(f"""
        Původní počet aktiva: {amount_owned}, nakoupeno: {self._amount}
        """)

    def _get_history(self):
        self._dates = pd.date_range(start=self._date, end=get_last_business_day(), freq='D')
        self._history = self._asset.get_prices(self._date)
        self._first_record_date = self._asset.get_earliest_record_date()
        self._record_to_date = self._get_record_to_date()

    def _get_record_to_date(self) -> pd.DataFrame:
        nearest_row = self._history.index.asof(self._date)
        if pd.isna(nearest_row):
            self._history = self._history.reindex(self._dates)
            self._history.index = self._history.index.date
            return self._get_record_to_date()
        return self._history.loc[nearest_row]

    def _check_transaction(self):

        # Pokud byla transakce provedena dříve než existuje záznam, vyhodíme varování
        if self._date < self._first_record_date:
            print(
                f"[red]!!!Pozor, v datu {self._date} transakce {self._asset.get_name()} ještě není záznam cen!!![/red] první datum záznamu: {self._first_record_date}")
            # Jestli nebyla zadána cena nákupu, určíme z nejbližší zavírací ceny
            if self._price is None:
                self._price = self._history.loc[self._first_record_date, "Close"]
        else:
            # Jestli nebyla zadána cena nákupu, určíme z nejbližší zavírací ceny
            if self._price is None:
                self._price = self._record_to_date["Close"]

            # Zkontrolujeme zda cena zapadá do denního rozmezí
            low = self._record_to_date["Low"]
            high = self._record_to_date["High"]
            if not low <= self._price <= high:
                print(f"""
        [red]!!! Cena {self._asset.get_name()} mimo denní rozsah!!![/red]
        Platný rozsah: low: {low}, price: {self._price}, high: {high}""")
                price_temp = self._price * self._amount
                if self._price > high:
                    self._price = high
                else:
                    self._price = low
                self._amount = price_temp / self._price
                print(f"""
        [orange]Transakce bude převedena na frakční:[/orange]
        Nová nákupní cena: {self._price}
""")

    def _create_base(self):
        self._transaction_prices["Base"] = self._amount * self._price

    def _create_change(self):

        # Vytvoření řady změny se začátkem v datu transakce
        returns = self._history.loc[self._date:, "return"]
        returns = returns.reindex(index=self._transaction_prices.index)
        returns = returns.fillna(0) + 1

        # Výpočet procentuálního rozdílu nákupní ceny od poslední obchodované toho dne
        intraday_change = (self._history.iloc[0]["Close"] - self._price) / self._price + 1
        if pd.isna(intraday_change):
            intraday_change = (self._history.loc[self._first_record_date, "Close"] - self._price) / self._price + 1

        # Nastavení intraday change na den nákupu
        returns.iloc[0] = intraday_change

        self._transaction_prices["Growth"] = returns.cumprod()

    def _create_profit(self):
        self._transaction_prices["Profit"] = self._transaction_prices["Base"] * (self._transaction_prices["Growth"] - 1)

    def _create_price(self):
        self._transaction_prices["Price"] = self._transaction_prices["Base"].add(self._transaction_prices["Profit"])

    def _create_mask(self):
        _dates = pd.date_range(start=self._date, end=get_last_business_day(), freq='D')
        self._history = self._history.reindex(_dates)
        self._transaction_prices["Mask"] = self._history["Close"].notna()

    def get_transaction(self):
        return self._transaction_prices

    def get_date(self) -> datetime:
        return self._date

class LongTransaction(Transaction):
    def __init__(self,
                 asset: Asset,
                 date: datetime,
                 amount_owned : float,
                 amount: int = None,
                 price: float = None
                 ):
        super().__init__(asset, date, amount_owned, amount, price)

    def _set_parameters(self):

        # Získání historie assetu
        self._get_history()

        # Získání jména assetu
        self._name = self._asset.get_name()

class LongFractionTransaction(Transaction):
    def __init__(self,
                 asset: Asset,
                 date: datetime,
                 amount_owned : float,
                 amount: int = None,
                 price: float = None
                 ):
        super().__init__(asset, date, amount_owned, amount, price)

    def _set_parameters(self):

        # Získání historie assetu
        self._get_history()

        # Získání jména assetu
        self._name = self._asset.get_name()

        # Určíme zavírací cenu
        close_price = self._record_to_date["Close"]
        if pd.isna(close_price):
            close_price = self._history.loc[self._first_record_date, "Close"]

        self._amount = self._price / close_price
        self._price = close_price








