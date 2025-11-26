import pandas as pd

from Asset import *
from rich import print

class Position:
    
    def __init__(self, price: float, date: datetime, asset: Asset, amount: int):
        self._asset = asset
        self._ticker = asset.get_ticker()
        self._amount = amount
        self._name = asset.get_name()
        self._position_changes = {}
        self._daily_history = None
        self.change_position(amount=amount, date=date, price=price)

    def get_currency(self) -> str:
        return self._asset.get_currency()

    def _get_first_buy_date(self) -> datetime:
        keys = self._position_changes.keys()
        return min(keys)

    # Doplnění dat
    def _fill_history_data(self):

        first_date = self._get_first_buy_date()
        print(first_date)
        
        # Vytvoření úplné datové řady pro danou hystorii
        full_date_range = pd.date_range(
            start=first_date,
            end=get_last_business_day(),
            freq='D'  # Frekvence 'D' znamená denní
        )
        full_date_range.name = 'Date'
        
        #self._daily_history = self._daily_history.reindex(full_date_range)

    
    # Vrátí data růstu z dané transakce
    def _create_transaction_history(self, date) -> pd.DataFrame:

        # Získání informací o pozici
        amount = self._position_changes[date][0]
        price = self._position_changes[date][1]

        daily_history_copy = self._daily_history.copy(deep=True)

        multiplier_index_to_change = 0

        # Pokud ještě neexistuje záznam, doplníme
        if date < self._asset.get_earliest_record_date():

            closing_price = daily_history_copy.loc[self.get_earliest_record_date(), "Close"]
            daily_history_copy.loc[date, "Close"] = price
            daily_history_copy = daily_history_copy.sort_index()
            multiplier_index_to_change = 1

        else:
            new_index = daily_history_copy.index.union([date])
            re_indexed_series = daily_history_copy['Close'].reindex(new_index, method='bfill')
            closing_price = re_indexed_series.loc[date]

        # Výpočet procentuálního rozdílu nákupní ceny od poslední obchodované toho dne
        intraday_change = (closing_price - price) / price
        print(intraday_change)

        # Převedení daily_change na procenta
        new_index = daily_history_copy.index.union([date])
        re_indexed_series = daily_history_copy['return'].reindex(new_index, method='bfill')
        multipliers = 1 + re_indexed_series.loc[date:].copy(deep=True)
        multipliers.iloc[0] = intraday_change + 1

        if date < self._asset.get_earliest_record_date():
            multipliers.iloc[1] = 1

        #pp.pprint(multipliers)

        # Výpočet kumulativního nárůstu na jednotku
        cum_multipliers = multipliers.cumprod()

        # Výpočet celkového růstu pozice
        prices = price * amount * cum_multipliers

        # Převod na dataframe
        prices = prices.to_frame(name="Close")

        # Vrátí data růstu z dané transakce jako dataframe
        return prices

    def plot_price(self):
        plot_price(self.get_position_history(), self._get_first_buy_date(), f"{self._name} position price growth graph", "Close")

    def get_position_history(self) -> pd.DataFrame:
        
        growth_list = []
        
        for date in self._position_changes.keys():
            
            transaction_df = self._create_transaction_history(date)
            growth_list.append(transaction_df)
            
        if not growth_list:
            
            return pd.DataFrame()

        position_history = growth_list[0]    

        for i in range(1, len(growth_list)):

            position_history = position_history.add(growth_list[i], fill_value=0)

        position_history["Return"] = self._asset.get_prices(self._get_first_buy_date()).loc[:, "return"]

        #print(f"Tisk {self._ticker} unvitř get_position_history")
        #pp.pprint(position_history.head())

        position_history.to_csv(f'DATA/{self._ticker}.position.history.csv')

        #self.plot_price()

        return position_history
        
    def print_overview(self):
        print(f"Number of {self._name} owned is {self._amount}.")
        
    def __str__(self):
        print(f"Number of {self._name} owned is {self._amount}. Transactions:")
        pp.pprint(self._position_changes)
        return ""

    def get_earliest_record_date(self) -> datetime:
        return self._asset.get_earliest_record_date()

    def _get_history(self, date):
        if (self._daily_history is None) or (self._daily_history.index.min() > date):
            self._daily_history = self._asset.get_prices(date)

    def change_position(self, amount: int, date: datetime, price: float):

        self._get_history(date)
            
        # Handle pokud jsou dvě transakce za jeden den. Sečte se počet kusů a zprůměruje cena
        if date in self._position_changes:
            new_amount = self._position_changes[date][0] + amount
            new_price = (self._position_changes[date][1] * self._position_changes[date][0] + amount * price) / new_amount
            self._amount = max(0, new_amount)
            self._position_changes[date] = [new_amount, new_price]
        else:
            self._position_changes[date] = [max(0, amount), price]
            self._amount = max(0, amount)
        
        # Pokud existuje záznam, zkontrolovat jestli je cena v platném rozsahu a když ne hodit výstrahu uživateli
        # Pokud záznam neexistuje, hodit výstrahu a reindexovat historii
        if self.get_earliest_record_date() < date:

            # Zjistit High a Low daného dne a zkontrolovat že jsme uvnitř
            low = self._daily_history.asof(date).loc["Low"]
            high = self._daily_history.asof(date).loc["High"]
            if not low <= price <= high:
                print(f"[red]!!! Cena {self._name} mimo denní rozsah!!![/red] platný rozsah: low: {low}, price: {price}, high: {high}")
        else:
            
            print(f"[red]!!!Pozor, v datu {date} transakce {self._name} ještě není záznam cen!!![/red] první datum záznamu: {self.get_earliest_record_date()}")

            # Reindexovat záznam do posledního nejzazšího potřebného data (hodnoty budou NaN)
            self._fill_history_data()


