from Portfolio import *

test_portfolio = Portfolio("Test", "EUR")

test_portfolio.new_transaction(TransactionType.LONG, datetime(2010,12,12),"VUSA.AS",amount=3)
test_portfolio.new_transaction(TransactionType.LONG, datetime(2012,12,12),"VUSA.AS",amount=-3)
test_portfolio.new_transaction(TransactionType.LONG, datetime(2008,12,12),"VUSA.AS",amount=2)
test_portfolio.new_transaction(TransactionType.LONG, datetime(2005,12,12),"VUSA.AS",amount=3)
test_portfolio.new_transaction(TransactionType.FRACTION_LONG, datetime(2023,12,12),"VUSA.AS",price=-100)
test_portfolio.new_transaction(TransactionType.FRACTION_LONG, datetime(2024,12,12),"VUSA.AS",price=100)
test_portfolio.new_transaction(TransactionType.LONG, datetime(2025,12,12),"VUSA.AS",amount=-1)

test_portfolio.get_portfolio()

test_portfolio.export_portfolio_to_pdf()

test_portfolio2 = Portfolio("Test2", "EUR")

test_portfolio2.new_transaction(TransactionType.LONG, datetime(2010,12,12),"VUSA.AS",amount=3)
test_portfolio2.new_transaction(TransactionType.LONG, datetime(2012,12,12),"VUSA.AS",amount=-3)
test_portfolio2.new_transaction(TransactionType.LONG, datetime(2008,12,12),"VUSA.AS",amount=2)
test_portfolio2.new_transaction(TransactionType.LONG, datetime(2005,12,12),"VUSA.AS",amount=3)
test_portfolio2.new_transaction(TransactionType.FRACTION_LONG, datetime(2023,12,12),"VUSA.AS",price=-100)
test_portfolio2.new_transaction(TransactionType.FRACTION_LONG, datetime(2024,12,12),"VUSA.AS",price=100)
test_portfolio2.new_transaction(TransactionType.LONG, datetime(2025,12,12),"VUSA.AS",amount=-5)

test_portfolio2.get_portfolio()

test_portfolio2.export_portfolio_to_pdf()

# test_portfolio.get_position("VUSA.AS")._calculate_bz()