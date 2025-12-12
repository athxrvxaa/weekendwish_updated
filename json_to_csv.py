import pandas as pd
import json

# Load JSON
with open("pune_clean.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Convert to DataFrame (automatically expands nested dictionaries)
df = pd.json_normalize(data)

# Save to CSV
df.to_csv("pune_clean.csv", index=False, encoding="utf-8")
