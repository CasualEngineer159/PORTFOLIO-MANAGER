import pprint

import pandas as pd

from Asset import *
from rich import print

def create_dataframe_from_date(date) -> pd.DataFrame:
    dates = pd.date_range(start=date, end=get_last_business_day(), freq='D')
    df = pd.DataFrame()
    df = df.reindex(dates)
    df.index.name = "Date"
    df["Base"] = np.nan
    df["Profit"] = np.nan
    df["Price"] = np.nan
    df["Growth"] = np.nan
    df["Mask"] = True
    return df

class Portfolio:

    def __init__(self, name: str, currency: str):
        self._name = name
        self._currency = currency
        self._position_dict = {}
        self._portfolio_prices = pd.DataFrame()
        
    # Vytvoří dataframe pro následné ukládání hodnot
    def _create_portfolio_prices(self):
        self._portfolio_prices = create_dataframe_from_date(self._first_date)

    # Vytvoření nové transakce - vytvření/přiřazení pozice
    def new_transaction(self, amount: int, date: datetime, asset: Asset, price: float = None):

        # Odstranění času z data
        date = date.date()

        # Pokud daný asset nemá v portfoliu pozici, vytvoří novou
        if asset not in self._position_dict.keys():
            self._position_dict[asset] = Position(asset)

        # Vytvoření transakce v dané pozici
        self._position_dict[asset].new_transaction(amount, date, price)
    
    # Zjistí datum první transakce
    def _create_first_date(self):
        asset, position = next(iter(self._position_dict.items()))
        date = position.get_first_date()
        for asset, position in self._position_dict.items():
            if position.get_first_date() < date:
                date = position.get_first_date()
        self._first_date = date
        print(date)
    
    # Sečte pozice ve měně portfolia
    def _add_positions(self):
        
        for asset, position in self._position_dict.items():
            
            position_prices = position.get_position(self._currency)
            
            # Sečtení sloupců Base, Profit a Price
            self._portfolio_prices["Base"] = self._portfolio_prices["Base"].add(position_prices["Base"], fill_value=0)
            self._portfolio_prices["Profit"] = self._portfolio_prices["Profit"].add(position_prices["Profit"], fill_value=0)
            self._portfolio_prices["Price"] = self._portfolio_prices["Price"].add(position_prices["Price"], fill_value=0)
            
            # Logický součin masek existence záznamu
            self._portfolio_prices["Mask"] = self._portfolio_prices["Mask"].combine(
                position_prices["Mask"],
                func=lambda x, y: x & y,
                fill_value=True
            )
    
    # Výpočet výkonu pozice
    def _calculate_growth(self):
        self._portfolio_prices["Growth"] = self._portfolio_prices["Price"] / self._portfolio_prices["Base"]
    
    # Změní měnu portfolia
    def change_currency(self, currency: str):
        self._currency = currency
    
    # Vrátí cenový průběh portfolia v čase
    def get_portfolio(self, real:bool = False):
        self._create_first_date()
        self._create_portfolio_prices()
        self._add_positions()
        self._calculate_growth()
        if real is True:
            self._portfolio_prices = self._portfolio_prices[self._portfolio_prices["Mask"]]
        self.plot_price(real)
        print(self._portfolio_prices)
    
    # Vytvoří graf png   
    def plot_price(self, real):
        plot_price(self._portfolio_prices, self._first_date, f"Portfolio {self._name} graf růstu {self._currency} {real}", "Growth")
        plot_price(self._portfolio_prices, self._first_date, f"Portfolio {self._name} graf ceny {self._currency} {real}", "Price")
        plot_price(self._portfolio_prices, self._first_date, f"Portfolio {self._name} graf profitu {self._currency} {real}", "Profit")
        plot_price(self._portfolio_prices, self._first_date, f"Portfolio {self._name} graf báze {self._currency} {real}", "Base")

