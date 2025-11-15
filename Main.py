from Asset import *

snp = ETF("VUSA.AS")
apple = Stock("US67066G1040")
bitcoin = Crypto("BTC-USD")
gold = Commodity("XAUUSD")
gold_futures = Futures("GC=F")

class Position:
    
    def __init__(self, price=float, date=datetime, asset=Asset, amount=int):
        self._ticker = asset.get_ticker()
        self._amount = amount
        self._name = asset.get_name()
        self._position_changes = {}
        self._position_changes[date] = [amount, price]
        
    def print_overview(self):
        print(f"Number of {self._name} owned is {self._amount}.")
        
    def __str__(self):
        print(f"Number of {self._name} owned is {self._amount}. Transactions:")
        pp.pprint(self._position_changes)
        return ""

    def change_position(self, amount=int, date=datetime, price=float):
        # Handle pokud jsou dvě transakce za jeden den. Sečte se počet kusů a zprůměruje cena
        print("Měníme pozici")
        if date in self._position_changes:
            new_amount = self._position_changes[date][0] + amount
            new_price = (self._position_changes[date][1] * self._position_changes[date][0] + amount * price) / new_amount
            self._amount = new_amount
            self._position_changes[date] = [new_amount, new_price]
        else:
            self._position_changes[date] = [amount, price]
            self._amount = self._amount + amount

class Portfolio:
    def __init__(self):
        self._position_dict = {}
        
    def __str__(self):
        for item in self._position_dict.values():
            item.print_overview()
        return ""
        
    def get_position(self, ticker) -> Position:
        return self._position_dict[ticker]
        
    def transaction(self, price = float, amount = int, date = datetime, asset=Asset):
        date = date.date()
        if asset.get_ticker() not in self._position_dict:
            self._position_dict[asset.get_ticker()] = Position(price, date, asset=asset,amount=amount)
        else:
            self._position_dict[asset.get_ticker()].change_position(amount=amount, date=date, price=price)


portfolio = Portfolio()
portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2021,8,13), amount=3,price=67.2021255493164)
portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2021,8,14), amount=-3,price=67.2021255493164)
portfolio.transaction(asset=ETF("VUSA.AS"), date=datetime(2021,8,13), amount=15,price=200)
portfolio.transaction(asset=Stock("aapl"), date=datetime(2024,8,13), amount=4,price=600)
portfolio.transaction(asset=Commodity("XPTUSD"), date=datetime(2010,8,14), amount=7,price=1050)
print(portfolio.get_position("VUSA.AS"))
print(portfolio)