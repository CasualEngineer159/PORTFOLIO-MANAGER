import pandas as pd
import numpy as np
from datetime import datetime
from enum import IntEnum
from typing import Tuple
from Asset import *


# ==============================================================================
# ENUMERACE TYPŮ TRANSAKCÍ
# ==============================================================================

class TransactionType(IntEnum):
    LONG = 1
    FRACTION_LONG = 2


# ==============================================================================
# ZÁKLADNÍ TŘÍDA PRO TRANSAKCE
# ==============================================================================

class Transaction:
    def __init__(self, asset: Asset, date: datetime, amount_owned: float,
                 amount: int = None, price: float = None):

        # Základní atributy transakce
        self._asset = asset
        self._date = date
        self._amount_owned = amount_owned
        self._amount = amount
        self._price = price

        # Inicializace výsledného dataframe a stavu
        self._transaction_prices = create_dataframe_from_date(self._date)
        self._terminate_position = False

        # 1. Nastavení specifických parametrů dle typu transakce
        self._set_parameters()

        # 2. Validace a kontrola dat
        self._check_transaction()
        self._check_amount(amount_owned)

        # 3. Výpočet finančních ukazatelů časové řady
        self._create_base()
        self._create_change()
        self._create_profit()
        self._create_price()
        self._create_mask()

    # ==============================================================================
    # VNITŘNÍ METODY PRO NASTAVENÍ A VALIDACI
    # ==============================================================================

    # Metoda určená k přepsání v potomcích pro nastavení specifických dat
    def _set_parameters(self):
        pass

    # Načte cenovou historii aktiva a připraví pomocné proměnné
    def _get_history(self):
        # Generování rozsahu dat od transakce do dneška
        self._dates = pd.date_range(start=self._date, end=datetime.now().date(), freq='D')

        # Získání cenových dat z objektu aktiva
        self._history = self._asset.get_prices(self._date)
        self._first_record_date = self._asset.get_earliest_record_date()
        self._record_to_date = self._get_record_to_date()

    # Vrátí záznam ceny nejbližší datu transakce
    def _get_record_to_date(self) -> pd.DataFrame:
        # Vyhledání nejbližšího předchozího nebo shodného záznamu
        nearest_row = self._history.index.asof(self._date)

        # Pokud záznam neexistuje, zkusíme reindexaci časové řady
        if pd.isna(nearest_row):
            self._history = self._history.reindex(self._dates)
            self._history.index = self._history.index.date
            return self._get_record_to_date()

        # Vrátí nalezený řádek historie
        return self._history.loc[nearest_row]

    # Prověří, zda transakce proběhla v platném čase a za reálnou cenu
    def _check_transaction(self):
        # Kontrola, zda transakce nepředchází dostupným datům
        if self._date < self._first_record_date:
            print(f"!!! Pozor: Pro datum {self._date} u aktiva {self._asset.get_name()} neexistují cenové záznamy.")
            print(f"    První dostupný záznam v databázi: {self._first_record_date}")

            # Pokud nebyla zadána cena, použijeme první dostupnou zavírací cenu
            if self._price is None:
                self._price = self._history.loc[self._first_record_date, "Close"]
        else:
            # Pokud nebyla zadána cena, použijeme zavírací cenu daného dne
            if self._price is None:
                self._price = self._record_to_date["Close"]

            # Kontrola denního rozmezí (High/Low)
            low = self._record_to_date["Low"]
            high = self._record_to_date["High"]

            # Upozornění, pokud je zadaná cena mimo rozsah daného dne
            if not (low <= self._price <= high):
                print(f"!!! Varování: Cena {self._asset.get_name()} ({self._price}) je mimo denní rozsah.")
                print(f"    Platný rozsah pro tento den: {low:.2f} - {high:.2f}")

    # Kontroluje, zda prodej nepřekračuje držené množství
    def _check_amount(self, amount_owned):
        # Pokud by množství kleslo pod nulu, uzavřeme pozici na nulu
        if amount_owned + self._amount <= 0:
            self._amount = -amount_owned
            self._terminate_position = True

    # ==============================================================================
    # VNITŘNÍ METODY PRO VÝPOČET HISTORIE (DATAFRAME)
    # ==============================================================================

    # Vypočítá počáteční investovanou částku (Base)
    def _create_base(self):
        # Násobek množství a pořizovací ceny
        self._transaction_prices["Base"] = self._amount * self._price

    # Vypočítá kumulativní vývoj hodnoty (Growth) od data transakce
    def _create_change(self):
        # Výpočet denních výnosů od data transakce
        returns = self._history.loc[self._date:, "return"]
        returns = returns.reindex(index=self._transaction_prices.index)
        returns = returns.fillna(0) + 1

        # Výpočet změny ceny uvnitř dne nákupu vůči zavírací ceně
        # $$ \text{intraday\_change} = \frac{\text{Close} - \text{Price}}{\text{Price}} + 1 $$
        intraday_change = (self._history.iloc[0]["Close"] - self._price) / self._price + 1

        if pd.isna(intraday_change):
            intraday_change = (self._history.loc[self._first_record_date, "Close"] - self._price) / self._price + 1

        # Nastavení úvodní změny na první den transakce
        returns.iloc[0] = intraday_change

        # Výpočet kumulativního produktu pro získání vývojové křivky
        self._transaction_prices["Growth"] = returns.cumprod()

    # Vypočítá průběžný zisk v absolutních hodnotách
    def _create_profit(self):
        # Rozdíl mezi aktuální hodnotou a základem
        self._transaction_prices["Profit"] = self._transaction_prices["Base"] * (self._transaction_prices["Growth"] - 1)

    # Vypočítá celkovou tržní cenu pozice v čase
    def _create_price(self):
        # Součet nákupního základu a dosaženého zisku
        self._transaction_prices["Price"] = self._transaction_prices["Base"].add(self._transaction_prices["Profit"])

    # Vytvoří masku platnosti dat na základě existence cen v historii
    def _create_mask(self):
        # Reindexace historie pro kontrolu děr v datech
        _dates = pd.date_range(start=self._date, end=datetime.now().date(), freq='D')
        self._history = self._history.reindex(_dates)

        # Maska je True tam, kde máme k dispozici zavírací cenu
        self._transaction_prices["Mask"] = self._history["Close"].notna()

    # ==============================================================================
    # VEŘEJNÉ PŘÍSTUPOVÉ METODY (GETTERY)
    # ==============================================================================

    # Vrátí nákupní základnu (Base)
    def get_base(self):
        return self._transaction_prices["Base"]

    # Vrátí počet kusů v transakci
    def get_amount(self) -> float:
        return self._amount

    # Vrátí jednotkovou cenu transakce
    def get_price(self) -> float:
        return self._price

    # Vrátí kompletní DataFrame s vypočtenou historií
    def get_transaction(self):
        return self._transaction_prices

    # Vrátí datum provedení transakce
    def get_date(self) -> datetime:
        return self._date


