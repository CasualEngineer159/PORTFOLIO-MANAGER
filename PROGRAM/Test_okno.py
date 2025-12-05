import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkcalendar import DateEntry
from datetime import date

# -----------------------------------------------------------------
# 1. ZDE JE VAŠE FUNKCE (jako placeholder)
# Tuto funkci nahraďte vaší existující funkcí.
# -----------------------------------------------------------------
def moje_vlastni_funkce(typ, ticker, datum, cena, pocet):
    """
    Toto je vaše cílová funkce, která zpracuje data.
    Pro účely demonstrace je jen vypíšeme a ukážeme v okně.
    """
    print("--- Funkce byla zavolána ---")
    print(f"Typ: {typ}")
    print(f"Ticker: {ticker}")
    print(f"Datum: {datum} (Typ: {type(datum)})")
    print(f"Cena: {cena} (Typ: {type(cena)})")
    print(f"Počet: {pocet} (Typ: {type(pocet)})")
    
    # Zobrazit potvrzení v GUI
    messagebox.showinfo(
        "Úspěch!",
        f"Data byla odeslána:\n\n"
        f"Typ: {typ}\n"
        f"Ticker: {ticker}\n"
        f"Datum: {datum.strftime('%d.%m.%Y')}\n"
        f"Cena: {cena}\n"
        f"Počet: {pocet}"
    )


# -----------------------------------------------------------------
# 2. POMOCNÁ FUNKCE, KTERÁ SBÍRÁ DATA Z OKNA A VOLÁ VAŠI FUNKCI
# -----------------------------------------------------------------
def odeslat_data():
    """
    Tato funkce se zavolá po stisknutí tlačítka "Odeslat".
    Shromáždí data z polí, provede základní kontrolu a zavolá 
    'moje_vlastni_funkce'.
    """
    # Získání hodnot z polí
    vybrany_typ = typ_combobox.get()
    zadaný_ticker = ticker_entry.get()
    vybrane_datum = datum_calendar.get_date() # Vrací objekt datetime.date
    
    # Kontrola a konverze číselných hodnot
    try:
        zadana_cena = float(cena_entry.get().replace(',', '.')) # Povolí i desetinnou čárku
        zadany_pocet = int(pocet_entry.get())
    except ValueError:
        messagebox.showerror("Chyba vstupu", "Cena a Počet musí být platná čísla.")
        return # Přeruší funkci, pokud data nejsou čísla

    # Kontrola, zda jsou vyplněny textové hodnoty
    if not vybrany_typ or not zadaný_ticker:
        messagebox.showwarning("Chybějící data", "Vyplňte prosím Typ a Ticker.")
        return

    # Pokud je vše v pořádku, zavoláme vaši hlavní funkci
    moje_vlastni_funkce(
        typ=vybrany_typ,
        ticker=zadaný_ticker,
        datum=vybrane_datum,
        cena=zadana_cena,
        pocet=zadany_pocet
    )
    
    # Volitelné: Po odeslání zavřít okno
    # root.destroy()


# -----------------------------------------------------------------
# 3. NASTAVENÍ HLAVNÍHO OKNA (GUI)
# -----------------------------------------------------------------

# Inicializace hlavního okna
root = tk.Tk()
root.title("Vstupní formulář transakce")

# Použití 'ttk.Frame' pro lepší vzhled a odsazení
frame = ttk.Frame(root, padding="20 20 20 20")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

# Nastavení rozložení (grid)
frame.columnconfigure(1, weight=1) # Dovolí vstupním polím se roztáhnout

# --- 1. řádek: Typ (Combobox/Dropdown) ---
ttk.Label(frame, text="Typ:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
typy_transakci = ['Stock', 'ETF', 'Commodity', 'Crypto']
typ_combobox = ttk.Combobox(frame, values=typy_transakci, state="readonly")
typ_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
typ_combobox.current(0) # Nastaví 'BUY' jako výchozí

# --- 2. řádek: Ticker (Text Entry) ---
ttk.Label(frame, text="Ticker:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
ticker_entry = ttk.Entry(frame, width=30)
ticker_entry.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

# --- 3. řádek: Datum (Calendar) ---
ttk.Label(frame, text="Datum:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
datum_calendar = DateEntry(
    frame, 
    width=27, 
    background='darkblue',
    foreground='white', 
    borderwidth=2,
    date_pattern='dd.MM.yyyy', # Český formát data
    maxdate=date.today() # Nelze vybrat datum v budoucnosti
)
datum_calendar.grid(row=2, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

# --- 4. řádek: Cena (Text Entry) ---
ttk.Label(frame, text="Cena:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
cena_entry = ttk.Entry(frame, width=30)
cena_entry.grid(row=3, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

# --- 5. řádek: Počet (Text Entry) ---
ttk.Label(frame, text="Počet:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
pocet_entry = ttk.Entry(frame, width=30)
pocet_entry.grid(row=4, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

# --- 6. řádek: Tlačítko Odeslat ---
submit_button = ttk.Button(frame, text="Odeslat", command=odeslat_data)
submit_button.grid(row=5, column=0, columnspan=2, padx=5, pady=15) # Roztažení přes 2 sloupce

# Spuštění hlavní smyčky aplikace
root.mainloop()