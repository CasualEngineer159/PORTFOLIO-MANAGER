from Asset import *
from rich import print

snp = ETF("VUSA.AS")
apple = Stock("US67066G1040")
Apple = Stock("aapl")
bitcoin = Crypto("BTC-USD")
gold = Commodity("XAUUSD")
gold_futures = Futures("GC=F")

class Position:
    
    def __init__(self, price: float, date: datetime, asset: Asset, amount: int):
        self._asset = asset
        self._ticker = asset.get_ticker()
        self._amount = amount
        self._name = asset.get_name()
        self._position_changes = {}
        self._daily_history = None
        self.change_position(amount=amount, date=date, price=price)

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

        # Převedení daily_change na procenta
        new_index = daily_history_copy.index.union([date])
        re_indexed_series = daily_history_copy['return'].reindex(new_index, method='bfill')
        multipliers = 1 + re_indexed_series.loc[date:].copy(deep=True)
        multipliers.iloc[0] = intraday_change + 1

        if date < self._asset.get_earliest_record_date():
            multipliers.iloc[1] = 1

        #pp.pprint(multipliers)

        # Výpočet kumulativního nárůstu na jednotku
        cum_multipliers = multipliers.cumprod().shift()
        cum_multipliers = cum_multipliers.fillna(1.0)
        
        # Výpočet celkového růstu pozice
        prices = price * amount * cum_multipliers

        # Převod na dataframe
        prices = prices.to_frame(name="Close")

        # Vrátí data růstu z dané transakce jako dataframe
        return prices

    def plot_price(self):
        plot_price(self.get_position_history(), self._get_first_buy_date(), f"{self._name} position price growth graph")

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

        position_history.to_csv(f'DATA/{self._ticker}.position.history.csv')
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
        if (self._daily_history is None) or (self._daily_history.index.min().date() > date.date()):
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
            nearest_row = self._daily_history.asof(date).name
            low = self._daily_history.loc[nearest_row, "Low"]
            high = self._daily_history.loc[nearest_row, "High"]
            if not low <= price <= high:
                print(f"[red]!!! Cena {self._name} mimo denní rozsah!!![/red] platný rozsah: low: {low}, price: {price}, high: {high}")
        else:
            
            print(f"[red]!!!Pozor, v datu {date} transakce {self._name} ještě není záznam cen!!![/red] první datum záznamu: {self.get_earliest_record_date()}")

            # Reindexovat záznam do posledního nejzazšího potřebného data (hodnoty budou NaN)
            self._fill_history_data()


class Portfolio:
    def __init__(self):
        self._position_dict = {}
        
    def __str__(self):
        for item in self._position_dict.values():
            item.print_overview()
        return ""

    def get_earliest_record_date(self) -> datetime:
        first_dates = []
        for item in self._position_dict.values():
            first_dates.append(item.get_earliest_record_date())
        print(max(first_dates).date())
        return max(first_dates).date()
        
    def get_position(self, ticker) -> Position:
        return self._position_dict[ticker]
        
    def transaction(self, price: float, amount: int, date: datetime, asset: Asset):
        asset = asset
        date = date.date()
        if asset.get_ticker() not in self._position_dict:
            self._position_dict[asset.get_ticker()] = Position(price, date, asset=asset,amount=amount)
        else:
            self._position_dict[asset.get_ticker()].change_position(amount=amount, date=date, price=price)


portfolio = Portfolio()

#portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2010,1,1), amount=1,price=100)
#portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2015,1,1), amount=1,price=100)
portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2020,1,1), amount=1,price=51)
#portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2025,1,1), amount=1,price=100)
portfolio.transaction(asset=Stock("aapl"), date=datetime(1970,12,16), amount=1,price=100)
#portfolio.transaction(asset=Stock("aapl"), date=datetime(1980,12,16), amount=1,price=0.08641161024570465)
#portfolio.transaction(asset=Commodity("XPTUSD"), date=datetime(2024,8,13), amount=4,price=600)
#portfolio.transaction(asset=Commodity("XPLUSD"), date=datetime(2024,8,13), amount=4,price=600)
portfolio.transaction(asset=Commodity("XAUUSD"), date=datetime(2015,12,16), amount=1,price=100)

#print(portfolio.get_position("VUSA.AS"))
#print(portfolio)
#portfolio.get_earliest_record_date()

#gold.plot_closing_price()
#snp.plot_closing_price()
#apple.plot_closing_price()

#portfolio.get_position("VUSA.AS").create_position_history()
#print(date)
#pp.pprint(portfolio.get_position("VUSA.AS")._create_transation_history(date))
#pp.pprint(portfolio.get_position("VUSA.AS").get_position_history())
portfolio.get_position("VUSA.AS").plot_price()
portfolio.get_position("XAUUSD").plot_price()
#pp.pprint(portfolio.get_position("AAPL").get_position_history())
portfolio.get_position("AAPL").plot_price()