# ==============================================================================
# KONKRÉTNÍ IMPLEMENTACE TYPŮ TRANSAKCÍ
# ==============================================================================

class LongTransaction(Transaction):
    def __init__(self, asset: Asset, date: datetime, amount_owned: float,
                 amount: int = None, price: float = None):
        super().__init__(asset, date, amount_owned, amount, price)

    # Nastaví parametry specifické pro nákup celých kusů
    def _set_parameters(self):
        # Načtení historie a názvu aktiva
        self._get_history()
        self._name = self._asset.get_name()


class LongFractionTransaction(Transaction):
    def __init__(self, asset: Asset, date: datetime, amount_owned: float,
                 amount: int = None, price: float = None):
        super().__init__(asset, date, amount_owned, amount, price)

    # Nastaví parametry pro frakční nákup (přepočet množství z ceny)
    def _set_parameters(self):
        # Načtení historie
        self._get_history()
        self._name = self._asset.get_name()

        # Určení aktuální zavírací ceny pro přepočet frakce
        close_price = self._record_to_date["Close"]
        if pd.isna(close_price):
            close_price = self._history.loc[self._first_record_date, "Close"]

        # Přepočet množství na základě vložené částky (v parametru price) a kurzu
        self._amount = self._price / close_price
        self._price = close_price