class Position:
    def __init__(self, asset: Asset):
        self._asset = asset
        self._transaction_list = []
        self._currency = self._asset.get_currency()
        self._prices_calculated = False
        self._amount = 0
    
    # Najde datum první transakce
    def _create_first_date(self):
        date = self._transaction_list[0].get_date()
        for transaction in self._transaction_list:
            if transaction.get_date() < date:
                date = transaction.get_date()
        self._first_date = date
        self._dates = pd.date_range(start=self._first_date, end=get_last_business_day(), freq='D')
    
    # Vytvoří dataframe pro následné ukládání hodnot
    def _create_position_prices(self):
        self._position_prices = create_dataframe_from_date(self._first_date)

    # Vytvoření nového objektu transakce a zařazení do listu transakcí
    def new_transaction(self, amount: int, date: datetime, price: float = None):
        if (self._amount + amount) < 0:
            amount = -self._amount
        self._transaction_list.append(Transaction(self._asset, date, amount, price))
        self._amount = self._amount + amount
        self._prices_calculated = False
    
    # Sečte Base, Profit a Price
    def _add_transactions(self):

        # Postupné sčítání všech transakcí v dané pozici
        for transaction in self._transaction_list:
            
            transaction_prices = transaction.get_transaction()
            
            # Sečtení sloupců Base, Profit a Price
            self._position_prices["Base"] = self._position_prices["Base"].add(transaction_prices["Base"], fill_value=0)
            self._position_prices["Profit"] = self._position_prices["Profit"].add(transaction_prices["Profit"], fill_value=0)
            self._position_prices["Price"] = self._position_prices["Price"].add(transaction_prices["Price"], fill_value=0)
            
            # Logický součin masek existence záznamu
            self._position_prices["Mask"] = self._position_prices["Mask"].combine(
                transaction_prices["Mask"],
                func=lambda x, y: x & y,
                fill_value=True
            )
    
    # Výpočet výkonu pozice
    def _calculate_growth(self):
        self._position_prices["Growth"] = self._position_prices["Price"] / self._position_prices["Base"]
    
    # Měnový převod
    def _currency_exchange(self, currency):
        
        # Vytvoření tickeru pro Forex
        ticker = self._currency + currency + "=X"
        
        # Vytvoření Forexu
        forex = Forex(ticker)
        forex_prices = forex.get_prices(self._first_date)
        
        # Přeindexování na potřebný rozsah a vytvoření masky
        forex_prices = forex_prices.reindex(self._dates)
        forex_prices["Mask"] = forex_prices["Close"].notna()
        
        # Doplnění chybějících hodnot forex exchange forward i backward fill
        forex_prices["Close"] = forex_prices["Close"].ffill().bfill()
        
        # Vytvoření sloupce pro násobení Base
        forex_prices["Close_base"] = np.nan
        for transaction in self._transaction_list:
            date = transaction.get_date()
            date = pd.to_datetime(date)
            forex_prices.loc[date, "Close_base"] = forex_prices.loc[date, "Close"]
            
        # Doplnění chybějících hodnot forex exchange pro base
        forex_prices["Close_base"] = forex_prices["Close_base"].ffill()
        
        # Přenásobení cen měnovým kurzem
        self._position_prices["Base"] = self._position_prices["Base"] * forex_prices["Close_base"]
        self._position_prices["Profit"] = self._position_prices["Profit"] * forex_prices["Close"]
        self._position_prices["Price"] = self._position_prices["Price"] * forex_prices["Close"]
        
        # Logický součin masek existence záznamu
        self._position_prices["Mask"] = self._position_prices["Mask"].combine(
            forex_prices["Mask"],
            func=lambda x, y: x & y,
            fill_value=True
        )
    
    # Vrátí datum první transakce
    def get_first_date(self) -> datetime:
        self._create_first_date()
        return self._first_date
        
    # Vrátí historii pozice
    def get_position(self, currency:str) -> pd.DataFrame:
        
        if not self._prices_calculated:
            self._create_first_date()
            self._create_position_prices()
            self._add_transactions()
        print(f"Asset currency: {self._currency}, portfolio currency: {currency}")
        if not (self._currency == currency):
            self._currency_exchange(currency)
        self._calculate_growth()
        self._prices_calculated = True
        return self._position_prices

class Transaction:

    def __init__(self, asset: Asset, date: datetime, amount: int, price: float = None):
        
        self._asset = asset
        self._date = date
        self._price = price
        self._amount = amount

        self._dates = pd.date_range(start=self._date, end=get_last_business_day(), freq='D')

        self._history = self._asset.get_prices(self._date)
        self._first_record_date = self._asset.get_earliest_record_date()

        self._record_to_date = self._get_record_to_date()
        
        # Kontrola správnosti transakce
        self._check_transaction()

        self._transaction_prices = create_dataframe_from_date(self._date)
        
        # Výpočet průběhu transakce
        self._create_base()
        self._create_change()
        self._create_profit()
        self._create_price()
        self._create_mast()

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
            print(f"[red]!!!Pozor, v datu {self._date} transakce {self._asset.get_name()} ještě není záznam cen!!![/red] první datum záznamu: {self._first_record_date}")
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
                print(f"[red]!!! Cena {self._asset.get_name()} mimo denní rozsah!!![/red] platný rozsah: low: {low}, price: {self._price}, high: {high}")

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
        
    def _create_mast(self):
        self._history = self._history.reindex(self._dates)
        self._transaction_prices["Mask"] = self._history["Close"].notna()

    def get_transaction(self):
        return self._transaction_prices
    
    def get_date(self) -> datetime:
        return self._date