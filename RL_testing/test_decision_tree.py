import joblib
import pandas as pd
import sys

# -------- CONFIG --------
MODEL_PATH = "DecisionTreeClassifier.pkl"  # trained model file
INPUT_CSV = "summary_batch_1.csv"               # default test file
OUTPUT_CSV = "predicted_output.csv"        # prediction output file
# ------------------------

def main(input_file):
    print("🔍 Loading trained model...")
    model = joblib.load(MODEL_PATH)
    print(f"✅ Model loaded: {type(model)}")

    # Load test CSV
    print(f"📂 Reading input file: {input_file}")
    df = pd.read_csv(input_file)
    print(f"📊 Original columns: {list(df.columns)}")

    # Try to match model feature names if available
    if hasattr(model, "feature_names_in_"):
        feature_cols = list(model.feature_names_in_)
        print(f"🧩 Using model feature columns: {feature_cols}")
    else:
        print("⚠️ Model does not store feature names — using numeric columns only.")
        feature_cols = df.select_dtypes(include=["number"]).columns.tolist()

    # Select only matching columns
    df_aligned = df.loc[:, df.columns.intersection(feature_cols)]

    # Warn if columns are missing
    missing = set(feature_cols) - set(df_aligned.columns)
    if missing:
        print(f"⚠️ Missing columns (filled with 0): {missing}")
        for col in missing:
            df_aligned[col] = 0

    # Ensure correct column order
    df_aligned = df_aligned[feature_cols]

    print(f"✅ Final feature shape: {df_aligned.shape}")

    # Make predictions
    print("🤖 Running predictions...")
    preds = model.predict(df_aligned)

    # Save results
    output_df = df.copy()
    output_df["Predicted_Label"] = preds
    output_df.to_csv(OUTPUT_CSV, index=False)
    print(f"💾 Predictions saved to: {OUTPUT_CSV}")

    print("\n📈 Sample predictions:")
    print(output_df[["Predicted_Label"]].head())

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else INPUT_CSV
    main(input_file)
