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
        
    def _create_transation_history(self, date):
        
        amount = self._position_changes[date][0]
        price = self._position_changes[date][1]
        
        closing_price = self._daily_history.loc[date, "Close"]
        
        intraday_change = (closing_price - price) / price
        
        multipliers = 1 + self._daily_history.loc[date:, "return"]
        multipliers.iloc[0] = intraday_change + 1
        
        cum_multipliers = multipliers.cumprod().shift()
        cum_multipliers = cum_multipliers.fillna(1.0)
        
        prices = price * amount * cum_multipliers
        
        pp.pprint(multipliers)
        pp.pprint(cum_multipliers)
        pp.pprint(prices)
        
    def create_position_history(self):
        
        multipliers = 1 + self._daily_history["return"]
        multipliers = multipliers.fillna(1.0)
        
        cum_multipliers = multipliers.cumprod().shift()
        
        pp.pprint(multipliers)
        pp.pprint(cum_multipliers)
        
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

        # Handle pokud jsou dvě transakce za jeden den. Sečte se počet kusů a zprůměruje cena
        self._get_history(date)
        if self.get_earliest_record_date() < date:
            low = self._daily_history.loc[date, "Low"]
            high = self._daily_history.loc[date, "High"]
            #print(f"low: {low}, price: {price}, high: {high}")
            if not low <= price <= high:
                print(f"[red]!!! Cena {self._name} mimo denní rozsah!!![/red] platný rozsah: low: {low}, price: {price}, high: {high}")
        else:
            print(f"[red]!!!Pozor, v datu {date.date()} transakce {self._name} ještě není záznam cen!!![/red] první datum záznamu: {self.get_earliest_record_date().date()}")

        if date in self._position_changes:
            new_amount = self._position_changes[date][0] + amount
            new_price = (self._position_changes[date][1] * self._position_changes[date][0] + amount * price) / new_amount
            self._amount = max(0, new_amount)
            self._position_changes[date] = [new_amount, new_price]
        else:
            self._position_changes[date] = [max(0, amount), price]
            self._amount = max(0, amount)

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
portfolio.get_position("VUSA.AS")._create_transation_history(date)