class Portfolio:
    def __init__(self, currency: str):
        self._currency = currency
        self._position_dict = {}
        
    def __str__(self):
        for item in self._position_dict.values():
            item.print_overview()
        return ""

    def _add_positions(self):

        self._portfolio_history = pd.DataFrame({})

        self._portfolio_history["Close"] = {}
        self._portfolio_history["Return"] = {}

        position = pd.DataFrame({})

        for key in self._position_prices.keys():

            position = self._position_prices[key]

            # Reindexuje na každý den a doplní chybějící hodnoty Close
            position = position.asfreq('D')
            position["Close"] = position["Close"].ffill()

            #pp.pprint(position)

            self._portfolio_history["Close"] = self._portfolio_history["Close"].add(position["Close"], fill_value=0)

        for key in self._position_prices.keys():

            position = self._position_prices[key]
            position = position.asfreq('D')

            #pp.pprint(f"position {key}:")
            #pp.pprint(position)

            position_weight = position["Close"] / self._portfolio_history["Close"]

            #pp.pprint(f"position_weight {key}:")
            #pp.pprint(position_weight)

            position["Weighted_change"] = position["returns"] * position_weight

            pp.pprint(f"Weighted_change 25.11.2025 {key}:")
            pp.pprint(position.loc[datetime(2025,11,25),"Weighted_change"])

            self._portfolio_history["Return"] = self._portfolio_history["Return"].add(position["Weighted_change"], fill_value=0)

            pp.pprint(self._portfolio_history)

            pp.pprint(f"Weighted_change součet 25.11.2025 {key}:")
            pp.pprint(self._portfolio_history.loc[datetime(2025,11,25),"Return"])

        #self._portfolio_history["Return"] = self._portfolio_history["Return"].cumprod().shift()

        self._portfolio_history["Return"] = self._portfolio_history["Return"] + 1
        self._portfolio_history.iloc[0, self._portfolio_history.columns.get_loc("Return")] = 1
        self._portfolio_history["Growth"] = self._portfolio_history["Return"].cumprod()

        pp.pprint(f"Druhý tisk:")
        pp.pprint(self._portfolio_history)

        first_date = self._portfolio_history.iloc[0].name

        self._portfolio_history.to_csv(f'DATA/portfolio.history.csv')

        plot_price(self._portfolio_history,first_date,"Plot growth portfolia", "Growth")
        plot_price(self._portfolio_history, first_date, "Plot price portfolia", "Close")


    def _create_position_prices(self):

        self._create_currency_list()

        self._position_prices = {}

        for item in self._position_dict.keys():
            position = self.get_position(item)

            # Převod na měnu Portfolia
            prices = position.get_position_history().loc[:, "Close"]
            returns = position.get_position_history().loc[:, "Return"]
            currency = position.get_currency()

            if not (currency == self._currency):

                forex_obj = self._currency_list.get(currency)
                date = prices.index[0]
                forex_prices = forex_obj.get_prices(date).loc[:, "Close"]
                forex_prices = forex_prices.reindex(prices.index)

                prices = prices * forex_prices

            position_prices = pd.DataFrame(prices)
            position_prices.index.name = "Date"
            position_prices["returns"] = returns

            self._position_prices[item] = position_prices

    def _create_currency_list(self):

        self._currency_list = {}
        for item in self._position_dict.keys():
            position = self.get_position(item)
            currency = position.get_currency()
            if currency == self._currency:
                continue
            self._currency_list[currency] = Forex(currency + self._currency + "=X")

    def get_earliest_record_date(self) -> datetime:
        first_dates = []
        for item in self._position_dict.values():
            first_dates.append(item.get_earliest_record_date())
        print(max(first_dates))
        return max(first_dates)
        
    def get_position(self, ticker) -> Position:
        return self._position_dict[ticker]
        
    def transaction(self, amount: int, date: datetime, asset: Asset, price: float = None):
        asset = asset
        date = date.date()
        if asset.get_ticker() not in self._position_dict:
            self._position_dict[asset.get_ticker()] = Position(price, date, asset=asset,amount=amount)
        else:
            self._position_dict[asset.get_ticker()].change_position(amount=amount, date=date, price=price)


