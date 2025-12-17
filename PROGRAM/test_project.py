import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock, patch

# Import testovaných komponent systému
from DownloadManager import fill_gaps, _delete_outliers
from Portfolio import Portfolio, TransactionType

# ==============================================================================
# POMOCNÉ FUNKCE PRO TESTOVÁNÍ (MOCK DATA)
# ==============================================================================

# Generuje falešnou historii cen pro testování bez nutnosti stahování dat
def create_mock_history(start_date='2023-01-01', days=10, start_price=100.0, trend=0.0):
    # Vytvoření časového rozsahu a prázdného pole pro záznamy
    dates = pd.date_range(start=start_date, periods=days, freq='D')
    data = []

    current_price = start_price
    for _ in range(days):
        # Simulace denních cenových limitů (OHLC)
        row = {
            "Open": current_price,
            "High": current_price + 1,
            "Low": current_price - 1,
            "Close": current_price,
            "Volume": 1000
        }
        data.append(row)
        current_price += trend  # Simulace lineárního růstu nebo poklesu

    # Vytvoření DataFrame a převedení indexu na čisté datum
    df = pd.DataFrame(data, index=dates)
    df.index.name = "Date"
    df.index = df.index.date

    # Výpočet sloupce s denní výnosností (pro potřeby normalizace)
    df['return'] = df['Close'].pct_change()

    return df

# ==============================================================================
# TESTY ČIŠTĚNÍ DAT (DOWNLOAD MANAGER)
# ==============================================================================

# Ověřuje správné doplnění chybějících obchodních dní v časové řadě
def test_fill_gaps():
    # Příprava dat s mezerou (pátek a pondělí)
    dates = [datetime(2023, 1, 6), datetime(2023, 1, 9)]
    df = pd.DataFrame({'Close': [100, 102], 'High': [101, 103], 'Low': [99, 101]}, index=dates)
    df.index.name = "Date"

    # Vyplnění mezer předchozími hodnotami
    filled_df = fill_gaps(df)

    # Kontrola, zda index obsahuje chybějící víkendové dny
    assert pd.Timestamp('2023-01-07') in filled_df.index
    assert pd.Timestamp('2023-01-08') in filled_df.index

    # Ověření, že sobotní cena odpovídá páteční zavírací ceně
    val_saturday = filled_df.loc[pd.Timestamp('2023-01-07'), 'Close']
    assert val_saturday == 100

# Prověřuje schopnost systému identifikovat a odstranit extrémní cenové výkyvy
def test_delete_outliers():
    # Příprava dat a vložení chybné hodnoty (outlier)
    df = create_mock_history(days=10, start_price=100)
    target_date = df.index[5]
    df.loc[target_date, 'Close'] = 500.0
    df['return'] = df['Close'].pct_change()

    # Odstranění nalezených outlierů z DataFrame
    cleaned_df = _delete_outliers(df)

    # Ověření, že extrémní hodnota 500 byla skutečně smazána
    assert 500.0 not in cleaned_df['Close'].values
    assert len(cleaned_df) < len(df)

# ==============================================================================
# TESTY LOGIKY PORTFOLIA A TRANSAKCÍ
# ==============================================================================

# Fixture pro vytvoření čisté instance portfolia před každým testem
@pytest.fixture
def mock_portfolio():
    return Portfolio("Test_Portfolio", "USD")

