import argparse
import os
import pickle
from pathlib import Path

import numpy as np


FEATURE_COLUMNS = [
    "diff_std",
    "diff_stripe",
    "diff_vignette",
    "diff_mean_abs",
    "diff_p95",
    "raw_mean",
    "raw_std",
    "raw_p1",
    "raw_p99",
]


def load_csv(path):
    import csv

    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
    return rows


def split_by_pair(rows, test_ratio=0.2, seed=13):
    rng = np.random.default_rng(seed)
    pairs = sorted({row["pair"] for row in rows})
    rng.shuffle(pairs)
    split = int(len(pairs) * (1 - test_ratio))
    train_pairs = set(pairs[:split])
    train_rows = [row for row in rows if row["pair"] in train_pairs]
    test_rows = [row for row in rows if row["pair"] not in train_pairs]
    return train_rows, test_rows


def build_arrays(rows):
    x = np.array([[float(row[col]) for col in FEATURE_COLUMNS] for row in rows], dtype=np.float32)
    y = np.array([int(row["label"]) for row in rows], dtype=np.int32)
    return x, y


def train_model(x_train, y_train):
    from sklearn.ensemble import RandomForestClassifier

    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced",
        n_jobs=-1,
        random_state=13,
    )
    model.fit(x_train, y_train)
    return model


def evaluate(model, x_test, y_test):
    from sklearn.metrics import classification_report, confusion_matrix

    preds = model.predict(x_test)
    report = classification_report(y_test, preds, digits=3)
    matrix = confusion_matrix(y_test, preds)
    return report, matrix


def main():
    parser = argparse.ArgumentParser(description="Train ML model for bad frame detection.")
    base_dir = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--data",
        default=str(base_dir / "data-ml" / "dataset.csv"),
        help="CSV dataset path.",
    )
    parser.add_argument(
        "--out",
        default=str(base_dir / "data-ml" / "model.pkl"),
        help="Output model path.",
    )
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    rows = load_csv(args.data)
    if not rows:
        print("Dataset is empty.")
        return

    train_rows, test_rows = split_by_pair(rows, test_ratio=args.test_ratio, seed=args.seed)
    x_train, y_train = build_arrays(train_rows)
    x_test, y_test = build_arrays(test_rows)

    model = train_model(x_train, y_train)
    report, matrix = evaluate(model, x_test, y_test)
    print(report)
    print("Confusion matrix:\n", matrix)

    payload = {
        "model": model,
        "features": FEATURE_COLUMNS,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "wb") as handle:
        pickle.dump(payload, handle)
    print(f"Saved model to {args.out}")


if __name__ == "__main__":
    main()
