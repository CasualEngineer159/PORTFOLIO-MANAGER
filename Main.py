import requests
import pprint as pp
import yfinance as yf
import os
import csv

class ApiManager:
    def __init__(self, ):
        pass


class Asset:
    def __init__(self, ticker):
        self.ticker = ticker
    def get_name(self) -> str:
        pass

class Stock(Asset):
    def __init__(self, ticker):
        super().__init__(ticker)


stock = yf.Ticker("VUSA.AS")
print(type(stock.ticker))

stock_history = stock.history(period="max", interval="1d")
stock_history.to_csv(f'DATA/{stock.ticker}.history.csv')
stock_info = stock.get_info()
print(type(stock_info))
pp.pprint(stock_info["currency"])

with open(f"DATA/{stock.ticker}.info.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=stock_info.keys())
    writer.writeheader()
    writer.writerow(stock_info)