"""Load trained pest models and predict the week after the newest observation."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from train_nanjing_multi_pest import FEATURES, make_features


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True, help="Weekly CSV produced by prepare script")
    p.add_argument("--model-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("outputs/latest_pest_weights.csv"))
    p.add_argument("--pests", nargs="*", help="PestCode values; omit to use every model in model-dir")
    p.add_argument("--horizon", type=int, default=1)
    args = p.parse_args()

    raw = pd.read_csv(args.input)
    raw["week_start"] = pd.to_datetime(raw["week_start"])
    if args.pests:
        raw = raw[raw["PestCode"].isin(args.pests)]
    featured = make_features(raw, args.horizon, require_target=False)
    predictions = []
    for code, pest in featured.groupby("PestCode"):
        matches = sorted(args.model_dir.glob(f"model_{code}_*.joblib"))
        if not matches:
            print(f"skip {code}: no model file")
            continue
        if len(matches) > 1:
            raise ValueError(f"Multiple models found for {code}: {matches}")
        latest_date = pest["week_start"].max()
        latest = pest[pest["week_start"] == latest_date].copy()
        model = joblib.load(matches[0])
        latest["Prediction"] = np.maximum(0, model.predict(latest[FEATURES]))
        predictions.append(latest[["PestSpecies", "PestCode", "Location", "week_start", "target_date", "Prediction"]])
    if not predictions:
        raise ValueError("No matching pest model could be used")
    station = pd.concat(predictions, ignore_index=True)
    totals = station.groupby(["target_date", "PestCode"], as_index=False).Prediction.sum()
    denominator = totals.groupby("target_date").Prediction.transform("sum")
    totals["PredictionWeight"] = totals.Prediction / denominator.replace(0, np.nan)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    totals.to_csv(args.output, index=False, encoding="utf-8-sig")
    station.to_csv(args.output.with_name(args.output.stem + "_by_station.csv"), index=False, encoding="utf-8-sig")
    print(totals.to_string(index=False))


if __name__ == "__main__":
    main()

