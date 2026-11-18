import pandas as pd

df = pd.read_csv("data/literature_reference.csv", encoding="utf-8-sig")

targets = {
    "0.05C capacity": ("Discharge_Capacity_0_05C_mAh_g", 10, 220),
    "0.1C capacity": ("Discharge_Capacity_0_1C_mAh_g", 10, 220),
    "1C capacity": ("Discharge_Capacity_1C_mAh_g", 10, 220),
    "5C capacity": ("Discharge_Capacity_5C_mAh_g", 5, 220),
    "Capacity retention": ("Capacity_Retention_percent", 10, 110),
    "Initial coulombic efficiency": (
        "Initial_Coulombic_Efficiency_percent", 50, 100
    ),
}

print("Total records:", len(df))
print("Unique papers:", df["Paper_ID"].nunique())
print("Duplicate Sample_IDs:", df["Sample_ID"].duplicated().sum())
print("\nUsable samples and distinct papers per target:")

for name, (column, minimum, maximum) in targets.items():
    values = pd.to_numeric(df[column], errors="coerce")
    valid = values.between(minimum, maximum)
    usable = df.loc[valid]
    print(
        f"{name}: {len(usable)} samples, "
        f"{usable['Paper_ID'].nunique()} papers"
    )
