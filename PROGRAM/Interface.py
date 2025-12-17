from Portfolio import *

portfolio = Portfolio("LongFraction", "EUR")
portfolio2 = Portfolio("Long", "EUR")
degiro_portfolio = Portfolio("Degiro", "EUR")
degiro_portfolio_2 = Portfolio("Degiro LONG WHOLE", "EUR")

file_path = f'../DATA/PERSONAL/Transactions.csv'

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
    exchange = row.Reference


    degiro_portfolio_2.new_transaction(
        transaction_type=TransactionType.LONG,
        date=datum,
        ticker=ticker,
        amount=amount,
        price=price,
        currency=currency,
        venue=exchange
    )

# degiro_portfolio_2.new_transaction(TransactionType.LONG,datetime(2021,4,28),"GC=F","CZK",1)

degiro_portfolio_2.get_portfolio()

degiro_portfolio_2.export_portfolio_to_pdf()