# Testuje základní nákupní transakci a správnost následného výpočtu hodnoty
@patch('pandas.DataFrame.to_csv')
@patch('Asset.YfinanceManager.get_history')
@patch('Asset.YfinanceManager.get_info')
def test_buy_stock_transaction(mock_get_info, mock_get_history, mock_to_csv, mock_portfolio):
    # Nastavení simulovaných dat pro Yahoo Finance API
    mock_get_info.return_value = {"longName": "Apple Inc.", "currency": "USD", "shortName": "AAPL"}
    history_df = create_mock_history(start_date='2023-01-01', days=30, start_price=150.0)
    mock_get_history.return_value = history_df

    # Provedení transakce: Nákup 10 kusů akcie
    mock_portfolio.new_transaction(
        transaction_type=TransactionType.LONG,
        date=datetime(2023, 1, 5),
        ticker="AAPL",
        amount=10,
        price=150.0,
        currency="USD"
    )

    # Vynucení výpočtu historie pozice
    position = mock_portfolio.get_position("AAPL")
    position.get_position("USD")

    # Získání výsledných hodnot a ověření množství a celkové ceny
    values = position.get_last_value()
    assert values[6] == 10  # Počet vlastněných kusů
    assert values[2] == pytest.approx(1500.0)  # Aktuální tržní hodnota

# Prověřuje klíčovou FIFO logiku pro výpočet realizovaného zisku a Break Evenu
@patch('pandas.DataFrame.to_csv')
@patch('Asset.YfinanceManager.get_history')
@patch('Asset.YfinanceManager.get_info')
def test_fifo_logic_realized_profit(mock_get_info, mock_get_history, mock_to_csv, mock_portfolio):
    # Nastavení simulovaných historických dat
    mock_get_info.return_value = {"longName": "Test Stock", "currency": "USD"}
    history_df = create_mock_history(start_date='2023-01-01', days=100, start_price=100.0)
    mock_get_history.return_value = history_df

    # Sekvence nákupů a následný částečný prodej (pro ověření FIFO fronty)
    ticker = "TEST"
    mock_portfolio.new_transaction(TransactionType.LONG, datetime(2023, 1, 10), ticker, amount=10, price=100.0)
    mock_portfolio.new_transaction(TransactionType.LONG, datetime(2023, 1, 15), ticker, amount=10, price=200.0)
    mock_portfolio.new_transaction(TransactionType.LONG, datetime(2023, 1, 20), ticker, amount=-5, price=300.0)

    # Spuštění výpočtu pozice v měně USD
    mock_portfolio.get_position(ticker).get_position("USD")
    values = mock_portfolio.get_position(ticker).get_last_value()

    # Ověření: Zbývá 15 ks, realizovaný zisk 1000 a průměrná cena BEP 166.67
    assert values[6] == 15
    assert values[9] == pytest.approx(1000.0)
    assert values[5] == pytest.approx(166.666, rel=1e-3)

# Testuje automatický výpočet množství kusů při nákupu za fixní obnos (zlomky)
@patch('pandas.DataFrame.to_csv')
@patch('Asset.YfinanceManager.get_history')
@patch('Asset.YfinanceManager.get_info')
def test_fractional_shares(mock_get_info, mock_get_history, mock_to_csv, mock_portfolio):
    # Simulace historie s konstantní cenou 50 EUR
    mock_get_info.return_value = {"longName": "ETF World", "currency": "EUR"}
    history_df = create_mock_history(start_date='2023-01-01', days=20, start_price=50.0)
    mock_get_history.return_value = history_df

    # Investice 1000 EUR při ceně 50 EUR/ks -> mělo by vzniknout 20 kusů
    mock_portfolio.new_transaction(
        transaction_type=TransactionType.FRACTION_LONG,
        date=datetime(2023, 1, 10),
        ticker="VWCE.DE",
        price=1000.0
    )

    # Výpočet dat pozice a kontrola množství
    mock_portfolio.get_position("VWCE.DE").get_position("EUR")
    values = mock_portfolio.get_position("VWCE.DE").get_last_value()
    assert values[6] == pytest.approx(20.0)

# ==============================================================================
# TESTY OKRAJOVÝCH STAVŮ A SPECIÁLNÍCH SCÉNÁŘŮ
# ==============================================================================

