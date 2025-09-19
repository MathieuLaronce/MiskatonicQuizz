import pandas as pd
import json

questions_path = "./data/questions.csv"
output_csv = "./data/questions_clean.csv"
output_json = "./data/quiz.json"

def run_etl():
    """Charge le CSV, nettoie, normalise et transforme en format long sans perdre de questions."""
    
    # Charger le fichier
    df = pd.read_csv(questions_path)
    print(f"✅ Fichier chargé : {questions_path} ({len(df)} lignes)")

    # Colonnes réponses (A, B, C, D…)
    response_cols = [col for col in df.columns if col.lower().startswith("response")]

    # Nettoyage basique : lignes vides
    df = df.dropna(subset=["correct", "question"])
    df = df[df["question"].str.strip() != ""]
    print(f"📌 Lignes après suppression des lignes vides : {len(df)}")

    # Normalisation des questions pour comparaison (mais garder l'original)
    df["question_norm"] = (
        df["question"]
        .str.strip()
        .str.lower()
        .str.replace(r"[?:]+$", "", regex=True)
    )

    # Normalisation des réponses (texte)
    for col in response_cols:
        df[col] = df[col].fillna("").astype(str).str.strip()
        df[col] = df[col].apply(lambda x: [x] if x else [])

    # Normalisation des bonnes réponses (A, B, C, D)
    df["correct"] = (
        df["correct"]
        .astype(str)
        .apply(lambda x: ",".join(sorted({c.strip().upper() for c in x.split(",") if c.strip()})))
    )

    # Regroupement par question normalisée
    df_grouped = (
        df.groupby("question_norm")
        .agg({
            "question": "first",
            "subject": "first",  # ✅ garder le sujet
            "use": "first",      # ✅ garder l'usage
            "remark": "first",   # ✅ garder le commentaire
            **{col: lambda s: [item for sublist in s for item in sublist] for col in response_cols},
            "correct": lambda x: ",".join(sorted(set(",".join(x).split(","))))
        })
        .reset_index(drop=True)
    )
    print(f"📌 Lignes après regroupement logique : {len(df_grouped)}")

    # Construire possible_answers (sans doublons)
    df_grouped["possible_answers"] = df_grouped[response_cols].apply(
        lambda x: list(dict.fromkeys(i.strip() for lst in x for i in lst if i.strip() != "")),
        axis=1
    )

    # Construire correct_answers texte
    def get_correct_answers(row):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        mapping = {letters[i]: ans for i, ans in enumerate(row["possible_answers"])}
        correct_letters = str(row["correct"]).split(",")
        return [mapping[l] for l in correct_letters if l in mapping]

    df_grouped["correct_answers"] = df_grouped.apply(get_correct_answers, axis=1)

    # Format final long avec subject, use et remark
    df_long = df_grouped[["question", "subject", "use", "possible_answers", "correct_answers"]]
    print(f"📌 Transformation en format long terminée : {len(df_long)} lignes")

    # Sauvegardes
    df_long.to_csv(output_csv, index=False)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(df_long.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    print(f"✅ Sauvegardé : {output_csv} et {output_json}")
    return df_long

if __name__ == "__main__":
    df_long = run_etl()
    print("📌 Aperçu du DataFrame final :")
    print(df_long.head())
