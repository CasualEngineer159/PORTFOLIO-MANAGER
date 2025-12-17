from collections import deque
from Transaction import *
from DownloadManager import get_last_business_day


# ==============================================================================
# TŘÍDA REPREZENTUJÍCÍ INVESTIČNÍ POZICI
# ==============================================================================

class Position:
    def __init__(self, asset: Asset):
        # Základní atributy aktiva
        self._asset = asset
        self._transaction_list = []
        self._currency = self._asset.get_currency()
        self._venue = self._asset.get_venue()

        # Stavové proměnné a výsledky výpočtů
        self._amount = 0
        self._realized_pnl = 0
        self._break_even_point = None
        self._prices_calculated = False

        # Dataframe a časové řady
        self._position_prices = None
        self._dates = None
        self._first_date = None
        self._forex = None

    # ==============================================================================
    # VNITŘNÍ METODY PRO VÝPOČTY (NORMALIZACE A LOGIKA)
    # ==============================================================================

    # Vypočítá realizovaný zisk a Break Even Point pomocí metody FIFO
    def _calculate_bz(self):
        # Seřazení transakcí podle data
        dated_transactions = {t.get_date(): t for t in self._transaction_list}
        sorted_transactions = sorted(dated_transactions.items(), key=lambda x: x[1].get_date())

        priced_list_fifo = deque()
        realized_profit = 0

        # Zpracování fronty transakcí
        for date, transaction in sorted_transactions:
            amount = transaction.get_amount()
            price = transaction.get_price()

            # Nákup - přidání do fronty
            if amount > 0:
                priced_list_fifo.appendleft([amount, price])
            # Prodej - odebrání z fronty (realizace zisku/ztráty)
            else:
                while amount < 0:
                    if not priced_list_fifo:
                        break
                    old_amount, old_price = priced_list_fifo.pop()
                    new_amount = old_amount + amount
                    sold_amount = old_amount - max(new_amount, 0)
                    realized_profit += sold_amount * (price - old_price)

                    if new_amount < 0:
                        amount = new_amount
                        continue
                    priced_list_fifo.append([new_amount, old_price])
                    break

        # Výpočet celkové nákupní ceny zbývajících kusů
        full_price = 0
        full_amount = 0
        for amount, price in priced_list_fifo:
            full_price += amount * price
            full_amount += amount

        # Ošetření nulového množství
        if full_amount == 0:
            self._break_even_point = 0
            return

        self._realized_pnl = realized_profit
        self._break_even_point = full_price / full_amount

    # Určí datum první transakce pro inicializaci časové řady
    def _create_first_date(self):
        # Nalezení nejstaršího data v seznamu transakcí
        first_date = self._transaction_list[0].get_date()
        for transaction in self._transaction_list:
            if transaction.get_date() < first_date:
                first_date = transaction.get_date()

        self._first_date = first_date
        self._dates = pd.date_range(start=self._first_date, end=datetime.now().date(), freq='D')

    # Inicializuje prázdný DataFrame pro ukládání cenové historie pozice
    def _create_position_prices(self):
        # Vytvoření dataframe na základě počátečního data
        self._position_prices = create_dataframe_from_date(self._first_date)

    # Kumulativně sečte hodnoty ze všech transakcí do historie pozice
    def _add_transactions(self):
        # Procházení všech transakcí a sčítání jejich vlivu na pozici
        for transaction in self._transaction_list:
            transaction_prices = transaction.get_transaction()

            # Sčítání základních finančních sloupců
            self._position_prices["Base"] = self._position_prices["Base"].add(transaction_prices["Base"], fill_value=0)
            self._position_prices["Price"] = self._position_prices["Price"].add(transaction_prices["Price"],
                                                                                fill_value=0)

            # Aktualizace masky platnosti dat (logický AND)
            self._position_prices["Mask"] = self._position_prices["Mask"].combine(
                transaction_prices["Mask"],
                func=lambda x, y: x & y,
                fill_value=True
            )

        # Výpočet průběžného zisku
        self._position_prices["Profit"] = self._position_prices["Price"] - self._position_prices["Base"]

    # Vypočítá procentuální růst pozice (Growth faktor)
    def _calculate_growth(self):
        # Poměr aktuální tržní ceny vůči nákupní základně
        self._position_prices["Growth"] = self._position_prices["Price"] / self._position_prices["Base"]

    # Provede měnovou konverzi celé historie pozice
    def _currency_exchange(self, target_currency: str):
        # Inicializace forexového převodníku
        self._forex = forex_creator(from_currency=self._currency, to_currency=target_currency)
        forex_prices = self._forex.get_prices(self._first_date)

        # Převod realizovaného zisku aktuálním kurzem
        rate = self._forex.get_rate()
        self._realized_pnl *= rate

        # Sjednocení časové řady forexu s daty pozice
        forex_prices = forex_prices.reindex(self._dates)
        forex_prices["Mask"] = forex_prices["Close"].notna()
        forex_prices["Close"] = forex_prices["Close"].ffill().bfill()

        # Přepočet nákupní základny (Base) historickými kurzy v dnech transakcí
        self._position_prices["Base"] = np.nan
        for transaction in self._transaction_list:
            date = pd.to_datetime(transaction.get_date())
            base_value = transaction.get_base()
            historical_rate = forex_prices.loc[date, "Close"]
            self._position_prices["Base"] = self._position_prices["Base"].add(base_value * historical_rate,
                                                                              fill_value=0)

        # Přepočet tržní ceny a zisku novým kurzem
        self._position_prices["Price"] = self._position_prices["Price"] * forex_prices["Close"]
        self._position_prices["Profit"] = self._position_prices["Price"] - self._position_prices["Base"]

        # Aktualizace masky o platnost dat forexu
        self._position_prices["Mask"] = self._position_prices["Mask"].combine(
            forex_prices["Mask"],
            func=lambda x, y: x & y,
            fill_value=True
        )

        self._currency = target_currency

    # Vyčistí data v případě, že je pozice uzavřena (vynulována)
    def _clean_position_data(self):
        # Identifikace řádků s nulovou hodnotou
        invalid_mask = self._position_prices['Price'].abs() < 0.0001

        # Vynulování základny a ceny pro neaktivní dny
        cols_to_zero = ['Base', 'Price']
        existing_cols_zero = [c for c in cols_to_zero if c in self._position_prices.columns]
        if existing_cols_zero:
            self._position_prices.loc[invalid_mask, existing_cols_zero] = 0

        # Zachování poslední hodnoty růstu (Growth) pro přehlednost v grafech
        cols_to_fill = ['Growth']
        existing_cols_fill = [c for c in cols_to_fill if c in self._position_prices.columns]
        if existing_cols_fill:
            self._position_prices[existing_cols_fill] = (
                self._position_prices[existing_cols_fill]
                .where(~invalid_mask)
                .ffill()
            )

    # ==============================================================================
    # VEŘEJNÉ METODY PRO PRÁCI S POZICÍ
    # ==============================================================================

    # Přidá novou transakci do pozice a zohlední případný měnový kurz
    def new_transaction(self, amount: int, date: datetime, transaction_type: TransactionType,
                        currency, venue, price: float = None):
        # Inicializace transakce
        transaction = None

        # Výběr typu transakce
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

        # Uložení transakce a aktualizace celkového množství
        self._transaction_list.append(transaction)
        self._amount += transaction.get_amount()
        self._prices_calculated = False

    # Vrátí datum první transakce v této pozici
    def get_first_date(self) -> datetime:
        self._create_first_date()
        return self._first_date

    # Vrátí aktuální přehled o stavu pozice (poslední známé hodnoty)
    def get_last_value(self):
        # Filtrace pouze platných dat
        filtered_prices = self._position_prices[self._position_prices["Mask"]]

        # Sběr dat o aktivu
        name = self._asset.get_name()
        currency = self._asset.get_currency()
        ticker = self._asset.get_ticker()

        # Sběr vypočtených hodnot z dataframe
        price = filtered_prices["Price"].iloc[-1]
        growth = filtered_prices["Growth"].iloc[-1]
        profit = filtered_prices["Profit"].iloc[-1]

        # Aktuální tržní data
        current_market_price = self._asset.get_prices(get_last_business_day())["Close"].iloc[-1]

        # Realizovaný zisk a Break Even
        realized_profit = self._realized_pnl
        if price < 1:
            realized_profit = profit

        return (name, currency, price, growth, profit, self._break_even_point,
                self._amount, current_market_price, ticker, realized_profit)

    # Provede kompletní výpočet historie pozice a vrátí DataFrame
    def get_position(self, currency: str) -> pd.DataFrame:
        # Prvotní výpočet historie, pokud ještě neproběhl
        if not self._prices_calculated:
            self._create_first_date()
            self._create_position_prices()
            self._add_transactions()

        # Výpočet FIFO statistik
        self._calculate_bz()

        # Případná měnová konverze do požadované měny
        if not (self._currency == currency):
            self._currency_exchange(currency)

        # Finalizace dat
        self._calculate_growth()
        self._prices_calculated = True
        self._clean_position_data()

        # Export do CSV pro archivaci
        file_name = self._asset.get_name()
        self._position_prices.to_csv(f'../DATA/POSITION_PRICES/{file_name}.history.csv')

        return self._position_prices