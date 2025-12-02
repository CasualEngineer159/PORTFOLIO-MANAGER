import pandas as pd

from Portfolio import *

#omx = asset_creator("IE00BD3RYZ16.AS")

portfolio = Portfolio("LongFraction", "EUR")
portfolio2 = Portfolio("Long", "EUR")
degiro_portfolio = Portfolio("Degiro", "EUR")
degiro_portfolio_2 = Portfolio("Degiro LONG WHOLE", "EUR")

#for i in range(15,24):
#    for j in range(1,13):
#        print(asset_creator("AAPL"))
#        portfolio.new_transaction(
#            transaction_type=TransactionType.FRACTION_LONG,
#            date=datetime(2000+i,j,1),
#            asset=asset_creator("AAPL"),
#            price=150,  # Zde použijeme vypočtenou hodnotu
#            #currency="CZK"
#        )

file_path = f'DATA/Transactions.csv'

degiro_transactions = pd.read_csv(
    file_path,
    decimal=','
)
degiro_transactions['Datetime'] = degiro_transactions['Datum'].astype(str) + ' ' + degiro_transactions['Čas'].astype(str)

degiro_transactions['Datetime'] = pd.to_datetime(
    degiro_transactions['Datetime'],
    format='%d-%m-%Y %H:%M'
)

degiro_transactions = degiro_transactions.set_index('Datetime').drop(columns=['Datum', 'Čas'])

degiro_transactions.rename(columns={"Směnný kurz": "kurz",
                                    "Unnamed: 8": "Měna"
                                    },
                           inplace=True)

degiro_transactions["kurz"] = degiro_transactions["kurz"].fillna(1.0)

degiro_transactions = degiro_transactions.sort_index()

# Iterace
for row in degiro_transactions.itertuples():

    datum = row.Index
    ticker = row.ISIN
    price = row.Cena
    amount = row.Počet
    total_price = price * amount
    currency = row.Měna

    """degiro_portfolio.new_transaction(
        transaction_type=TransactionType.FRACTION_LONG,
        date=datum,
        asset=asset_creator(ticker),
        price=total_price,  # Zde použijeme vypočtenou hodnotu
        currency=currency
    )"""

    degiro_portfolio_2.new_transaction(
        transaction_type=TransactionType.LONG,
        date=datum,
        asset=asset_creator(ticker),
        amount=amount,
        price=price,
        currency=currency
    )

#degiro_portfolio.get_portfolio()

#degiro_portfolio.print_portfolio_positions()

degiro_portfolio_2.get_portfolio()

degiro_portfolio_2.print_portfolio_positions()

