from Portfolio import *

portfolio = Portfolio("TEST","EUR")

portfolio.new_transaction(transaction_type=TransactionType.LONG,
                          date=datetime(2010,10,10),
                          ticker="VUSA.AS",
                          amount=2)

portfolio.new_transaction(transaction_type=TransactionType.LONG,
                          date=datetime(2020,10,10),
                          ticker="VUSA.AS",
                          amount=-1)

portfolio.get_portfolio()
portfolio.export_portfolio_to_pdf()