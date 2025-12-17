import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime
from matplotlib.lines import Line2D
from DownloadManager import YfinanceManager, fill_gaps

# Inicializace globálního manažera pro Yahoo Finance
yfinance_manager = YfinanceManager()


# ==============================================================================
# POMOCNÉ FUNKCE
# ==============================================================================

# Vytvoří prázdný DataFrame s přednastavenými sloupci od zadaného data do dneška
def create_dataframe_from_date(start_date) -> pd.DataFrame:
    # Vytvoření rozsahu datumů
    dates = pd.date_range(start=start_date, end=datetime.now().date(), freq='D')

    # Inicializace DataFrame s indexem Date
    df = pd.DataFrame(index=dates)
    df.index.name = "Date"

    # Předdefinování prázdných sloupců
    df["Base"] = np.nan
    df["Profit"] = np.nan
    df["Price"] = np.nan
    df["Growth"] = np.nan
    df["Mask"] = True

    return df


# Najde nejbližší dostupnou hodnotu v daném sloupci k zadanému datu
def get_closest_value(df: pd.DataFrame, wanted_date, column: str):
    # Seřazení podle indexu pro správné fungování metody asof
    df = df.sort_index()

    # Vyhledání nejbližšího předchozího indexu
    target_idx = df.index.asof(wanted_date)

    # Pokud není nalezen, použije se první dostupný
    if pd.isna(target_idx):
        target_idx = df.index[0]

    return df[column].loc[target_idx]


# ==============================================================================
# VIZUALIZACE
# ==============================================================================

# Vykreslí graf vývoje ceny s vyznačením statistik
def plot_price(history: pd.DataFrame, start_date, plot_name: str, column: str):
    # Inicializace grafu a os
    fig, ax = plt.subplots(figsize=(12, 7))

    # Příprava dat pro vykreslení
    try:
        data_to_plot = history.loc[start_date:, [column, 'Mask']]
        data_to_plot = data_to_plot.asfreq('D')
        data_to_plot = data_to_plot.infer_objects(copy=False)

        # Doplnění chybějících hodnot pro plynulost čáry
        data_to_plot['Mask'] = data_to_plot['Mask'].ffill()
        data_to_plot[column] = data_to_plot[column].ffill()
    except KeyError as e:
        plt.close()
        return

    # Výpočet základních statistik pro legendu a risky
    valid_data = data_to_plot[column].dropna()
    if valid_data.empty:
        plt.close()
        return

    max_val = valid_data.max()
    min_val = valid_data.min()
    last_val = valid_data.iloc[-1]

    # Vykreslení segmentů grafu (černá pro reálná data, šedá pro doplněná)
    mask_values = data_to_plot['Mask'].values
    if len(mask_values) > 1:
        change_points = np.where(mask_values[:-1] != mask_values[1:])[0]
        split_indices = [0] + (change_points + 1).tolist() + [len(data_to_plot)]
    else:
        split_indices = [0, len(data_to_plot)]

    for i in range(len(split_indices) - 1):
        start_idx = split_indices[i]
        end_idx = split_indices[i + 1]

        # Určení rozsahu řezu
        slice_end = end_idx + 1 if end_idx < len(data_to_plot) and len(mask_values) > 1 else end_idx
        segment = data_to_plot.iloc[start_idx:slice_end]

        if segment.empty:
            continue

        # Určení barvy podle masky (True = Černá, False = Šedá)
        is_real = bool(mask_values[start_idx]) if start_idx < len(mask_values) else bool(mask_values[0])
        line_color = 'black' if is_real else 'gray'

        ax.plot(segment.index, segment[column], color=line_color, linewidth=1.8)

    # Vykreslení horizontálních statistických linek
    ax.axhline(y=max_val, color="forestgreen", linestyle='dotted', linewidth=1, alpha=0.7)
    ax.axhline(y=min_val, color="firebrick", linestyle='dotted', linewidth=1, alpha=0.7)
    ax.axhline(y=last_val, color="royalblue", linestyle='dotted', linewidth=1, alpha=0.7)

    # Automatické nastavení limitů osy Y s polstrováním
    y_range = max_val - min_val
    if y_range <= 1e-9:
        y_range = 1
    ax.set_ylim(min_val - 0.15 * y_range, max_val + 0.15 * y_range)

    # Formátování vzhledu grafu
    ax.set_title(f'{plot_name}', fontsize=16, pad=20)
    ax.set_xlabel('Datum', fontsize=12)
    ax.set_ylabel('Hodnota', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.5)
    plt.xticks(rotation=45)

    # Definice prvků legendy
    legend_elements = [
        Line2D([0], [0], color='black', lw=2, label='Kompletní historie'),
        Line2D([0], [0], color='gray', lw=2, label='Nekompletní historie'),
        Line2D([0], [0], color='none', label=''),
        Line2D([0], [0], color='forestgreen', lw=2, label=f'High: {max_val:.2f}'),
        Line2D([0], [0], color='firebrick', lw=2, label=f'Low: {min_val:.2f}'),
        Line2D([0], [0], color='royalblue', lw=2, label=f'End: {last_val:.2f}'),
    ]

    # Umístění legendy mimo plochu grafu
    ax.legend(
        handles=legend_elements,
        loc='upper left',
        bbox_to_anchor=(1.02, 1),
        title="Legenda & Statistiky",
        frameon=True,
        fancybox=True,
        framealpha=0.9,
        shadow=True
    )

    # Uložení grafu do souboru
    filename = f"../GRAPHS/{plot_name}.png"
    plt.savefig(filename, bbox_inches='tight', dpi=150)
    plt.close()


