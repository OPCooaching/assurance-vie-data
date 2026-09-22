"""Build actual readings for proposed ChatGPT strategy families.

This output deliberately contains no performance curve. It reports today's
inputs and the resulting allocation under each pre-written rule. A live
performance history can start only on a future committed start date.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import yaml

def last_value(frame: pd.DataFrame, column: str) -> tuple[pd.Timestamp, float]:
    data = frame[["date", column]].dropna().sort_values("date")
    row = data.iloc[-1]
    return pd.Timestamp(row["date"]), float(row[column])

def asset_rows(latest: pd.DataFrame, universe: pd.DataFrame, assets: list[str]) -> list[dict]:
    names = universe.set_index("asset_id")["support_name"].to_dict()
    by_id = latest.set_index("asset_id")
    return [{"asset_id": asset, "name": names.get(asset, asset),
             "volatility_60d": round(float(by_id.loc[asset, "vol_60d_ann"]) * 100, 1),
             "return_60d": round(float(by_id.loc[asset, "ret_60d"]) * 100, 1),
             "above_sma200": bool(float(by_id.loc[asset, "sma200_ratio"]) > 0)}
            for asset in assets]

def main() -> None:
    cfg = yaml.safe_load(Path("config/chatgpt_strategy_lab.yml").read_text())
    latest = pd.read_csv("data/indicators/latest.csv")
    prices = pd.read_csv("data/prices/daily.csv", parse_dates=["date"])
    context = pd.read_csv("data/context/daily.csv", parse_dates=["date"])
    universe = pd.read_csv("config/universe.csv")
    strategies = cfg["strategies"]
    names = universe.set_index("asset_id")["support_name"].to_dict()
    output = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "strategies": []}

    risk = strategies["risk_budget"]
    rows = asset_rows(latest, universe, risk["assets"])
    inverse_vol = [1 / max(row["volatility_60d"], 0.1) for row in rows]
    weights = [value / sum(inverse_vol) for value in inverse_vol]
    weights = [min(value, 0.40) for value in weights]
    weights = [value / sum(weights) for value in weights]
    for row, weight in zip(rows, weights):
        row["suggested_weight"] = round(weight * 100, 1)
    output["strategies"].append({**risk, "kind": "risk_budget",
      "as_of": str(pd.to_datetime(latest["date"]).max().date()),
      "state": "Allocation calculée", "rows": rows})

    macro = strategies["macro_regime"]
    ndate, nfci = last_value(context, "financial_conditions_us")
    udate, uncertainty = last_value(context, "policy_uncertainty_us")
    ddate, _ = last_value(context, "broad_us_dollar")
    threshold = float(context["policy_uncertainty_us"].dropna().tail(252).quantile(0.75))
    dollar = context[["date", "broad_us_dollar"]].dropna().sort_values("date")
    dollar_60 = float(dollar.iloc[-1]["broad_us_dollar"] / dollar.iloc[-61]["broad_us_dollar"] - 1)
    checks = [
      {"name":"Conditions financières","value":round(nfci,3),"date":str(ndate.date()),"test":"NFCI supérieur à 0","met":nfci > 0},
      {"name":"Incertitude économique","value":round(uncertainty,1),"date":str(udate.date()),"test":f"au-dessus de {threshold:.1f}","met":uncertainty > threshold},
      {"name":"Dollar large","value":round(dollar_60 * 100,1),"date":str(ddate.date()),"test":"hausse supérieure à 3 % sur 60 séances","met":dollar_60 > 0.03}]
    cautious = sum(item["met"] for item in checks) >= 2
    allocation = macro["cautious_assets"] if cautious else macro["normal_assets"]
    output["strategies"].append({**macro, "kind":"macro_regime",
      "as_of":str(max(ndate, udate, ddate).date()),
      "state":"Prudence" if cautious else "Allocation normale", "checks":checks,
      "allocation":[{"asset_id":asset,"name":names.get(asset,asset),"weight":round(weight*100,1)}
                    for asset, weight in allocation.items()]})

    volume = strategies["volume_confirmation"]
    etfs = set(universe.loc[universe["category"].eq("ETF"), "asset_id"])
    px = prices.loc[prices["asset_id"].isin(etfs)].sort_values(["asset_id","date"]).copy()
    px["volume_avg20"] = px.groupby("asset_id")["volume"].transform(lambda x: x.rolling(20, min_periods=20).mean())
    last = px.groupby("asset_id", as_index=False).tail(1).merge(latest, on="asset_id", suffixes=("", "_indicator"))
    last["volume_ratio"] = last["volume"] / last["volume_avg20"]
    selected = last.loc[(last["sma200_ratio"] > 0) & (last["ret_60d"] > 0) &
                        (last["volume_ratio"] >= float(volume["volume_ratio_min"]))].nlargest(int(volume["top_n"]), "ret_60d")
    rows = [{"asset_id":row.asset_id,"name":names.get(row.asset_id,row.asset_id),
             "return_60d":round(float(row.ret_60d)*100,1),"volume_ratio":round(float(row.volume_ratio),2),
             "above_sma200":True} for row in selected.itertuples()]
    output["strategies"].append({**volume, "kind":"volume_confirmation",
      "as_of":str(pd.to_datetime(latest["date"]).max().date()),
      "state":f"{len(rows)} ETF retenu(s) par les trois conditions" if rows else "Aucun ETF ne remplit les trois conditions",
      "rows":rows})
    Path("docs/data/strategy-lab.json").write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n")

if __name__ == "__main__":
    main()
