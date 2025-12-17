from datetime import datetime
from Portfolio import Portfolio
from Transaction import TransactionType
from BrokerImports import load_transactions_to_portfolio

# ==============================================================================
# 1. INICIALIZACE UKÁZKOVÉHO PORTFOLIA
# ==============================================================================

# Vytvoření portfolia s názvem a hlavní měnou (v té se počítají reporty)
demo_portfolio = Portfolio("Showcase_Portfolio", "EUR")

# ==============================================================================
# 2. MANUÁLNÍ ZADÁVÁNÍ TRANSAKCÍ (RŮZNÉ TYPY)
# ==============================================================================

# --- A. Standardní nákup celých kusů (LONG) ---
# Nakoupíme 5 kusů akcie Apple za cenu 150 USD (systém automaticky přepočítá na EUR)
demo_portfolio.new_transaction(
    transaction_type=TransactionType.LONG,
    date=datetime(2022, 1, 15),
    ticker="AAPL",
    amount=5,
    price=150.0,
    currency="USD"
)

# --- B. Prodej části pozice (LONG se záporným množstvím) ---
# Prodáme 2 kusy Apple za aktuální tržní cenu (systém vypočítá realizovaný zisk)
demo_portfolio.new_transaction(
    transaction_type=TransactionType.LONG,
    date=datetime(2023, 6, 10),
    ticker="AAPL",
    amount=-2
)

# --- C. Frakční nákup podle hodnoty (FRACTION_LONG) ---
# Investujeme fixní částku 1000 EUR do ETF VUSA (systém dopočítá počet kusů dle kurzu)
demo_portfolio.new_transaction(
    transaction_type=TransactionType.FRACTION_LONG,
    date=datetime(2021, 5, 20),
    ticker="VUSA.AS",
    price=1000.0  # Zde zadáváme částku, ne počet kusů
)

# --- D. Frakční prodej/výběr hodnoty (FRACTION_LONG se zápornou cenou) ---
# Vybereme (prodáme) hodnotu 500 EUR z ETF VUSA
demo_portfolio.new_transaction(
    transaction_type=TransactionType.FRACTION_LONG,
    date=datetime(2023, 12, 1),
    ticker="VUSA.AS",
    price=-500.0
)

# --- E. Transakce se specifikací burzy (Venue) ---
# Nákup na konkrétní burze (např. Tradegate), což ovlivňuje validaci tickeru
# Dobré použít pokud známe jen ISIN a burzu na které jsme kupovali
# Burza musí být zavedená do převodního souboru značení DATA/IMPORTANT/EXCHANGE_CODES.csv
demo_portfolio.new_transaction(
    transaction_type=TransactionType.LONG,
    date=datetime(2024, 2, 1),
    ticker="IE00BD1F4N50",
    amount=1,
    venue="XET"
)

# --- F. Prodej celé pozice (LONG se záporným množstvím) ---
# Prodáme 2 kusy Apple za aktuální tržní cenu (systém vypočítá realizovaný zisk)
demo_portfolio.new_transaction(
    transaction_type=TransactionType.LONG,
    date=datetime(2025, 6, 10),
    ticker="AAPL",
    amount=-100
)

# ==============================================================================
# 3. HROMADNÝ IMPORT Z EXTERNÍHO SOUBORU
# ==============================================================================

# Cesta k exportu z brokera (např. Degiro)
TRANSACTIONS_PATH = '../DATA/PERSONAL/Transactions.csv'

# Pokus o načtení transakcí z CSV (používá robustní funkci s fallbackem)
try:
    load_transactions_to_portfolio(demo_portfolio, TRANSACTIONS_PATH)
except Exception as e:
    print(f"Hromadný import přeskočen: {e}")

# ==============================================================================
# 4. VYHODNOCENÍ, GENEROVÁNÍ GRAFŮ A PDF REPORTU
# ==============================================================================

# Spuštění kompletního výpočetního jádra (historie, zisky, růst)
demo_portfolio.evaluate_portfolio()