# ==============================================================================
# TŘÍDY ASSETŮ
# ==============================================================================

class Asset:
    def __init__(self, ticker):
        self._ticker = ticker
        self._stock_info = self.manager.get_info(ticker)
        self._daily_history = self.manager.get_history(ticker)
        self._name = self._stock_info.get("longName", self._ticker)

    # Vrátí krátký název aktiva
    def get_short_name(self):
        return self._stock_info.get("shortName", self._ticker)

    # Vrátí burzu, na které se aktivum obchoduje
    def get_venue(self) -> str:
        return self._stock_info.get("exchange", None)

    # Vrátí očištěný ticker
    def get_ticker(self) -> str:
        return self.manager.get_ticker(self._ticker)

    # Vrátí dlouhý název aktiva
    def get_name(self) -> str:
        return self._name

    # Vrátí měnu aktiva
    def get_currency(self) -> str:
        return self._stock_info.get("currency", None)

    # Vrátí datum nejstaršího záznamu v historii
    def get_earliest_record_date(self) -> datetime:
        self._daily_history.sort_index()
        return self._daily_history.index[0]

    # Vygeneruje a uloží graf zavírací ceny
    def plot_closing_price(self):
        plot_price(
            self._daily_history,
            self.get_earliest_record_date(),
            f"{self._name} closing price graph",
            "Close"
        )

    # Vrátí výřez historie cen od zadaného data
    def get_prices(self, start_date) -> pd.DataFrame:
        self._daily_history.sort_index()
        nearest_row = self._daily_history.index.asof(start_date)

        if pd.isna(nearest_row):
            return self._daily_history.copy()

        return self._daily_history.loc[nearest_row:].copy()


class Stock(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_manager
        super().__init__(ticker)


class Commodity(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_manager
        super().__init__(ticker)


class Crypto(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_manager
        super().__init__(ticker)


class ETF(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_manager
        super().__init__(ticker)


class Futures(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_manager
        super().__init__(ticker)
        # U futures preferujeme krátký název kvůli expiracím
        self._name = self._stock_info.get("shortName", self._ticker)


class Forex(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_manager
        super().__init__(ticker)

    # Rozšířená metoda get_prices pro Forex, která doplňuje chybějící víkendy
    def get_prices(self, start_date) -> pd.DataFrame:
        self._daily_history.sort_index()
        self._daily_history = fill_gaps(self._daily_history)
        return self._daily_history.loc[start_date:].copy()

    # Vrátí aktuální nebo nejbližší kurz
    def get_rate(self, date=datetime.now()) -> float:
        return get_closest_value(self._daily_history, date, "Close")


# ==============================================================================
# TOVÁRNY (CREATORS) A CACHE
# ==============================================================================

forex_cache = {}
asset_cache = {}


# Vytvoří nebo vrátí existující instanci Forexu
def forex_creator(from_currency, to_currency) -> Forex:
    ticker = f"{from_currency}{to_currency}=X"
    if ticker in forex_cache:
        return forex_cache[ticker]

    forex_obj = Forex(ticker)
    forex_cache[ticker] = forex_obj
    return forex_obj


# Vytvoří nebo vrátí existující instanci Akcie
def asset_creator(ticker) -> Stock:
    if ticker in asset_cache:
        return asset_cache[ticker]

    stock_obj = Stock(ticker)
    asset_cache[ticker] = stock_obj
    return stock_obj