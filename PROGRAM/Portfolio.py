from fpdf import FPDF
from FigiApi import *
from Position import *


# ==============================================================================
# TŘÍDA PORTFOLIO - SPRÁVA KOLEKCE INVESTIČNÍCH POZIC
# ==============================================================================

class Portfolio:

    def __init__(self, name: str, currency: str):
        # Inicializace základních parametrů portfolia
        self._name = name
        self._currency = currency
        self._position_dict = {}
        self._portfolio_prices = pd.DataFrame()
        self._first_date = None

    # Změní výchozí měnu portfolia pro výpočty
    def change_currency(self, currency: str):
        self._currency = currency

    # Vrátí konkrétní objekt pozice podle tickeru
    def get_position(self, ticker: str):
        # Vytvoření pomocného objektu assetu pro klíč
        asset = asset_creator(ticker)

        # Vrátí nalezenou pozici ze slovníku
        return self._position_dict[asset]

    # ==============================================================================
    # SPRÁVA TRANSAKCÍ
    # ==============================================================================

    # Zpracuje novou transakci a přiřadí ji ke správné pozici
    def new_transaction(self, transaction_type: TransactionType, date: datetime, ticker: str,
                        currency: str = None, amount: int = None, price: float = None, venue: str = None):

        # Prvotní vytvoření assetu pro kontrolu burzy
        current_asset = asset_creator(ticker)

        # Kontrola, zda sedí burza (případné přemapování přes OpenFIGI)
        if venue is not None and current_asset.get_venue() != venue:
            figi_code, yahoo_suffix = venue_interpreter(venue)

            if figi_code is not None:
                try:
                    # Získání nového tickeru z API a přidání suffixu
                    ticker = ticker_from_isin(ticker, figi_code) + yahoo_suffix
                except Exception as e:
                    print(f"Chyba při mapování FIGI: {e}")

        # Finální vytvoření assetu po validaci tickeru
        final_asset = asset_creator(ticker)
        transaction_date = date.date()

        # Pokud pozice pro tento asset neexistuje, vytvoříme ji
        if final_asset not in self._position_dict:
            self._position_dict[final_asset] = Position(final_asset)

        # Přidání transakce do příslušné pozice
        self._position_dict[final_asset].new_transaction(amount, transaction_date, transaction_type, currency, venue,
                                                         price)

    # ==============================================================================
    # VNITŘNÍ VÝPOČETNÍ METODY
    # ==============================================================================

    # Identifikuje nejstarší datum transakce napříč všemi pozicemi
    def _create_first_date(self):
        # Inicializace datem první nalezené pozice
        _, first_position = next(iter(self._position_dict.items()))
        earliest_date = first_position.get_first_date()

        # Porovnání se všemi ostatními pozicemi
        for _, position in self._position_dict.items():
            if position.get_first_date() < earliest_date:
                earliest_date = position.get_first_date()

        # Uložení nejstaršího data do vlastnosti objektu
        self._first_date = earliest_date

    # Inicializuje prázdný DataFrame pro ukládání časových řad portfolia
    def _create_portfolio_prices(self):
        # Vytvoření dataframe od prvního záznamu (využívá globální funkci)
        self._portfolio_prices = create_dataframe_from_date(self._first_date)

    # Přidá do historie nultý záznam (den před první transakcí) pro grafy
    def _add_record_zero(self):
        # Výpočet data před zahájením investování
        zero_date = self._first_date - pd.Timedelta(days=1)
        self._portfolio_prices.index = self._portfolio_prices.index.date

        # Nastavení výchozích nulových hodnot
        self._portfolio_prices.loc[zero_date, "Mask"] = True
        self._portfolio_prices.loc[zero_date, "Base"] = 0
        self._portfolio_prices.loc[zero_date, "Growth"] = 1
        self._portfolio_prices.loc[zero_date, "Price"] = 0
        self._portfolio_prices.loc[zero_date, "Profit"] = 0

        # Seřazení historie tak, aby nula byla na začátku
        self._portfolio_prices.sort_index(inplace=True)
        self._first_date = zero_date

    # Agreguje data ze všech pozic do celkových hodnot portfolia
    def _add_positions(self):
        for _, position in self._position_dict.items():
            # Získání časové řady pozice v měně portfolia
            pos_data = position.get_position(self._currency)

            # Kumulativní součet klíčových finančních sloupců
            self._portfolio_prices["Base"] = self._portfolio_prices["Base"].add(pos_data["Base"], fill_value=0)
            self._portfolio_prices["Profit"] = self._portfolio_prices["Profit"].add(pos_data["Profit"], fill_value=0)
            self._portfolio_prices["Price"] = self._portfolio_prices["Price"].add(pos_data["Price"], fill_value=0)

            # Logické spojení masek platnosti dat
            self._portfolio_prices["Mask"] = self._portfolio_prices["Mask"].combine(
                pos_data["Mask"],
                func=lambda x, y: x & y,
                fill_value=True
            )

    # Vypočítá index růstu (relativní výkonnost) celého portfolia
    def _calculate_growth(self):
        # Výpočet poměru aktuální ceny vůči investované bázi
        self._portfolio_prices["Growth"] = self._portfolio_prices["Price"] / self._portfolio_prices["Base"]

    # Vypočítá a vrátí výkon portfoli pa
    def get_performance_pa(self) -> float:
        # 1. Získání celkového růstu z historie (např. 1.15 pro +15 %)
        total_growth = self._portfolio_prices["Growth"].iloc[-1]

        # 2. Výpočet počtu dní mezi první transakcí a dneškem
        total_days = (datetime.now().date() - self._first_date).days

        # Ošetření, aby nedošlo k dělení nulou u nových portfolií
        if total_days <= 0:
            return 0.0

        # 3. Přepočet dní na roky
        years = total_days / 365.25

        # 4. Výpočet CAGR (výkon p.a.)
        performance_pa = (total_growth ** (1 / years)) - 1

        return performance_pa

    # ==============================================================================
    # VEŘEJNÉ VÝSTUPY (GRAFY, REPORTY)
    # ==============================================================================

    # Kompletně přepočítá historii portfolia a vygeneruje grafy
    def evaluate_portfolio(self):

        # Ukončení pokud je portfolio prázdné
        if not self._position_dict:
            print("V portfoliu ještě neexistují žádné záznamy")
            return

        # Sekvenční provedení všech výpočetních kroků
        self._create_first_date()
        self._create_portfolio_prices()
        self._add_positions()
        self._calculate_growth()
        self._add_record_zero()

        # Generování PNG souborů
        self.plot_price()

        # Export výpisu portfolia do PDF
        self.export_portfolio_to_pdf()

    # Vygeneruje sadu grafů v čase pro různé metriky
    def plot_price(self):
        # Volání externí funkce pro vykreslení růstu, ceny, profitu a báze
        plot_price(self._portfolio_prices, self._first_date, f"Portfolio {self._name} graf růstu {self._currency}",
                   "Growth")
        plot_price(self._portfolio_prices, self._first_date, f"Portfolio {self._name} graf ceny {self._currency}",
                   "Price")
        plot_price(self._portfolio_prices, self._first_date, f"Portfolio {self._name} graf profitu {self._currency}",
                   "Profit")
        plot_price(self._portfolio_prices, self._first_date, f"Portfolio {self._name} graf báze {self._currency}",
                   "Base")

    # Exportuje detailní PDF report se stavem pozic, grafy a výkonem p.a.
    def export_portfolio_to_pdf(self):
        # Definice cesty pro uložení výsledného PDF
        report_path = f"../DATA/PERSONAL/Portfolio_Report_{self._name}.pdf"
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()

        # --- NASTAVENÍ PÍSMA (Podpora češtiny) ---
        font_reg = 'C:/Windows/Fonts/arial.ttf'
        font_bold = 'C:/Windows/Fonts/arialbd.ttf'

        try:
            if os.path.exists(font_reg) and os.path.exists(font_bold):
                pdf.add_font('Arial', '', font_reg)
                pdf.add_font('Arial', 'B', font_bold)
                pdf.set_font("Arial", size=10)
            else:
                pdf.set_font("Helvetica", size=10)
        except Exception:
            pdf.set_font("Helvetica", size=10)

        # --- HLAVIČKA ---
        pdf.set_font("Arial", size=16, style='B')
        pdf.cell(0, 10, txt=f"PŘEHLED PORTFOLIA: {self._name}", ln=True, align='C')
        pdf.ln(5)

        # Definice sloupců tabulky
        col_widths = [80, 20, 20, 25, 25, 25, 25, 25, 25]
        headers = ["PRODUKT", "TICKER", "KS", "CENA", "BZ", "HODNOTA", "UNREAL. P/L", "ZMĚNA", "CELKEM P/L"]

        def _draw_table_header():
            pdf.set_font(style='B')
            pdf.set_fill_color(200, 220, 255)
            for i, h in enumerate(headers):
                pdf.cell(col_widths[i], 8, h, border=1, align='C', fill=True)
            pdf.ln()
            pdf.set_font(style='')

        # --- 1. SEKCE: OTEVŘENÉ POZICE ---
        pdf.set_font(size=12, style='B')
        pdf.cell(0, 10, "OTEVŘENÉ POZICE", ln=True)
        pdf.set_font(size=10)
        _draw_table_header()

        total_value_open = 0
        total_unrealized_open = 0
        total_profit_col_open = 0

        for _, position in self._position_dict.items():
            name, curr, price, _, profit, be, amt, lp, tick, realized = position.get_last_value()

            if price < 1: continue  # Přeskočení uzavřených pozic

            unrealized = profit - realized
            total_value_open += price
            total_unrealized_open += unrealized
            total_profit_col_open += profit

            growth_pct = (unrealized + price) / price * 100 if price != 0 else 0

            display_name = name
            if pdf.get_string_width(display_name) > 80:
                while pdf.get_string_width(display_name + '...') > 79 and len(display_name) > 3:
                    display_name = display_name[:-1]
                display_name += '...'

            row = [display_name, tick, f"{amt:.2f}", f"{lp:.2f} {curr}", f"{be:.2f} {curr}",
                   f"{price:.2f} {self._currency}", f"{unrealized:.2f} {self._currency}",
                   f"{growth_pct:.2f}%", f"{profit:.2f} {self._currency}"]

            for i, val in enumerate(row):
                pdf.cell(col_widths[i], 7, str(val), border=1, align='L' if i == 0 else 'R')
            pdf.ln()

        # Součtový řádek pro otevřené pozice
        pdf.set_font(style='B')
        pdf.cell(sum(col_widths[:5]), 8, "SOUČET OTEVŘENÝCH POZIC:", border=1, align='L')
        pdf.cell(col_widths[5], 8, f"{total_value_open:.2f}", border=1, align='R')
        pdf.cell(col_widths[6], 8, f"{total_unrealized_open:.2f}", border=1, align='R')
        pdf.cell(col_widths[7], 8, "-", border=1, align='C')
        pdf.cell(col_widths[8], 8, f"{total_profit_col_open:.2f}", border=1, align='R')
        pdf.ln(15)

        # --- 2. SEKCE: UZAVŘENÉ POZICE ---
        pdf.set_font(size=12, style='B')
        pdf.cell(0, 10, "UZAVŘENÉ POZICE", ln=True)
        pdf.set_font(size=10)
        _draw_table_header()

        total_profit_realized_closed = 0
        for _, position in self._position_dict.items():
            name, curr, price, _, _, be, amt, lp, tick, realized = position.get_last_value()

            if price >= 1: continue  # Přeskočení otevřených pozic

            total_profit_realized_closed += realized
            display_name = name
            if pdf.get_string_width(display_name) > 80:
                while pdf.get_string_width(display_name + '...') > 79 and len(display_name) > 3:
                    display_name = display_name[:-1]
                display_name += '...'

            row = [display_name, tick, f"{amt:.2f}", f"{lp:.2f} {curr}", f"{be:.2f} {curr}",
                   f"{price:.2f} {self._currency}", "0.00", " - ", f"{realized:.2f} {self._currency}"]

            for i, val in enumerate(row):
                pdf.cell(col_widths[i], 7, str(val), border=1, align='L' if i == 0 else 'R')
            pdf.ln()

        # Součtový řádek pro realizovaný zisk
        pdf.set_font(style='B')
        pdf.cell(sum(col_widths[:-1]), 8, "CELKEM REALIZOVANÝ ZISK (Z uzavřených):", border=1, align='L')
        pdf.cell(col_widths[-1], 8, f"{total_profit_realized_closed:.2f}", border=1, align='R')
        pdf.ln(15)

        # --- NOVÁ SEKCE: CELKOVÝ SOUHRN PORTFOLIA ---
        pdf.set_font(size=14, style='B')
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, "CELKOVÝ SOUHRN PORTFOLIA", ln=True, fill=True)
        pdf.set_font(size=11)

        # Výpočty pro souhrn
        full_total_profit = total_profit_col_open + total_profit_realized_closed
        performance_pa = self.get_performance_pa() * 100
        realized_in_open = total_profit_col_open - total_unrealized_open
        total_realized = total_profit_realized_closed + realized_in_open

        # Vykreslení řádků souhrnu
        pdf.cell(100, 8, f"Aktuální tržní hodnota portfolia:", border='B')
        pdf.cell(50, 8, f"{total_value_open:.2f} {self._currency}", border='B', ln=True, align='R')

        pdf.cell(100, 8, f"Celkový nerealizovaný P/L:", border='B')
        pdf.cell(50, 8, f"{total_unrealized_open:.2f} {self._currency}", border='B', ln=True, align='R')

        pdf.cell(100, 8, f"Celkový realizovaný P/L (vč. poplatků):", border='B')
        pdf.cell(50, 8, f"{total_realized:.2f} {self._currency}", border='B', ln=True, align='R')

        pdf.set_font(style='B')
        pdf.cell(100, 10, f"CELKOVÝ VÝSLEDEK (Profit/Loss):", border='T')
        pdf.cell(50, 10, f"{full_total_profit:.2f} {self._currency}", border='T', ln=True, align='R')

        # Zobrazení výkonnosti p.a.
        pdf.ln(5)
        pdf.set_text_color(0, 50, 150)
        pdf.cell(100, 10, f"PRŮMĚRNÝ ROČNÍ VÝNOS (p.a.):")
        pdf.cell(50, 10, f"{performance_pa:.2f} %", ln=True, align='R')
        pdf.set_text_color(0, 0, 0)

        # --- 3. SEKCE: GRAFY ---
        graph_dir = "../GRAPHS/"
        if os.path.exists(graph_dir):
            graphs = [f for f in os.listdir(graph_dir) if self._name in f and f.lower().endswith('.png')]
            graphs.sort()

            for g_name in graphs:
                pdf.add_page()
                pdf.image(os.path.join(graph_dir, g_name), x=18.5, y=35, w=260)

        # --- ULOŽENÍ A OTEVŘENÍ ---
        try:
            pdf.output(report_path)
            os.startfile(os.path.abspath(report_path))
            print(f"✅ PDF Report úspěšně vygenerován: {report_path}")
        except Exception as e:
            print(f"❌ Chyba při ukládání PDF: {e}")