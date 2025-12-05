import os

from Transaction import *
from figi_api import *
from fpdf import FPDF

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
            if figi_code is not None:
                try:
                    ticker = ticker_from_isin(ticker, figi_code) + yahoo_suf
                except Exception as e:
                    print(f"Figi blbne chyba: {e}")

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

    def export_portfolio_to_pdf(self):
        filename = f"../DATA/PERSONAL/Portfolio_Report_{self._name}.pdf"

        # ... inicializace pdf ...
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()

        # --- OPRAVA FONTŮ (Načtení Normální i Tučné verze) ---
        font_path_regular = 'C:/Windows/Fonts/arial.ttf'
        font_path_bold = 'C:/Windows/Fonts/arialbd.ttf'  # Cesta k tučnému fontu

        try:
            if os.path.exists(font_path_regular) and os.path.exists(font_path_bold):
                # 1. Načteme normální Arial
                pdf.add_font('Arial', '', font_path_regular)

                # 2. Načteme tučný Arial (style='B')
                pdf.add_font('Arial', 'B', font_path_bold)

                # Nastavíme výchozí
                pdf.set_font("Arial", size=10)
                print("✅ Fonty Arial (Regular i Bold) úspěšně načteny.")
            else:
                print("⚠️ Pozor: Soubory fontu Arial nebyly nalezeny v C:/Windows/Fonts/")
                # Fallback (čeština nepůjde)
                pdf.set_font("Helvetica", size=10)

        except Exception as e:
            print(f"⚠️ Chyba při načítání fontů: {e}")
            pdf.set_font("Helvetica", size=10)

        # --- HLAVIČKA DOKUMENTU ---
        # Nyní už můžeme bezpečně použít style='B', protože jsme ho nahoře definovali
        pdf.set_font("Arial", size=16, style='B')
        pdf.cell(0, 10, txt=f"PŘEHLED PORTFOLIA: {self._name}", ln=True, align='C')
        pdf.set_font(size=10)
        pdf.ln(5)  # Odřádkování

        # Definice šířky sloupců (celkem cca 275 mm pro A4 landscape)
        # Pořadí: Produkt, Počet, Cena, Měna, Hodnota, BZ, P/L, Změna
        col_widths = [80, 20, 20, 30, 30, 30, 30, 30]
        headers = ["PRODUKT","TICKER","KS","CENA","BZ", "HODNOTA","P/L","ZMĚNA"]

        # Funkce pro vykreslení hlavičky tabulky
        def print_table_header():
            pdf.set_font(style='B')
            pdf.set_fill_color(200, 220, 255)  # Světle modrá
            for i, h in enumerate(headers):
                pdf.cell(col_widths[i], 8, h, border=1, align='C', fill=True)
            pdf.ln()
            pdf.set_font(style='')  # Zrušit tučné

        # --- 1. OTEVŘENÉ POZICE ---
        pdf.set_font(size=12, style='B')
        pdf.cell(0, 10, "OTEVŘENÉ POZICE", ln=True)
        pdf.set_font(size=10)

        print_table_header()

        total_profit_open = 0

        # Iterace daty
        for asset, position in self._position_dict.items():
            name, currency, price, growth, profit, brake_even, amount, last_price, ticker = position.get_last_value()

            if price < 1: continue  # Filtr pro otevřené

            total_profit_open += profit

            # Výpočty
            growth_pct = (growth * 100) - 100

            # Zjistíme aktuální šířku názvu
            current_width = pdf.get_string_width(name)

            display_name = name

            # NOVÁ LOGIKA ZALOŽENÁ NA ŠÍŘCE
            if current_width > 80:
                # Zde už nemůžeme použít jednoduché zkrácení pomocí indexu [:-3],
                # musíme iterovat a zkracovat, dokud se šířka nevejde

                while pdf.get_string_width(display_name + '...') > 79 and len(display_name) > 3:
                    display_name = display_name[:-1]  # Odstraňujeme poslední znak

                display_name += '...'

            # Data řádku
            row_data = [
                display_name,
                ticker,
                f"{amount}",
                f"{last_price:.2f} " + currency,
                f"{brake_even:.2f} " + currency,
                f"{price:.2f} " + self._currency,
                f"{profit:.2f} " + self._currency,
                f"{growth_pct:.2f}% "
            ]

            # Vykreslení buněk
            for i, data in enumerate(row_data):
                # Zarovnání: První sloupec (název) vlevo, zbytek vpravo
                align = 'L' if i == 0 else 'R'
                pdf.cell(col_widths[i], 7, str(data), border=1, align=align)
            pdf.ln()

        # Součet otevřených
        pdf.set_font(style='B')
        pdf.cell(sum(col_widths[:-2]), 8, "CELKEM OTEVŘENÉ POZICE:", border=1, align='L')
        pdf.cell(col_widths[-2], 8, f"{total_profit_open:.2f}", border=1, align='R')
        pdf.cell(col_widths[-1], 8, "", border=1)  # Prázdná buňka na konci
        pdf.ln(15)  # Větší mezera mezi sekcemi

        # --- 2. UZAVŘENÉ POZICE ---
        pdf.set_font(size=12, style='B')
        pdf.cell(0, 10, "UZAVŘENÉ POZICE", ln=True)
        pdf.set_font(size=10)

        print_table_header()

        total_profit_closed = 0

        for asset, position in self._position_dict.items():
            name, currency, price, growth, profit, brake_even, amount, last_price, ticker = position.get_last_value()

            if price >= 1: continue  # Filtr pro uzavřené

            total_profit_closed += profit

            growth_pct = (growth * 100) - 100

            # Zjistíme aktuální šířku názvu
            current_width = pdf.get_string_width(name)

            display_name = name

            # NOVÁ LOGIKA ZALOŽENÁ NA ŠÍŘCE
            if current_width > 80:
                # Zde už nemůžeme použít jednoduché zkrácení pomocí indexu [:-3],
                # musíme iterovat a zkracovat, dokud se šířka nevejde

                while pdf.get_string_width(display_name + '...') > 79 and len(display_name) > 3:
                    display_name = display_name[:-1]  # Odstraňujeme poslední znak

                display_name += '...'

            # Data řádku
            row_data = [
                display_name,
                ticker,
                f"{amount}",
                f"{last_price:.2f} " + currency,
                f"{brake_even:.2f} " + currency,
                f"{price:.2f} " + self._currency,
                f"{profit:.2f} " + self._currency,
                f"{growth_pct:.2f}% "
            ]

            for i, data in enumerate(row_data):
                align = 'L' if i == 0 else 'R'
                pdf.cell(col_widths[i], 7, str(data), border=1, align=align)
            pdf.ln()

        # Součet uzavřených
        pdf.set_font(style='B')
        pdf.cell(sum(col_widths[:-2]), 8, "CELKEM REALIZOVANÝ ZISK:", border=1, align='L')
        pdf.cell(col_widths[-2], 8, f"{total_profit_closed:.2f}", border=1, align='R')
        pdf.cell(col_widths[-1], 8, "", border=1)

        # --- ULOŽENÍ ---
        try:
            pdf.output(filename)
            abs_path = os.path.abspath(filename)
            print(f"✅ PDF úspěšně vytvořeno: {abs_path}")
            os.startfile(abs_path)
        except Exception as e:
            print(f"❌ Chyba při ukládání PDF (máš ho otevřené?): {e}")

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
        self._break_even_point = None
    
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
            #self._position_prices["Profit"] = self._position_prices["Profit"].add(transaction_prices["Profit"], fill_value=0)
            self._position_prices["Price"] = self._position_prices["Price"].add(transaction_prices["Price"], fill_value=0)
            
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
        profit = filtered_prices["Profit"].iloc[-1]
        brake_point = self._break_even_point
        amount = self._amount
        current_price = self._asset.get_prices(get_last_business_day())["Close"].iloc[-1]
        ticker = self._asset.get_ticker()

        return name, currency, price, growth, profit, brake_point, amount, current_price, ticker
    
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

        self._clean_position_data()

        if not self._amount == 0:
            self._break_even_point = self._position_prices["Base"].iloc[-1] / self._amount
        else:
            self._break_even_point = 0

        if not (self._currency == currency):
            self._currency_exchange(currency)
        pp.pprint(self._position_prices)
        self._calculate_growth()
        self._prices_calculated = True

        pp.pprint(self._position_prices)

        # Zápis do souboru
        self._position_prices.to_csv(f'../DATA/POSITION_PRICES/{self._asset.get_name()}.history.csv')

        return self._position_prices
