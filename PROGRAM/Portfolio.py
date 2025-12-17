import os

from Transaction import *
from figi_api import *
from fpdf import FPDF
from Position import *

class Portfolio:

    def __init__(self, name: str, currency: str):
        self._name = name
        self._currency = currency
        self._position_dict = {}
        self._portfolio_prices = pd.DataFrame()

    def get_position(self, ticker: str):
        asset = asset_creator(ticker)
        return self._position_dict[asset]
        
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
        col_widths = [80, 20, 20, 25, 25, 25, 25, 25, 25]
        headers = ["PRODUKT","TICKER","KS","CENA","BZ", "HODNOTA","UNREAL. P/L","ZMĚNA","CELKEM P/L"]

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
            name, currency, price, growth, profit, brake_even, amount, last_price, ticker, realized_profit = position.get_last_value()

            if price < 1: continue  # Filtr pro otevřené
            unrealized_profit = profit - realized_profit
            total_profit_open += unrealized_profit

            # Výpočty
            growth_pct = (unrealized_profit + price) / price * 100

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
                f"{amount:.2f}",
                f"{last_price:.2f} " + currency,
                f"{brake_even:.2f} " + currency,
                f"{price:.2f} " + self._currency,
                f"{unrealized_profit:.2f} " + self._currency,
                f"{growth_pct:.2f}% ",
                f"{profit:.2f} " + self._currency
            ]

            # Vykreslení buněk
            for i, data in enumerate(row_data):
                # Zarovnání: První sloupec (název) vlevo, zbytek vpravo
                align = 'L' if i == 0 else 'R'
                pdf.cell(col_widths[i], 7, str(data), border=1, align=align)
            pdf.ln()

        # Součet otevřených
        pdf.set_font(style='B')
        pdf.cell(sum(col_widths[:-3]), 8, "CELKEM OTEVŘENÉ POZICE:", border=1, align='L')
        pdf.cell(col_widths[-3], 8, f"{total_profit_open:.2f}", border=1, align='R')
        pdf.cell(col_widths[-2], 8, "", border=1)  # Prázdná buňka na konci
        pdf.cell(col_widths[-1], 8, "", border=1)  # Prázdná buňka na konci

        pdf.ln(15)  # Větší mezera mezi sekcemi

        # --- 2. UZAVŘENÉ POZICE ---
        pdf.set_font(size=12, style='B')
        pdf.cell(0, 10, "UZAVŘENÉ POZICE", ln=True)
        pdf.set_font(size=10)

        print_table_header()

        total_profit_closed = 0

        for asset, position in self._position_dict.items():
            name, currency, price, growth, profit, brake_even, amount, last_price, ticker, realized_profit = position.get_last_value()

            if price >= 1: continue  # Filtr pro uzavřené
            total_profit_closed += realized_profit

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
                f"{amount:.2f}",
                f"{last_price:.2f} " + currency,
                f"{brake_even:.2f} " + currency,
                f"{price:.2f} " + self._currency,
                f"{0:.2f} " + self._currency,
                f" - ",
                f"{realized_profit:.2f} " + self._currency
            ]


            for i, data in enumerate(row_data):
                align = 'L' if i == 0 else 'R'
                pdf.cell(col_widths[i], 7, str(data), border=1, align=align)
            pdf.ln()

        # Součet uzavřených
        pdf.set_font(style='B')
        pdf.cell(sum(col_widths[:-1]), 8, "CELKEM REALIZOVANÝ ZISK:", border=1, align='L')
        pdf.cell(col_widths[-1], 8, f"{total_profit_closed:.2f}", border=1, align='R')

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