portfolio = Portfolio("EUR")

#portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2010,1,1), amount=1,price=27.7)
#portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2010,1,3), amount=100,price=27.7)
#portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2015,1,1), amount=1,price=27.7)
portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2020,1,1), amount=1,price=50.99663543701172)
portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2020,5,19), amount=1,price=48.06216812133789)
#portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2025,1,1), amount=1,price=108)
#portfolio.transaction(asset=Stock("aapl"), date=datetime(1970,12,16), amount=1,price=100)
#portfolio.transaction(asset=Stock("aapl"), date=datetime(1980,12,16), amount=1,price=0.0865)
#portfolio.transaction(asset=Stock("IE00BD3RYZ16"), date=datetime(2015,12,16), amount=1, price=100)

#print(portfolio.get_position("VUSA.AS"))
#print(portfolio)
#portfolio.get_earliest_record_date()

#gold.plot_closing_price()
#snp.plot_closing_price()
#apple.plot_closing_price()SSS

#portfolio.get_position("VUSA.AS").create_position_history()
#print(date)
#pp.pprint(portfolio.get_position("VUSA.AS")._create_transation_history(date))
#pp.pprint(portfolio.get_position("VUSA.AS").get_position_history())
#portfolio.get_position("VUSA.AS").plot_price()
#portfolio.get_position("XAUUSD").plot_price()
#pp.pprint(portfolio.get_position("AAPL").get_position_history())
#portfolio.get_position("AAPL").plot_price()

omx = ETF("IE00BD3RYZ16")
om3x = ETF("OM3X.DE")

GBPUSD_X = Forex("GBPUSD=X")

portfolio._create_position_prices()

portfolio._add_positions()


