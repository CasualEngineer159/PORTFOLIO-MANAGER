import json
import urllib.request
import urllib.parse
import os
import pandas as pd

# ==============================================================================
# KONFIGURACE A NASTAVENÍ API
# ==============================================================================

# Načtení API klíče z prostředí nebo nastavení výchozí hodnoty
OPENFIGI_API_KEY = os.environ.get("OPENFIGI_API_KEY", None)
OPENFIGI_BASE_URL = "https://api.openfigi.com"

# Definice typu pro JSON odpovědi (pro lepší čitelnost kódu)
JsonType = None | int | str | bool | list | dict


# ==============================================================================
# POMOCNÉ FUNKCE PRO PRÁCI S DATY A DISKEM
# ==============================================================================

# Načte uloženou odpověď z OpenFIGI z lokálního JSON souboru
def load_figi_response(isin: str) -> dict:
    try:
        # Definice cesty k souboru
        file_path = f"../DATA/FIGI_DATA/figi.response.{isin}.json"

        # Pokus o otevření a načtení dat
        with open(file_path, 'r', encoding='utf-8') as f:
            figi_data = json.load(f)
        return figi_data
    except (FileNotFoundError, json.JSONDecodeError):
        # V případě chyby vrátí prázdný slovník
        return {}


# Uloží odpověď z API do lokálního souboru pro budoucí použití
def save_figi_response(response: JsonType, isin: str) -> None:
    # Definice cesty k souboru
    file_path = f"../DATA/FIGI_DATA/figi.response.{isin}.json"

    # Zápis dat ve formátu JSON s odsazením
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(response, f, indent=4)


# Interpretuje kód burzy a vrací příslušné FIGI a Yahoo suffixy
def venue_interpreter(venue: str) -> tuple:
    # Načtení převodní tabulky burz
    exchange_codes = pd.read_csv(
        '../DATA/IMPORTANT/EXCHANGE_CODES.csv',
        delimiter=";",
        keep_default_na=False,
    )

    # Vyhledání řádku obsahujícího daný kód burzy
    mask = exchange_codes.apply(lambda row: row.astype(str).str.contains(venue, na=False).any(), axis=1)
    matched_indices = exchange_codes[mask].index.tolist()

    # Inicializace výchozích hodnot
    figi_code, yahoo_suffix = None, None

    # Pokud byl nalezen záznam, extrahujeme kódy
    if len(matched_indices) > 0:
        figi_code = exchange_codes["figi_code"].iloc[matched_indices[0]]
        yahoo_suffix = exchange_codes["yahoo_suf"].iloc[matched_indices[0]]

    # Vrátí nalezené identifikátory
    return figi_code, yahoo_suffix


# ==============================================================================
# KOMUNIKACE S OPENFIGI API
# ==============================================================================

# Provede nízkoúrovňové volání OpenFIGI API
def api_call(path: str, data: list | None = None, method: str = "POST") -> JsonType:
    # Příprava HTTP hlaviček
    headers = {"Content-Type": "application/json"}
    if OPENFIGI_API_KEY:
        headers["X-OPENFIGI-APIKEY"] = OPENFIGI_API_KEY

    # Sestavení požadavku
    request = urllib.request.Request(
        url=urllib.parse.urljoin(OPENFIGI_BASE_URL, path),
        data=data and bytes(json.dumps(data), encoding="utf-8"),
        headers=headers,
        method=method,
    )

    # Provedení požadavku a zpracování odpovědi
    with urllib.request.urlopen(request) as response:
        response_text = response.read().decode("utf-8")
        response_json = json.loads(response_text)

        # Vrátí naparsovaný JSON objekt
        return response_json


# ==============================================================================
# HLAVNÍ VEŘEJNÉ FUNKCE
# ==============================================================================

# Získá mapu tickerů pro daný ISIN a vrátí ticker pro konkrétní burzu
def ticker_from_isin(isin: str, exchange: str) -> str | None:
    # Nejprve zkusíme načíst data z lokální mezipaměti
    mapping_response = load_figi_response(isin)

    # Pokud data nejsou lokálně, dotážeme se API
    if not mapping_response:
        # Příprava těla dotazu pro hromadné mapování
        mapping_request = [{"idType": "ID_ISIN", "idValue": isin}]
        mapping_response = api_call("/v3/mapping", mapping_request)

        # Uložení výsledku pro příští použití
        save_figi_response(mapping_response, isin)

    # Mapa pro uložení nalezených tickerů podle burz
    ticker_map = {}

    # Procházení výsledků z API odpovědi
    for result in mapping_response:
        # Kontrola, zda výsledek obsahuje platná data
        if 'data' in result:
            for entry in result['data']:
                exch_code = entry.get('exchCode')
                ticker = entry.get('ticker')

                # Pokud máme kód burzy i ticker, přidáme do mapy
                if exch_code and ticker:
                    ticker_map[exch_code] = ticker

    # Vrátí ticker pro požadovanou burzu nebo None
    return ticker_map.get(exchange, None)