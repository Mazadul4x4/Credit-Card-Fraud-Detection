import os
import pandas as pd
import numpy as np

RAW_DATA = "data/raw_data/creditcard.csv"
BAD_DATA = "data/bad_data"

os.makedirs(BAD_DATA, exist_ok=True)

df = pd.read_csv(RAW_DATA)

bad_df = df.copy()

# Introduce missing values
bad_df.loc[0:50, "Amount"] = np.nan

# Introduce invalid numeric values instead of strings
bad_df.loc[51:100, "Time"] = -99999

# Duplicate some rows
bad_df = pd.concat([bad_df, bad_df.iloc[:10]], ignore_index=True)

bad_df.to_csv(f"{BAD_DATA}/bad_creditcard.csv", index=False)

print("Bad dataset generated successfully.")
print("Shape:", bad_df.shape)