import pandas as pd
import os
from Portfolio import Portfolio, TransactionType

# ==============================================================================
# FUNKCE PRO NAČTENÍ TRANSAKCÍ Z CSV DO PORTFOLIA
# ==============================================================================

def load_transactions_to_portfolio(portfolio: Portfolio, file_path: str) -> bool:
    """
    Načte transakce z CSV souboru (formát Degiro) a vloží je do objektu portfolia.
    Vrací True při úspěchu, False při chybě.
    """
    try:
        # 1. Kontrola existence souboru na zadané cestě
        if not os.path.exists(file_path):
            print(f"[CHYBA]: Soubor nebyl nalezen: {file_path}")
            return False

        # 2. Načtení dat z CSV souboru
        # Použití desetinné čárky pro správný import číselných hodnot
        transactions_df = pd.read_csv(file_path, decimal=',')

        if transactions_df.empty:
            print(f"[CHYBA]: Soubor {file_path} neobsahuje žádná data.")
            return False

        # 3. Předzpracování dat (Normalizace formátu)
        # Sjednocení data a času do indexu
        transactions_df['Datetime'] = transactions_df['Datum'].astype(str) + ' ' + transactions_df['Čas'].astype(str)
        transactions_df['Datetime'] = pd.to_datetime(transactions_df['Datetime'], format='%d-%m-%Y %H:%M')
        transactions_df = transactions_df.set_index('Datetime')

        # Odstranění nepotřebných sloupců a přejmenování pro konzistenci
        transactions_df.drop(columns=['Datum', 'Čas'], inplace=True, errors='ignore')
        transactions_df.rename(columns={
            "Směnný kurz": "rate",
            "Unnamed: 8": "Currency",
            "Reference exchange": "Exchange"
        }, inplace=True)

        # Doplnění chybějících kurzů a chronologické seřazení
        transactions_df["rate"] = transactions_df["rate"].fillna(1.0)
        transactions_df = transactions_df.sort_index()

        # 4. Iterace přes vyčištěná data a přidávání transakcí
        for row in transactions_df.itertuples():
            # Přidání transakce skrze veřejné rozhraní portfolia
            portfolio.new_transaction(
                transaction_type=TransactionType.LONG,
                date=row.Index,
                ticker=row.ISIN,
                amount=row.Počet,
                price=row.Cena,
                currency=row.Currency,
                venue=row.Exchange
            )

        print(f"[ÚSPĚCH]: Načteno {len(transactions_df)} transakcí do portfolia '{portfolio._name}'.")
        return True

    except Exception as e:
        # Obecný fallback pro nečekané chyby (např. chybná struktura CSV)
        print(f"[KRITICKÁ CHYBA]: Selhání při zpracování souboru {file_path}: {e}")
        return False
