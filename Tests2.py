from Asset import *

def _is_on_yahoo(ticker) -> bool:
    
    yahoo_ticker = yf.Ticker(ticker)
    info = yahoo_ticker.history(period = "7d", interval = "1d")
    return info.empty
    
#print(_is_on_yahoo("NEEXISTUJICI-TICKER"))

yahoo_ticker = yf.Ticker("US67066G1040")
info = yahoo_ticker.get_info()
ticker = yahoo_ticker.ticker
print(ticker)