import pandas as pd
from datetime import datetime

print("--- 1. PŘÍPRAVA DAT ---")
# Vytvoříme data jen pro obchodní dny (vynecháme 1.1. jako svátek a 4.1.-5.1. jako víkend)
dates = [
    datetime(2019, 12, 31),  # Úterý
    datetime(2020, 1, 2),  # Čtvrtek (1.1. burza zavřená)
    datetime(2020, 1, 3),  # Pátek
    datetime(2020, 1, 6)  # Pondělí (4. a 5. byl víkend)
]

# Vytvoření DataFrame
df = pd.DataFrame({
    'Low': [148.0, 150.0, 155.0, 152.0],
    'High': [155.0, 158.0, 160.0, 159.0]
}, index=dates)

# Ujistíme se, že index je seřazený (nutné pro asof/ffill)
df = df.sort_index()
print("Data v 'daily_history':")
print(df)
print("-" * 30)

date = datetime(2020, 1, 1)
print(f"date = {date}")
nearest_row = df.index.asof(date)
print(nearest_row)

