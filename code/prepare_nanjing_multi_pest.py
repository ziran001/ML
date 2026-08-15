"""Extract all Nanjing pheromone-trap workbooks into a weekly multi-pest table."""

from __future__ import annotations

import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd


PEST_CODES = {
    "稻纵卷叶螟": "RLF",   # rice leaf folder
    "二化螟": "SSB",       # striped stem borer
    "大螟": "PSB",         # pink stem borer
    "斜纹夜蛾": "TCW",     # tobacco cutworm
    "甜菜夜蛾": "BAW",     # beet armyworm
    "杨小舟蛾": "PSP",     # poplar small prominent
    "美国白蛾": "FWW",     # fall webworm
}
WEATHER = ["MaxT", "MinT", "RH1", "RH2", "RF", "WS", "SSH", "EVP"]


def infer_species(value, alias: str, sheet: str) -> str:
    if pd.notna(value) and str(value).strip():
        return str(value).strip()
    text = f"{alias}{sheet}"
    for species in PEST_CODES:
        if species in text or (species == "稻纵卷叶螟" and "稻纵" in text):
            return species
    return "未标注"


def read_sheet(path: str, sheet: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    alias = str(raw.iloc[1, 0])
    species = infer_species(raw.iloc[3, 2], alias, sheet)
    body = raw.iloc[6:, :4].copy()
    body.columns = ["Date", "PestCount", "TrapTemperature", "TrapHumidity"]
    body["Date"] = pd.to_datetime(body["Date"], errors="coerce")
    for col in ["PestCount", "TrapTemperature", "TrapHumidity"]:
        body[col] = pd.to_numeric(body[col], errors="coerce")
    body = body.dropna(subset=["Date", "PestCount"])
    body["Location"] = sheet
    body["GatewayAlias"] = alias
    body["Region"] = str(raw.iloc[1, 2])
    body["PestSpecies"] = species
    body["PestCode"] = PEST_CODES.get(species, "UNK")
    return body


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--xls-dir", type=Path, required=True)
    p.add_argument("--weather-source", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("data/nanjing_multi_pest_weekly.csv"))
    args = p.parse_args()

    parts = []
    for path in glob.glob(str(args.xls_dir / "**" / "*.xls"), recursive=True):
        for sheet in pd.ExcelFile(path).sheet_names:
            parts.append(read_sheet(path, sheet))
    daily = pd.concat(parts, ignore_index=True)
    daily = daily[daily["PestSpecies"].isin(PEST_CODES)].copy()
    # The consolidated workbook overlaps the two RLF-only exports. Keep one daily
    # observation per real gateway/date so the same trap is never counted twice.
    daily = daily.drop_duplicates(["PestSpecies", "GatewayAlias", "Region", "Date"], keep="last")
    daily["week_start"] = daily["Date"] - pd.to_timedelta((daily["Date"].dt.dayofweek + 1) % 7, unit="D")
    weekly = daily.groupby(
        ["PestSpecies", "PestCode", "Location", "GatewayAlias", "Region", "week_start"],
        as_index=False,
    ).agg(
        observed_days=("Date", "nunique"), PestCount=("PestCount", "sum"),
        TrapTemperature=("TrapTemperature", "mean"), TrapHumidity=("TrapHumidity", "mean"),
    )

    weather = pd.read_csv(args.weather_source)
    for col in WEATHER:
        weather[col] = pd.to_numeric(weather[col], errors="coerce")
    iso = weekly["week_start"].dt.isocalendar()
    weekly["Year"], weekly["Week"] = iso.year.astype(int), iso.week.astype(int)
    weather = weather.groupby(["Year", "Week"], as_index=False)[WEATHER].median()
    weekly = weekly.merge(weather, on=["Year", "Week"], how="left", validate="many_to_one")
    weekly = weekly.sort_values(["PestCode", "Location", "week_start"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    weekly.to_csv(args.output, index=False, encoding="utf-8-sig")
    summary = weekly.groupby(["PestSpecies", "PestCode"]).agg(
        stations=("Location", "nunique"), weeks=("week_start", "nunique"),
        rows=("PestCount", "size"), total_count=("PestCount", "sum")
    )
    summary.to_csv(args.output.with_name("nanjing_pest_inventory.csv"), encoding="utf-8-sig")
    print(summary.to_string())


if __name__ == "__main__":
    main()

