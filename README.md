### Portfolio Manager

Tento projekt je nástroj v jazyce Python určený pro komplexní správu a analýzu investičních portfolií. Umožňuje uživatelům sledovat různé typy aktiv, automaticky stahovat historická data, počítat výkonnost pomocí metody FIFO a generovat detailní PDF reporty včetně grafů vývoje.

### Hlavní funkce projektu

* **Sledování širokého spektra aktiv:** Podpora pro akcie, ETF, kryptoměny, forex, komodity a futures.
* **Automatické stahování dat:** Integrace s Yahoo Finance pro získávání historických cen a informací o aktivech.
* **Inteligentní normalizace dat:** Automatické čištění stažených dat, odstraňování outlierů a doplňování chybějících záznamů.
* **Výpočet metodou FIFO:** Přesný výpočet realizovaného zisku/ztráty a nákupní ceny (Break-Even Point).
* **Měnová konverze:** Automatický přepočet všech pozic a historie do jedné zvolené základní měny portfolia pomocí historických kurzů.
* **Import z CSV:** Podpora hromadného načítání transakcí z exportů brokera (např. Degiro).
* **Generování reportů:** Export přehledného PDF se statistikami a grafy vývoje ceny, profitu a báze.

### Navigace v projektu

Projekt je rozdělen do několika logických složek podle typu dat:

```text
Adresářová struktura
/
├── DATA/                   # Centrální úložiště dat
│   ├── ASSET_HISTORY/      # Historická data aktiv (CSV)
│   ├── ASSET_INFO/         # Metadata o aktivech (JSON)
│   ├── FIGI_DATA/          # Cache pro mapování ISIN kódů (OpenFIGI)
│   ├── IMPORTANT/          # Konfigurační soubory a převodní tabulky
│   ├── PERSONAL/           # Uživatelské exporty a hotové PDF reporty
│   └── POSITION_PRICES/    # Historie vypočtených cen pozic
├── GRAPHS/                 # Automaticky generované grafy (PNG)
└── PROGRAM/                # Zdrojové kódy aplikace (.py soubory)
```

### Popis klíčových souborů v /PROGRAM

| Soubor | Popis |
| :--- | :--- |
| **Portfolio.py** | Hlavní řídicí třída pro správu kolekce pozic a generování PDF. |
| **Position.py** | Logika výpočtu konkrétní investiční pozice (FIFO, měnový převod). |
| **Asset.py** | Definice tříd pro různé typy finančních instrumentů a jejich grafy. |
| **Transaction.py** | Zpracování nákupních a prodejních transakcí (vč. frakčních). |
| **DownloadManager.py** | Zajišťuje stahování, ukládání a čištění historických dat. |
| **BrokerImports.py** | Obsahuje funkce pro import transakcí z externích CSV souborů. |
| **FigiApi.py** | Komunikace s OpenFIGI API pro mapování ISIN na Yahoo tickery. |
| **Showcase.py** | Ukázkový skript demonstrující vytvoření portfolia a generování reportu. |


### Instalace

1. **Požadavky:** Ujistěte se, že máte nainstalován Python verze **3.10** nebo novější.
2. **Klonování:** Stáhněte (nebo naklonujte) projekt do svého lokálního pracovního adresáře.
3. **Instalace knihoven:** V kořenovém adresáři projektu spusťte příkaz:
   ```bash
   pip install -r requirements.txt
    ```
### Spuštění

Pro rychlé vyzkoušení funkčnosti systému je připraven soubor `Showcase.py`.

1. **Přejděte do složky se zdroji:** Otevřete terminál a přejděte do adresáře `/PROGRAM`.
2. **Spusťte ukázkový skript:**
   ```bash
   python Showcase.py
    ```
3. **Zkontrolujte výstupy:**
    * **Grafy:** V adresáři `/GRAPHS` se vytvoří vizualizace vývoje portfolia.
    * **PDF Report:** V adresáři `/DATA/PERSONAL` bude vygenerován soubor `Portfolio_Report_Showcase_Portfolio.pdf`.
    * **Zobrazení:** Skript se po dokončení automaticky pokusí vygenerovaný PDF report otevřít.
### Vlastní nastavení

Pro analýzu vlastních investic můžete v souboru Showcase.py upravovat parametry metody new_transaction (přidání nákupů/prodejů) nebo využít funkci load_transactions_to_portfolio pro načtení vlastního CSV souboru ve formátu brokera Degiro. Formáty jiných brokerů zatím nejsou podporované.