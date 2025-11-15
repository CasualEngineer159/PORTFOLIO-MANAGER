from Asset import *

snp = ETF("VUSA.AS")
apple = Stock("US67066G1040")
bitcoin = Crypto("BTC-USD")
gold = Commodity("XAUUSD")
gold_futures = Futures("GC=F")

class Position:
    def __init__(self, Asset, nakupni_cena, datum_nakupu, datum_prodeje, pocet_kusu):
        self.Asset = Asset
        self.nakupni_cena = nakupni_cena
        self.datum_nakupu = datum_nakupu
        self.datum_prodeje = datum_prodeje
        self.pocet_kusu = pocet_kusu
