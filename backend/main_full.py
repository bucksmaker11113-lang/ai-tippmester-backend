from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import csv, os, json, math, time
from typing import List, Dict

app = FastAPI(title="Tippmester AI 4.8 Full Live")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOW_ORIGINS","*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "version": "4.8-full-live"}

# ---------- Odds normalizálás (nemzetközi -> Tippmix skála) ----------
def normalize_to_tippmix(o: float) -> float:
    # kerekítés a Tippmix tipikus 2 tizedes formátumára + margin illesztés
    if o <= 0: return 0.0
    # egyszerű marzs-illesztés (3–6%) és “Tippmix” kerekítés
    adj = o * 0.97
    return float(f"{adj:.2f}")

# ---------- Bankroll (CSV) ----------
# Várja: reports/daily_report.csv; oszlopok: date,profit,bankroll
BANKROLL_CSV = os.getenv("BANKROLL_CSV", "backend/reports/daily_report.csv")

@app.get("/api/bankroll")
async def api_bankroll():
    start_huf = 300_000
    today_profit, total_profit, last_bankroll = 0.0, 0.0, start_huf
    try:
        with open(BANKROLL_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if rows:
            last = rows[-1]
            last_bankroll = float(last.get("bankroll", start_huf))
            # napi profit az utolsó sorból, összes profit a kezdőhöz képest
            today_profit = float(last.get("profit", 0.0))
            total_profit = last_bankroll - start_huf
    except FileNotFoundError:
        pass
    return {
        "start": start_huf,
        "today_profit": round(today_profit, 2),
        "total_profit": round(total_profit, 2),
        "bankroll": round(last_bankroll, 2),
    }

# ---------- Élő odds feed ----------
# Itt most sablon-adapter: ide valós API-k (TheOddsAPI/RapidAPI) köthetők.
# Kimenet: [{match, home, draw, away}]
@app.get("/api/live_odds")
async def api_live_odds():
    # Példa nemzetközi odds → Tippmix normalizálva
    raw = [
        {"match":"Man City – Arsenal", "home":1.89, "draw":3.60, "away":4.20},
        {"match":"Bayern – Dortmund",  "home":1.68, "draw":3.95, "away":4.90},
    ]
    data = []
    for r in raw:
        data.append({
            "match": r["match"],
            "home": normalize_to_tippmix(r["home"]),
            "draw": normalize_to_tippmix(r["draw"]),
            "away": normalize_to_tippmix(r["away"]),
        })
    return data

# ---------- Napi tippek + kombó ----------
class Tip(BaseModel):
    match: str
    pick: str
    odds: float

def generate_daily_tips() -> List[Tip]:
    # Itt majd a MonteCarlo/HybridBias hívás történik – most placeholder
    return [
        Tip(match="Real Madrid – Barca", pick="Hazai",  odds=2.12),
        Tip(match="PSG – Lyon",         pick="Over 2.5",odds=1.86),
        Tip(match="Liverpool – Chelsea",pick="BTTS",    odds=1.93),
        Tip(match="Juve – Napoli",      pick="Under 2.5",odds=1.71),
    ]

@app.get("/api/tips/single")
async def api_tips_single():
    tips = generate_daily_tips()
    # Tippmixhez igazított odds
    for t in tips:
        t.odds = normalize_to_tippmix(t.odds)
    return [t.dict() for t in tips]

@app.get("/api/tips/combo")
async def api_tips_combo():
    tips = generate_daily_tips()
    for t in tips:
        t.odds = normalize_to_tippmix(t.odds)
    combo_odds = 1.0
    for t in tips[:4]:  # 4 single a kombóban
        combo_odds *= max(t.odds, 1.01)
    combo_odds = float(f"{combo_odds:.2f}")
    return {"combo_odds": combo_odds, "items": [t.dict() for t in tips[:4]]}
  
