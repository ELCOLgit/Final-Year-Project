from pathlib import Path

import pandas as pd


# get the csv file path
data_file = Path(__file__).resolve().parent.parent / "data" / "postings.csv"

# load only the first 100 rows for testing
df = pd.read_csv(data_file, nrows=100)

# print the column names first to inspect the dataset structure
print("column names:")
print(list(df.columns))

# remove rows where title or description is missing
df = df.dropna(subset=["title", "description"])

# show a small summary after cleaning
print()
print(f"rows loaded after cleaning: {len(df)}")
print(df[["title", "description"]].head())
