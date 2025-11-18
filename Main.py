from Asset import *
from rich import print

snp = ETF("VUSA.AS")
apple = Stock("US67066G1040")
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
        
    # Doplnění dat
    def _fill_history_data(self):
        
        
        keys = self._position_changes.keys()
        first_date = min(keys)
        print(first_date)
        
        # Vytvoření úplné datové řady pro danou hystorii
        full_date_range = pd.date_range(
            start=first_date,
            end=get_last_business_day(),
            freq='D'  # Frekvence 'D' znamená denní
        )
        full_date_range.name = 'Date'
        
        self._daily_history = self._daily_history.reindex(full_date_range)

    
    # Vrátí data růstu z dané transakce
    def _create_transation_history(self, date) -> pd.Series:
        
        # Získání informací o pozici
        amount = self._position_changes[date][0]
        price = self._position_changes[date][1]
        
        # Výpočet procentuálního rozdílu nákupní ceny od poslední obchodované toho dne
        closing_price = self._daily_history.loc[date, "Close"]
        intraday_change = (closing_price - price) / price
        
        # Převedení daily_change na procenta
        multipliers = 1 + self._daily_history.loc[date:, "return"]
        multipliers.iloc[0] = intraday_change + 1
        
        # Výpočet kumulativního nárůstu na jednotku
        cum_multipliers = multipliers.cumprod().shift()
        cum_multipliers = cum_multipliers.fillna(1.0)
        
        # Růstu pozice
        prices = price * amount * cum_multipliers
        
        # Vrátí data růstu z dané transakce
        return prices
        
    def get_position_history(self):
        
        growth_list = []
        
        for date in self._position_changes.keys():
            
            transaction_df = self._create_transation_history(date)
            growth_list.append(transaction_df)
            
        if not growth_list:
            
            return pd.DataFrame()

        position_history = growth_list[0]    

        for i in range(1, len(growth_list)):

            position_history = position_history.add(growth_list[i], fill_value=0)
            
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
            low = self._daily_history.loc[date, "Low"]
            high = self._daily_history.loc[date, "High"]
            if not low <= price <= high:
                print(f"[red]!!! Cena {self._name} mimo denní rozsah!!![/red] platný rozsah: low: {low}, price: {price}, high: {high}")
        else:
            
            print(f"[red]!!!Pozor, v datu {date.date()} transakce {self._name} ještě není záznam cen!!![/red] první datum záznamu: {self.get_earliest_record_date().date()}")

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
        
        if asset.get_ticker() not in self._position_dict:
            self._position_dict[asset.get_ticker()] = Position(price, date, asset=asset,amount=amount)
        else:
            self._position_dict[asset.get_ticker()].change_position(amount=amount, date=date, price=price)


portfolio = Portfolio()

date = datetime(2022,8,14)

portfolio.transaction(asset=ETF("VUSA.AS"), date=date, amount=3,price=70)
portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2010,8,13), amount=15,price=200)
portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2021,8,13), amount=-60,price=67.2021255493164)
portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2022,8,13), amount=5,price=67.2021255493164)
portfolio.transaction(asset=Stock("aapl"), date=datetime(2024,8,13), amount=4,price=600)
portfolio.transaction(asset=Commodity("XPTUSD"), date=datetime(2024,8,13), amount=4,price=600)
portfolio.transaction(asset=Commodity("XPLUSD"), date=datetime(2024,8,13), amount=4,price=600)

#print(portfolio.get_position("VUSA.AS"))
#print(portfolio)
#portfolio.get_earliest_record_date()

#gold.plot_closing_price()
#snp.plot_closing_price()
#apple.plot_closing_price()

#portfolio.get_position("VUSA.AS").create_position_history()
#print(date)
#pp.pprint(portfolio.get_position("VUSA.AS")._create_transation_history(date))
pp.pprint(portfolio.get_position("VUSA.AS").get_position_history())