# Ověřuje, zda se pozice po úplném prodeji korektně vyčistí a lze ji znovu otevřít
@patch('pandas.DataFrame.to_csv')
@patch('Asset.YfinanceManager.get_history')
@patch('Asset.YfinanceManager.get_info')
def test_full_closure_and_reopen(mock_get_info, mock_get_history, mock_to_csv, mock_portfolio):
    mock_get_info.return_value = {"longName": "Test Stock", "currency": "USD"}
    mock_get_history.return_value = create_mock_history(start_date='2023-01-01', days=50, start_price=100.0)

    ticker = "REOPEN"
    # 1. Nákup a následný prodej celého objemu pozice
    mock_portfolio.new_transaction(TransactionType.LONG, datetime(2023, 1, 5), ticker, amount=10, price=100.0)
    mock_portfolio.new_transaction(TransactionType.LONG, datetime(2023, 1, 10), ticker, amount=-10, price=150.0)

    # 2. Nová investice do stejného aktiva po určité době
    mock_portfolio.new_transaction(TransactionType.LONG, datetime(2023, 1, 15), ticker, amount=5, price=200.0)

    # Výpočet hodnot a ověření kontinuity profitu
    pos = mock_portfolio.get_position(ticker)
    pos.get_position("USD")
    values = pos.get_last_value()

    # Množství musí odpovídat poslední transakci, realizovaný zisk musí obsahovat první prodej
    assert values[6] == 5
    assert values[9] >= 500.0

# Prověřuje mechanismus ochrany, který brání prodeji většího množství kusů, než je vlastněno
@patch('pandas.DataFrame.to_csv')
@patch('Asset.YfinanceManager.get_history')
@patch('Asset.YfinanceManager.get_info')
def test_overselling_protection(mock_get_info, mock_get_history, mock_to_csv, mock_portfolio):
    mock_get_info.return_value = {"longName": "Short Protection", "currency": "USD"}
    mock_get_history.return_value = create_mock_history(days=20)

    ticker = "NOSHORT"
    # Nákup 10 kusů, ale pokus o prodej 15 kusů
    mock_portfolio.new_transaction(TransactionType.LONG, datetime(2023, 1, 5), ticker, amount=10, price=100.0)
    mock_portfolio.new_transaction(TransactionType.LONG, datetime(2023, 1, 10), ticker, amount=-15, price=110.0)

    pos = mock_portfolio.get_position(ticker)
    pos.get_position("USD")
    values = pos.get_last_value()

    # Systém by měl omezit prodej na maximálně držené množství (výsledek 0)
    assert values[6] == 0

# Ověřuje správnost matematického přepočtu pozice mezi různými měnami (Forex)
@patch('Position.forex_creator')
@patch('pandas.DataFrame.to_csv')
@patch('Asset.YfinanceManager.get_history')
@patch('Asset.YfinanceManager.get_info')
def test_currency_conversion(mock_get_info, mock_get_history, mock_to_csv, mock_forex, mock_portfolio):
    # Portfolio vedeme v EUR, ale nákup proběhne v USD
    mock_portfolio.change_currency("EUR")
    mock_get_info.return_value = {"longName": "US Stock", "currency": "USD"}
    mock_get_history.return_value = create_mock_history(days=10, start_price=100.0)

    # Nastavení simulovaného směnného kurzu (Forex): 1 USD = 0.9 EUR
    mock_fx_obj = MagicMock()
    mock_fx_obj.get_rate.return_value = 0.9
    mock_fx_obj.get_prices.return_value = pd.DataFrame(
        {'Close': [0.9] * 10},
        index=pd.date_range('2023-01-01', periods=10, freq='D').date
    )
    mock_forex.return_value = mock_fx_obj

    # Provedení transakce v USD
    mock_portfolio.new_transaction(
        TransactionType.LONG, datetime(2023, 1, 1), "US_ASSET", amount=10, price=100.0, currency="USD"
    )

    # Přepočet nákupní základny v EUR: $$Base_{EUR} = Amount \cdot Price_{USD} \cdot Rate_{EUR/USD}$$
    pos = mock_portfolio.get_position("US_ASSET")
    pos_data = pos.get_position("EUR")

    assert pos_data["Base"].iloc[-1] == pytest.approx(900.0)