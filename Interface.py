from Portfolio import *

apple = Stock('AAPL')
snp = ETF("VUSA.AS")

portfolio = Portfolio("test", "EUR")

for i in range(0, 25):
    for j in range(1, 12):
        portfolio.new_transaction(1, datetime(2000+i,j,1), snp)
#portfolio.new_transaction(1, datetime(2020,11,15), snp)
#portfolio.new_transaction(1, datetime(2020,11,20), snp)
#portfolio.new_transaction(1, datetime(2020,11,25), snp)
#print(portfolio._position_dict)

#print(portfolio._position_dict[snp]._transaction_list[1].get_transaction())
#print(portfolio._position_dict[snp].get_position("EUR"))

#portfolio.get_portfolio()
portfolio.get_portfolio(True)

#portfolio.change_currency("CZK")

#portfolio.get_portfolio()