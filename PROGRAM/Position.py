from scipy.optimize import bracket

from Asset import *
from Transaction import *
from collections import deque

class Position:
    def __init__(self, asset: Asset):
        self._asset = asset
        self._transaction_list = []
        self._currency = self._asset.get_currency()
        self._prices_calculated = False
        self._amount = 0
        self._venue = self._asset.get_venue()
        self._break_even_point = None
        self._realized_pnl = 0
        self._forex = None

    def _calculate_bz(self):
        dated_transaction_list = {}
        for transaction in self._transaction_list:
            dated_transaction_list[transaction.get_date()] = transaction

        sorted_dated_transaction_list = sorted(dated_transaction_list.items(), key=lambda x: x[1].get_date())

        priced_list_fifo = deque()
        realized_profit = 0
        for date, transaction in sorted_dated_transaction_list:

            amount = transaction.get_amount()
            price = transaction.get_price()

            if amount > 0:
                priced_list_fifo.appendleft([amount, price])

            else:
                while amount < 0:
                    if not priced_list_fifo:
                        break
                    old_amount, old_price = priced_list_fifo.pop()
                    new_amount = old_amount + amount
                    sold_amount = old_amount - max(new_amount , 0)
                    realized_profit += sold_amount * (price - old_price)
                    if new_amount < 0:
                        amount = new_amount
                        continue
                    priced_list_fifo.append([new_amount, old_price])
                    break

        full_price = 0
        full_amount = 0
        for amount, price in priced_list_fifo:
            full_price += amount * price
            full_amount += amount

        if full_amount == 0:
            self._break_even_point = 0
            return

        self._realized_pnl = realized_profit
        self._break_even_point = full_price/full_amount

    # Najde datum první transakce
    def _create_first_date(self):
        date = self._transaction_list[0].get_date()
        for transaction in self._transaction_list:
            if transaction.get_date() < date:
                date = transaction.get_date()
        self._first_date = date
        self._dates = pd.date_range(start=self._first_date, end=datetime.now().date(), freq='D')

    # Vytvoří dataframe pro následné ukládání hodnot
    def _create_position_prices(self):
        self._position_prices = create_dataframe_from_date(self._first_date)

    # Vytvoření nového objektu transakce a zařazení do listu transakcí
    def new_transaction(self, amount: int, date: datetime, transaction_type: TransactionType, currency, venue,
                        price: float = None):

        price = price
        if not (self._currency == currency) and price is not None and currency is not None:
            forex = forex_creator(from_currency=currency, to_currency=self._currency)
            rate = forex.get_rate(date)
        transaction = None

        if transaction_type == TransactionType.LONG:
            transaction = LongTransaction(asset=self._asset,
                                          date=date,
                                          amount=amount,
                                          price=price,
                                          amount_owned=self._amount)

        elif transaction_type == TransactionType.FRACTION_LONG:
            transaction = LongFractionTransaction(asset=self._asset,
                                                  date=date,
                                                  amount=amount,
                                                  price=price,
                                                  amount_owned=self._amount)

        self._transaction_list.append(transaction)
        amount_bought = transaction.get_amount()
        self._amount = self._amount + amount_bought
        self._prices_calculated = False


    # Sečte Base, Profit a Price
    def _add_transactions(self):

        # Postupné sčítání všech transakcí v dané pozici
        for transaction in self._transaction_list:
            transaction_prices = transaction.get_transaction()

            # Sečtení sloupců Base, Profit a Price
            self._position_prices["Base"] = self._position_prices["Base"].add(transaction_prices["Base"], fill_value=0)
            # self._position_prices["Profit"] = self._position_prices["Profit"].add(transaction_prices["Profit"], fill_value=0)
            self._position_prices["Price"] = self._position_prices["Price"].add(transaction_prices["Price"],
                                                                                fill_value=0)

            # Logický součin masek existence záznamu
            self._position_prices["Mask"] = self._position_prices["Mask"].combine(
                transaction_prices["Mask"],
                func=lambda x, y: x & y,
                fill_value=True
            )
        self._position_prices["Profit"] = self._position_prices["Price"] - self._position_prices["Base"]

    # Výpočet výkonu pozice
    def _calculate_growth(self):
        self._position_prices["Growth"] = self._position_prices["Price"] / self._position_prices["Base"]

    def get_last_value(self):

        filtered_prices = self._position_prices[self._position_prices["Mask"]]
        name = self._asset.get_name()
        currency = self._asset.get_currency()
        price = filtered_prices["Price"].iloc[-1]
        growth = filtered_prices["Growth"].iloc[-1]

        current_price = self._asset.get_prices(get_last_business_day())["Close"].iloc[-1]
        amount = self._amount
        profit = filtered_prices["Profit"].iloc[-1]
        realized_profit = self._realized_pnl
        if price < 1:
            realized_profit = profit
        brake_point = self._break_even_point

        ticker = self._asset.get_ticker()

        return name, currency, price, growth, profit, brake_point, amount, current_price, ticker, realized_profit

    # Měnový převod
    def _currency_exchange(self, currency):

        print(f"Stock {self._asset.get_name()} in {self._currency} before exchange:")
        pp.pprint(self._position_prices)

        # Vytvoření Forexu
        self._forex = forex_creator(from_currency=self._currency, to_currency=currency)
        forex_prices = self._forex.get_prices(self._first_date)

        # Převedení realized profitu
        rate = self._forex.get_rate()
        self._realized_pnl *= rate

        # Přeindexování na potřebný rozsah a vytvoření masky
        forex_prices = forex_prices.reindex(self._dates)
        forex_prices["Mask"] = forex_prices["Close"].notna()

        # Doplnění chybějících hodnot forex exchange forward i backward fill
        forex_prices["Close"] = forex_prices["Close"].ffill().bfill()

        # Vytvoření sloupce pro násobení Base
        self._position_prices["Base"] = np.nan
        for transaction in self._transaction_list:
            date = transaction.get_date()
            date = pd.to_datetime(date)
            base = transaction.get_base()
            rate = forex_prices.loc[date, "Close"]
            self._position_prices["Base"] = self._position_prices["Base"].add(base*rate, fill_value=0)

        # Přenásobení cen měnovým kurzem
        self._position_prices["Price"] = self._position_prices["Price"] * forex_prices["Close"]
        self._position_prices["Profit"] = self._position_prices["Price"] - self._position_prices["Base"]

        # Logický součin masek existence záznamu
        self._position_prices["Mask"] = self._position_prices["Mask"].combine(
            forex_prices["Mask"],
            func=lambda x, y: x & y,
            fill_value=True
        )
        print(" ")
        print(f"Stock {self._asset.get_name()} in {currency} after exchange:")
        pp.pprint(self._position_prices)

        self._currency = currency

    # Vrátí datum první transakce
    def get_first_date(self) -> datetime:
        self._create_first_date()
        return self._first_date

    # Pokud byla pozice prodána, upravíme data od toho momentu
    def _clean_position_data(self):

        # 1. Vytvoření masky pro "nulové" řádky (kde je cena prakticky nula)
        # True = řádek, který chceme upravit (nulovat nebo fillovat)
        invalid_mask = self._position_prices['Price'].abs() < 0.0001

        # 2. Nastavení 'Base' a 'Price' na 0 tam, kde platí maska (neplatné řádky)
        # Používáme .loc pro bezpečný zápis do dataframe
        cols_to_zero = ['Base', 'Price']
        # Pro jistotu ověříme, zda sloupce existují, aby kód nepadal
        existing_cols_zero = [c for c in cols_to_zero if c in self._position_prices.columns]

        if existing_cols_zero:
            self._position_prices.loc[invalid_mask, existing_cols_zero] = 0

        # 3. Forward fill (doplnění) pro 'Profit' a 'Growth'
        # .where(~invalid_mask) -> Ponechá hodnoty tam, kde je řádek PLATNÝ (negace masky).
        # Ostatní (kde je invalid_mask True) nahradí NaN, které následně .ffill() vyplní.
        cols_to_fill = ['Growth']
        existing_cols_fill = [c for c in cols_to_fill if c in self._position_prices.columns]

        if existing_cols_fill:
            self._position_prices[existing_cols_fill] = (
                self._position_prices[existing_cols_fill]
                .where(~invalid_mask)  # Ponechat platné, zbytek NaN
                .ffill()  # NaN doplnit předchozí hodnotou
            )

    # Vrátí historii pozice
    def get_position(self, currency: str) -> pd.DataFrame:

        if not self._prices_calculated:
            self._create_first_date()
            self._create_position_prices()
            self._add_transactions()

        self._calculate_bz()

        if not (self._currency == currency):
            self._currency_exchange(currency)
        self._calculate_growth()
        self._prices_calculated = True

        self._clean_position_data()

        # Zápis do souboru
        self._position_prices.to_csv(f'../DATA/POSITION_PRICES/{self._asset.get_name()}.history.csv')

        return self._position_prices