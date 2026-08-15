"""Train one next-week regressor per pest and output normalized pest weights."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor, StackingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.tree import DecisionTreeRegressor


WEATHER = ["MaxT", "MinT", "RH1", "RH2", "RF", "WS", "SSH", "EVP"]
FEATURES = ["Year", "Week", *WEATHER, "PestCount", "PestCount_lag1", "PestCount_lag2", "PestCount_lag3",
            "PestCount_roll3_mean", "PestCount_roll3_max", "PestCount_roll6_mean", "PestCount_roll6_max",
            *[x for c in WEATHER for x in (f"{c}_lag1", f"{c}_roll3_mean")]]


def make_features(observed: pd.DataFrame, horizon: int) -> pd.DataFrame:
    generated = []
    for (code, location), part in observed.groupby(["PestCode", "Location"], sort=False):
        part = part.sort_values("week_start").set_index("week_start")
        grid = part.reindex(pd.date_range(part.index.min(), part.index.max(), freq="W-SUN"))
        grid.index.name = "week_start"; grid["PestCode"] = code; grid["Location"] = location
        for lag in (1, 2, 3): grid[f"PestCount_lag{lag}"] = grid["PestCount"].shift(lag)
        for window in (3, 6):
            roll = grid["PestCount"].shift(1).rolling(window, min_periods=1)
            grid[f"PestCount_roll{window}_mean"] = roll.mean(); grid[f"PestCount_roll{window}_max"] = roll.max()
        for col in WEATHER:
            grid[f"{col}_lag1"] = grid[col].shift(1)
            grid[f"{col}_roll3_mean"] = grid[col].shift(1).rolling(3, min_periods=1).mean()
        grid["Target_next"] = grid["PestCount"].shift(-horizon)
        grid["target_date"] = grid.index + pd.Timedelta(weeks=horizon)
        generated.append(grid.reset_index())
    return pd.concat(generated, ignore_index=True).dropna(subset=["PestCount", "Target_next"])


def candidates(seed: int):
    def pipe(model): return make_pipeline(SimpleImputer(strategy="median"), model)
    rf = pipe(RandomForestRegressor(n_estimators=400, min_samples_leaf=2, n_jobs=-1, random_state=seed))
    et = pipe(ExtraTreesRegressor(n_estimators=400, min_samples_leaf=2, n_jobs=-1, random_state=seed))
    gb = pipe(HistGradientBoostingRegressor(max_iter=300, learning_rate=.05, max_leaf_nodes=15, random_state=seed))
    stack = StackingRegressor([("GB", gb), ("RF", rf), ("ET", et)],
        final_estimator=DecisionTreeRegressor(max_depth=4, min_samples_leaf=5, random_state=seed), cv=5, n_jobs=-1)
    base = {"RandomForest": rf, "ExtraTrees": et, "GradientBoosting": gb, "Stacking": stack}
    try:
        from xgboost import XGBRegressor
        base["XGBoost"] = pipe(XGBRegressor(n_estimators=500, max_depth=5, learning_rate=.04,
            subsample=.8, colsample_bytree=.8, objective="reg:squarederror", n_jobs=-1, random_state=seed))
    except ImportError: pass
    try:
        from lightgbm import LGBMRegressor
        base["LightGBM"] = pipe(LGBMRegressor(n_estimators=500, learning_rate=.04, num_leaves=20,
            verbosity=-1, n_jobs=-1, random_state=seed))
    except ImportError: pass
    try:
        from catboost import CatBoostRegressor
        base["CatBoost"] = pipe(CatBoostRegressor(iterations=500, depth=6, learning_rate=.04,
            verbose=False, random_seed=seed))
    except ImportError: pass
    return {k: TransformedTargetRegressor(regressor=v, func=np.log1p, inverse_func=np.expm1, check_inverse=False)
            for k, v in base.items()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True); p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--pests", nargs="*", help="Three or more PestCode values; omit to train all")
    p.add_argument("--test-year", type=int, default=2024); p.add_argument("--horizon", type=int, default=1)
    p.add_argument("--seed", type=int, default=42); args = p.parse_args(); args.out_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(args.input); raw["week_start"] = pd.to_datetime(raw["week_start"])
    if args.pests: raw = raw[raw.PestCode.isin(args.pests)]
    data = make_features(raw, args.horizon); all_metrics=[]; all_predictions=[]
    for code, pest in data.groupby("PestCode"):
        train=pest[pest.target_date.dt.year < args.test_year]; test=pest[pest.target_date.dt.year == args.test_year]
        if len(train) < 30 or len(test) < 10: print(f"skip {code}: train={len(train)}, test={len(test)}"); continue
        best=None
        for name, model in candidates(args.seed).items():
            model.fit(train[FEATURES], train.Target_next); pred=np.maximum(0, model.predict(test[FEATURES]))
            row={"PestCode":code,"model":name,"train_n":len(train),"test_n":len(test),
                 "R2":r2_score(test.Target_next,pred),"RMSE":mean_squared_error(test.Target_next,pred)**.5,
                 "MAE":mean_absolute_error(test.Target_next,pred)}; all_metrics.append(row)
            if best is None or row["RMSE"] < best[0]: best=(row["RMSE"],name,model,pred)
        _,name,model,pred=best; joblib.dump(model,args.out_dir/f"model_{code}_{name}.joblib")
        out=test[["PestSpecies","PestCode","Location","week_start","target_date","Target_next"]].copy()
        out["BestModel"]=name; out["Prediction"]=pred; all_predictions.append(out)
    metrics=pd.DataFrame(all_metrics); predictions=pd.concat(all_predictions,ignore_index=True)
    # The requested weights are shares of predicted abundance for each target week.
    totals=predictions.groupby(["target_date","PestCode"],as_index=False).Prediction.sum()
    totals["PredictionWeight"]=totals.Prediction/totals.groupby("target_date").Prediction.transform("sum").replace(0,np.nan)
    metrics.to_csv(args.out_dir/"model_metrics.csv",index=False,encoding="utf-8-sig")
    predictions.to_csv(args.out_dir/"predictions_by_station.csv",index=False,encoding="utf-8-sig")
    totals.to_csv(args.out_dir/"pest_prediction_weights.csv",index=False,encoding="utf-8-sig")
    (args.out_dir/"feature_names.json").write_text(json.dumps(FEATURES,ensure_ascii=False,indent=2),encoding="utf8")
    print(metrics.sort_values(["PestCode","RMSE"]).groupby("PestCode").head(1).to_string(index=False))


if __name__ == "__main__": main()

