from rich import print

from Transaction import *
from figi_api import *

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
    def new_transaction(self, transaction_type: TransactionType, date: datetime, ticker: str,currency: str = None, amount: int = None, price: float = None, venue: str = None):

        asset = asset_creator(ticker)

        if venue is not None and asset.get_venue() != venue:
            figi_code, yahoo_suf = venue_interpreter(venue)
            try:
                ticker = ticker_from_isin(ticker, figi_code) + yahoo_suf
            except: "Open figi nevyšlo."

        asset = asset_creator(ticker)

        # Odstranění času z data
        date = date.date()

        # Pokud daný asset nemá v portfoliu pozici, vytvoří novou
        if asset not in self._position_dict.keys():
            self._position_dict[asset] = Position(asset)

        self._position_dict[asset].new_transaction(amount, date, transaction_type, currency, venue, price)

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
        if real:
            self._portfolio_prices = self._portfolio_prices[self._portfolio_prices["Mask"]]
        self.plot_price(real)
        print(self._portfolio_prices)

    def save_portfolio_to_file(self):
        filename = f"Výpis portfolia {self._name}.txt"

        # --- DEFINICE ŠÍŘKY SLOUPCŮ ---
        w_name = 30
        w_qty = 8
        w_price = 12
        w_curr = 6
        w_val = 12
        w_bz = 12
        w_pl = 12
        w_chg = 10

        # Formátovací řetězce (používají f-stringy pro vložení šířek)
        header_fmt = f"| {{:<{w_name}}} | {{:>{w_qty}}} | {{:>{w_price}}} | {{:^{w_curr}}} | {{:>{w_val}}} | {{:>{w_bz}}} | {{:>{w_pl}}} | {{:>{w_chg}}} |"
        row_fmt = f"| {{:<{w_name}}} | {{:>{w_qty}.2f}} | {{:>{w_price}.2f}} | {{:^{w_curr}}} | {{:>{w_val}.2f}} | {{:>{w_bz}.2f}} | {{:>{w_pl}.2f}} | {{:>{w_chg - 1}.2f}}% |"

        # Výpočet šířky pro součtový řádek (pro zarovnání pod P/L)
        width_before_pl = w_name + w_qty + w_price + w_curr + w_val + w_bz + (5 * 3)
        total_row_fmt = f"| {{:<{width_before_pl}}} | {{:>{w_pl}.2f}} | {{:<{w_chg}}} |"

        # Oddělovací čára
        line_sep = "+" + "-" * (w_name + 2) + "+" + "-" * (w_qty + 2) + "+" + "-" * (w_price + 2) + "+" + "-" * (
                    w_curr + 2) + "+" + "-" * (w_val + 2) + "+" + "-" * (w_bz + 2) + "+" + "-" * (
                               w_pl + 2) + "+" + "-" * (w_chg + 2) + "+"

        try:
            with open(filename, "w", encoding="utf-8") as f:

                print(f"PŘEHLED PORTFOLIA: {self._name} ({self._currency})", file=f)
                print("\n", file=f)

                # --- 1. OTEVŘENÉ POZICE ---
                print("💰 OTEVŘENÉ POZICE", file=f)
                print(line_sep, file=f)
                print(header_fmt.format("PRODUKT", "POČET", "CENA/KS", "MĚNA", "HODNOTA", "BZ (AVG)", "P/L", "ZMĚNA"),
                      file=f)
                print(line_sep, file=f)

                total_profit_open = 0

                for asset, position in self._position_dict.items():
                    name, currency, price, growth, profit, invested, amount, last_price = position.get_last_value()

                    if price < 1: continue  # Filtr pro otevřené

                    total_profit_open += profit

                    # Výpočty
                    avg_cost = invested / amount if amount != 0 else 0
                    growth_percent = (growth * 100) - 100
                    display_name = (name[:w_name - 2] + '..') if len(name) > w_name else name

                    print(row_fmt.format(display_name, amount, last_price, currency, price, avg_cost, profit,
                                         growth_percent), file=f)

                # Součet otevřených
                print(line_sep, file=f)
                print(total_row_fmt.format("CELKOVÝ P/L OTEVŘENÝCH POZIC:", total_profit_open, ""), file=f)
                print(line_sep, file=f)
                print("\n\n", file=f)

                # --- 2. UZAVŘENÉ POZICE ---
                print("🔒 UZAVŘENÉ POZICE", file=f)
                print(line_sep, file=f)
                print(header_fmt.format("PRODUKT", "POČET", "CENA/KS", "MĚNA", "HODNOTA", "BZ (AVG)", "P/L", "ZMĚNA"),
                      file=f)
                print(line_sep, file=f)

                total_profit_closed = 0

                for asset, position in self._position_dict.items():
                    name, currency, price, growth, profit, invested, amount, last_price = position.get_last_value()

                    if price >= 1: continue  # Filtr pro uzavřené

                    total_profit_closed += profit

                    # --- ZMĚNA: Použijeme stejné výpočty jako nahoře ---
                    # Ošetření dělení nulou je zde důležité, pokud je u uzavřené pozice amount=0
                    avg_cost = invested / amount if amount != 0 else 0
                    growth_percent = (growth * 100) - 100
                    display_name = (name[:w_name - 2] + '..') if len(name) > w_name else name

                    # --- ZMĚNA: Použijeme stejný row_fmt namísto ručních pomlček ---
                    print(row_fmt.format(display_name, amount, last_price, currency, price, avg_cost, profit,
                                         growth_percent), file=f)

                # Součet uzavřených (volitelné, pokud ho tam chcete také)
                print(line_sep, file=f)
                print(total_row_fmt.format("CELKOVÝ REALIZOVANÝ ZISK:", total_profit_closed, ""), file=f)
                print(line_sep, file=f)

            print(f"✅ Úspěšně uloženo do souboru: {filename}")

        except Exception as e:
            print(f"❌ Chyba při ukládání souboru: {e}")

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
        self._venue = self._asset.get_venue()
    
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
    def new_transaction(self, amount: int, date: datetime,transaction_type: TransactionType, currency, venue, price: float = None):

        print(f"""
        ==================================================
            ✨ Transakce {self._asset.get_name()} ✨
        ==================================================

        🚀 Typ transakce: {transaction_type}
        📅 Datum transakce: {date}
        ℹ️ Cena: {price}
        ℹ️ Počet: {amount}
        ℹ️ Měna: {currency}
        ℹ️ Burza: {venue}
        
        ℹ️ Měna vedené akcie: {self._currency}
        
        Zpracování transakce:
        
        
        """)

        price = price
        if not (self._currency == currency) and price is not None and currency is not None:
            forex = forex_creator(from_currency=currency, to_currency=self._currency)
            rate = forex.get_rate(date)
            print(f"""
        Exchange rate z {currency} do {self._currency} dne {date} je {rate}.""")
            price = price * rate
            print(f"""
        Po převodu je vychází nákup na {price} v {self._currency}.""")

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
        print(f"""
        Nový počet vlastněného aktiva: {self._amount}
        """)
        self._prices_calculated = False
        print("""  
              
        --------------------------------------------------
          Tento blok slouží k rychlé orientaci v konzoli.
        --------------------------------------------------

        """)
    
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

    def get_last_value(self):
        filtered_prices = self._position_prices[self._position_prices["Mask"]]
        name = self._asset.get_name()
        currency = self._currency
        price = filtered_prices["Price"].iloc[-1]
        growth = filtered_prices["Growth"].iloc[-1]
        profit = filtered_prices["Profit"].iloc[-1]
        invested = filtered_prices["Base"].iloc[-1]
        amount = self._amount
        current_price = self._asset.get_prices(get_last_business_day())["Close"].iloc[-1]

        return name, currency, price, growth, profit, invested, amount, current_price
    
    # Měnový převod
    def _currency_exchange(self, currency):

        # Vytvoření Forexu
        forex = forex_creator(from_currency=self._currency, to_currency=currency)
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

        #print(self._asset.get_name())
        #print(self._position_prices)
        # Logický součin masek existence záznamu
        self._position_prices["Mask"] = self._position_prices["Mask"].combine(
            forex_prices["Mask"],
            func=lambda x, y: x & y,
            fill_value=True
        )

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
    def get_position(self, currency:str) -> pd.DataFrame:
        
        if not self._prices_calculated:
            self._create_first_date()
            self._create_position_prices()
            self._add_transactions()
        #print(f"Asset currency: {self._currency}, portfolio currency: {currency}")
        if not (self._currency == currency):
            self._currency_exchange(currency)
        self._calculate_growth()
        self._prices_calculated = True

        self._clean_position_data()

        # Zápis do souboru
        self._position_prices.to_csv(f'DATA/POSITION_PRICES/{self._asset.get_name()}.history.csv')

        return self._position_prices
