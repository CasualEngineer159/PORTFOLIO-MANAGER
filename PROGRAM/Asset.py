import matplotlib.pyplot as plt
from DownloadManager import *
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import numpy as np


yfinance_m = YfinanceManager()
aplha_vantage_m = AlphaVantage()
twelve_data_m = TwelveData()

def create_dataframe_from_date(date) -> pd.DataFrame:
    _dates = pd.date_range(start=date, end=datetime.now().date(), freq='D')
    df = pd.DataFrame()
    df = df.reindex(_dates)
    df.index.name = "Date"
    df["Base"] = np.nan
    df["Profit"] = np.nan
    df["Price"] = np.nan
    df["Growth"] = np.nan
    df["Mask"] = True
    return df


def plot_price(history, date, plot_name, column):
    # Zvětšíme plochu grafu.
    # Už nepotřebujeme tolik místa vpravo (right=0.8) pro textové popisky,
    # ale budeme tam dávat legendu, takže nějaké místo se hodí.
    # Matplotlib si s bbox_inches='tight' při ukládání poradí s místem automaticky.
    fig, ax = plt.subplots(figsize=(12, 7))

    # Výběr dat a ošetření typů
    try:
        history_to_plot = history.loc[date:, [column, 'Mask']]
        history_to_plot = history_to_plot.asfreq('D')

        history_to_plot = history_to_plot.infer_objects(copy=False)
        history_to_plot['Mask'] = history_to_plot['Mask'].ffill()
        history_to_plot[column] = history_to_plot[column].ffill()
    except KeyError as e:
        print(f"Chyba při výběru dat: {e}. Zkontrolujte názvy sloupců nebo index.")
        plt.close()
        return

    # --- VÝPOČET STATISTIK ---
    valid_data = history_to_plot[column].dropna()

    if not valid_data.empty:
        max_val = valid_data.max()
        min_val = valid_data.min()
        last_val = valid_data.iloc[-1]
    else:
        # Pojistka pro prázdná data
        print("Žádná platná data pro vykreslení.")
        plt.close()
        return

    # --- VYKRESLENÍ SEGMENTŮ (Původní logika) ---
    mask_values = history_to_plot['Mask'].values
    # Ošetření pro případ, že jsou data příliš krátká pro detekci změn
    if len(mask_values) > 1:
        change_points = np.where(mask_values[:-1] != mask_values[1:])[0]
        split_indices = [0] + (change_points + 1).tolist() + [len(history_to_plot)]
    else:
        split_indices = [0, len(history_to_plot)]

    for i in range(len(split_indices) - 1):
        start_idx = split_indices[i]
        end_idx = split_indices[i + 1]
        # Ošetření rozsahu řezu
        slice_end = end_idx + 1 if end_idx < len(history_to_plot) and len(mask_values) > 1 else end_idx
        segment = history_to_plot.iloc[start_idx:slice_end]

        if segment.empty: continue

        # Získání hodnoty masky bezpečně
        is_real_val = mask_values[start_idx] if start_idx < len(mask_values) else mask_values[0]
        # Převod na boolean, pokud je to nutné (např. pokud je maska float 1.0/0.0)
        is_real = bool(is_real_val)

        color = 'black' if is_real else 'gray'
        ax.plot(segment.index, segment[column], color=color, linewidth=1.8)

    # --- VYKRESLENÍ VÝRAZNÝCH RISEK (Horizontální linky) ---
    # Místo složité funkce s textem nyní jen vykreslíme výrazné linky.
    # linewidth=2 (tlustší), alpha=0.7 (méně průhledné), linestyle='-' (plná čára)
    ax.axhline(y=max_val, color="forestgreen", linestyle='dotted', linewidth=1, alpha=0.7)
    ax.axhline(y=min_val, color="firebrick", linestyle='dotted', linewidth=1, alpha=0.7)
    ax.axhline(y=last_val, color="royalblue", linestyle='dotted', linewidth=1, alpha=0.7)


    # Úprava limitů osy Y (Původní logika)
    y_range = max_val - min_val
    if y_range <= 1e-9: y_range = 1 # Ošetření pro téměř nulový rozsah
    # Přidáme trochu více místa nahoře a dole (0.15 místo 0.1), aby linky nebyly na hraně
    ax.set_ylim(min_val - 0.15 * y_range, max_val + 0.15 * y_range)

    # Formátování grafu
    ax.set_title(f'{plot_name}', fontsize=16, pad=20)
    ax.set_xlabel('Datum', fontsize=12)
    ax.set_ylabel('Hodnota', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.5)
    plt.xticks(rotation=45) # Natočení popisků osy X pro lepší čitelnost

    # --- NOVÁ LEGENDA ---
    # Vytvoříme seznam prvků pro legendu. Použijeme Line2D pro definici barev a stylů.

    legend_elements = [
        # 1. Historie (Původní)
        Line2D([0], [0], color='black', lw=2, label='Kompletní historie'),
        Line2D([0], [0], color='gray', lw=2, label='Nekompletní historie'),

        # 2. Oddělovač (prázdná čára pro vizuální mezeru v legendě)
        Line2D([0], [0], color='none', label=''),

        # 3. Statistiky cen (Nové)
        # Barvy odpovídají horizontálním linkám v grafu.
        # Do labelu formátujeme vypočítanou cenu.
        Line2D([0], [0], color='forestgreen', lw=2, label=f'High: {max_val:.2f}'),
        Line2D([0], [0], color='firebrick', lw=2, label=f'Low: {min_val:.2f}'),
        Line2D([0], [0], color='royalblue', lw=2, label=f'End: {last_val:.2f}'),
    ]

    # Umístění legendy:
    # loc='upper left' dá legendu dovnitř grafu (může překrývat data).
    # Pokud ji chcete vedle grafu (jak byly původní popisky), použijte:
    # bbox_to_anchor=(1.02, 1), loc='upper left' -> umístí levý horní roh legendy těsně za pravý okraj grafu.
    ax.legend(handles=legend_elements,
              loc='upper left',
              bbox_to_anchor=(1.02, 1), # Umístění vpravo mimo graf
              title="Legenda & Statistiky",
              frameon=True,
              fancybox=True, framealpha=0.9, shadow=True) # Vizuální vylepšení rámečku


    filename = f"../GRAPHS/{plot_name}.png"
    # bbox_inches='tight' je zde klíčové, zajistí, že se legenda mimo graf neořízne.
    plt.savefig(filename, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Graf uložen: {filename}")


class Asset:

    def __init__(self, ticker):
        self._ticker = ticker
        self._stock_info = self.manager.get_info(ticker)
        self._daily_history = self.manager.get_history(ticker)
        self._name = self._stock_info.get("longName", self._ticker)

    def get_short_name(self):
        return self._stock_info.get("shortName", self._ticker)

    def get_venue(self) -> str:
        return self._stock_info.get("exchange", None)

    def get_ticker(self) -> str:
        return self.manager.get_ticker(self._ticker)

    def get_name(self) -> str:
        return self._name

    def get_currency(self) -> str:
        return self._stock_info.get("currency", None)

    def get_earliest_record_date(self) -> datetime:
        self._daily_history.sort_index()
        return self._daily_history.index[0]

    def plot_closing_price(self):
        plot_price(self._daily_history, self.get_earliest_record_date(), f"{self._name} closing price graph")

    def get_prices(self, start_date) -> pd.DataFrame:
        self._daily_history.sort_index()
        nearest_row = self._daily_history.index.asof(start_date)
        if pd.isna(nearest_row):
            return self._daily_history.copy()
        return self._daily_history.loc[nearest_row:].copy()

class Stock(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)

class Commodity(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)

class Crypto(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)

class ETF(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)

class Futures(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)
        self._name = self._stock_info.get("shortName", self._ticker)

class Forex(Asset):
    def __init__(self, ticker):
        self.manager = yfinance_m
        super().__init__(ticker)

    def get_prices(self, start_date) -> pd.DataFrame:
        self._daily_history.sort_index()
        self._daily_history = fill_gaps(self._daily_history)
        return self._daily_history.loc[start_date:].copy()

    def get_rate(self, date=datetime.now()) -> float:
        return get_closest_value(self._daily_history, date,"Close")

forex_dict = {}
def forex_creator(from_currency, to_currency) -> Forex:
    ticker = from_currency + to_currency + "=X"
    if ticker in forex_dict.keys():
        return forex_dict[ticker]
    forex = Forex(ticker)
    forex_dict[ticker] = forex
    return forex

asset_dict = {}
def asset_creator(ticker) -> Stock:
    if ticker in asset_dict.keys():
        return asset_dict[ticker]
    stock = Stock(ticker)
    asset_dict[ticker] = stock
    return stock

def get_closest_value(df, wanted_date, column):
    df = df.sort_index()
    idx = df.index.asof(wanted_date)
    if pd.isna(idx):
        idx = df.index[0]
    return df[column].loc[idx]
