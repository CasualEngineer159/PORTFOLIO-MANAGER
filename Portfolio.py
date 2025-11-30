from idlelib import history

from matplotlib import dates

from Asset import *
from rich import print
from enum import IntEnum
from Transaction import *

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
    def new_long_transaction(self, date: datetime, asset: Asset, amount: int = None, price: float = None, fraction: bool = False):

        # Odstranění času z data
        date = date.date()

        # Pokud daný asset nemá v portfoliu pozici, vytvoří novou
        if asset not in self._position_dict.keys():
            self._position_dict[asset] = Position(asset)

        # Vytvoření transakce v dané pozici
        if not fraction:
            self._position_dict[asset].new_transaction(amount, date, TransactionType.LONG, price)
        else:
            self._position_dict[asset].new_transaction(amount, date, TransactionType.FRACTION_LONG, price)

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

long_transaction_factory = LongTransactionPrepper()
long_fraction_transaction_factory = LongFractionTransactionPrepper()

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
    def new_transaction(self, amount: int, date: datetime,transaction_type: TransactionType, price: float = None):

        transaction, amount_bought = None, None

        if transaction_type == TransactionType.LONG:
            transaction, amount_bought = long_transaction_factory.new_transaction(asset=self._asset,
                                                                                  date=date,
                                                                                  amount=amount,
                                                                                  price=price,
                                                                                  amount_owned=self._amount)

        elif transaction_type == TransactionType.FRACTION_LONG:
            transaction, amount_bought = long_fraction_transaction_factory.new_transaction(asset=self._asset,
                                                                                  date=date,
                                                                                  amount=amount,
                                                                                  price=price,
                                                                                  amount_owned=self._amount)
        self._transaction_list.append(transaction)
        self._amount = self._amount + amount_bought
        print(f"new amount owned: {self._amount}")
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
