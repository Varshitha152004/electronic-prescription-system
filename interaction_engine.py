import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data")

drugs_df = pd.read_csv(os.path.join(DATA_PATH, "drugs_master.csv"))
interactions_df = pd.read_csv(os.path.join(DATA_PATH, "interactions_master.csv"))

# Normalize everything to uppercase
drugs_df["drug_name"] = drugs_df["drug_name"].str.upper().str.strip()

drug_name_to_id = dict(zip(drugs_df["drug_name"], drugs_df["drug_id"]))
drug_id_to_name = dict(zip(drugs_df["drug_id"], drugs_df["drug_name"]))

interaction_lookup = {}

for _, row in interactions_df.iterrows():
    key = tuple(sorted([row["drug_a_id"], row["drug_b_id"]]))
    interaction_lookup[key] = {
        "severity": row["severity"],
        "mechanism": row["mechanism"],
        "effect": row["effect"],
        "safer_alternative": row["Safer_alternative"],
        "rationale": row["rationale"]
    }


def check_interactions(drug_list):

    results = []
    unknown_drugs = []

    drug_ids = []

    for drug in drug_list:
        drug = drug.upper().strip()
        if drug in drug_name_to_id:
            drug_ids.append(drug_name_to_id[drug])
        else:
            unknown_drugs.append(drug)

    if len(drug_ids) < 2:
        return {
            "interactions": [],
            "unknown_drugs": unknown_drugs
        }

    for i in range(len(drug_ids)):
        for j in range(i + 1, len(drug_ids)):

            pair = tuple(sorted([drug_ids[i], drug_ids[j]]))

            if pair in interaction_lookup:
                interaction = interaction_lookup[pair]

                results.append({
                    "drug_a": drug_id_to_name[pair[0]],
                    "drug_b": drug_id_to_name[pair[1]],
                    "severity": interaction["severity"],
                    "mechanism": interaction["mechanism"],
                    "effect": interaction["effect"],
                    "safer_alternative": interaction["safer_alternative"],
                    "rationale": interaction["rationale"]
                })

    return {
        "interactions": results,
        "unknown_drugs": unknown_drugs
    }
