import pandas as pd

from Portfolio import *

apple = Stock('AAPL')
snp = ETF("VUSA.AS")

portfolio = Portfolio("LongFraction", "EUR")
portfolio2 = Portfolio("Long", "EUR")
degiro_portfolio = Portfolio("Degiro", "EUR")

for i in range(15,24):
    for j in range(1,13):
        print(asset_creator("AAPL"))
        portfolio.new_transaction(
            transaction_type=TransactionType.FRACTION_LONG,
            date=datetime(2000+i,j,1),
            asset=asset_creator("AAPL"),
            price=150,  # Zde použijeme vypočtenou hodnotu
            #currency="CZK"
        )


portfolio.get_portfolio(True)
#portfolio2.get_portfolio(True)

file_path = f'DATA/Transactions.csv'

degiro_transactions = pd.read_csv(
    file_path,
    decimal=','
)

# 2. Vytvořte nový sloupec spojením stringů Datum a Čas
degiro_transactions['Datetime'] = degiro_transactions['Datum'].astype(str) + ' ' + degiro_transactions['Čas'].astype(str)

# 3. Převeďte na datetime (včetně času)
degiro_transactions['Datetime'] = pd.to_datetime(
    degiro_transactions['Datetime'],
    format='%d-%m-%Y %H:%M'
)

# Nastavte Datetime jako index
degiro_transactions = degiro_transactions.set_index('Datetime').drop(columns=['Datum', 'Čas'])

#print(degiro_transactions.index)
#print(degiro_transactions["ISIN"])
#print(degiro_transactions["Počet"])
# 1. Správné přejmenování sloupce v DataFrame
degiro_transactions.rename(columns={"Směnný kurz": "kurz",
                                    "Unnamed: 8": "Měna"
                                    },
                           inplace=True)

# 2. DŮLEŽITÉ: Pokud je kurz prázdný (např. pro EUR transakce), doplň 1.0
degiro_transactions["kurz"] = degiro_transactions["kurz"].fillna(1.0)

degiro_transactions = degiro_transactions.sort_index()

print(degiro_transactions)

# Iterace
for row in degiro_transactions.itertuples():
    datum = row.Index # Nebo row[0], itertuples dává index do atributu .Index
    isin_kod = row.ISIN

    # Výpočet ceny v domácí měně
    # Předpokládám, že 'Cena' i 'kurz' jsou už čísla (float).
    # Pokud ne, musíš je převést (viz předchozí rady o decimal=',')
    total_price = abs(row.Cena) * row.Počet

    print(f"Index: {datum}, Produkt: {row.Produkt}, Cena: {total_price}, Počet: {row.Počet} ")

    degiro_portfolio.new_transaction(
        transaction_type=TransactionType.FRACTION_LONG,
        date=datum,
        asset=asset_creator(isin_kod),
        price=total_price,  # Zde použijeme vypočtenou hodnotu
        currency=row.Měna
    )

#print(degiro_transactions)

degiro_portfolio.get_portfolio(True)

forex = forex_creator("EUR", "CZK")
date=datetime(2024,3,5)
rate = forex.get_rate(date.date())
print(rate)


