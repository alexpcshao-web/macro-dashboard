import yfinance as yf
import pandas as pd
import json
from datetime import datetime

# ── 候選池 ──────────────────────────────────────────────
US_TICKERS = {
    "AI供應鏈/半導體": ["NVDA", "AMD", "AVGO", "AMAT", "LRCX", "KLAC"],
    "AI基礎建設":      ["MSFT", "GOOGL", "META", "DELL", "SMCI"],
    "記憶體":          ["MU"],
}

TW_TICKERS = {
    "台灣半導體":  ["2330.TW", "2454.TW", "2379.TW"],
    "AI伺服器":    ["2382.TW", "6669.TW", "2317.TW"],
    "記憶體/封裝": ["2408.TW", "3711.TW"],
}

# 代工/組裝股用寬鬆毛利率標準
ASSEMBLY_TICKERS = {"DELL", "SMCI", "2382.TW", "6669.TW", "2317.TW", "3711.TW"}

# ── 篩選標準 ─────────────────────────────────────────────
CRITERIA_STANDARD = {
    "revenueGrowth": {"min": 0.10,  "label": "營收成長率 >10%"},
    "grossMargins":  {"min": 0.20,  "label": "毛利率 >20%"},
    "debtToEquity":  {"max": 100,   "label": "負債比 <100"},
    "freeCashflow":  {"min": 0,     "label": "FCF 為正"},
    "forwardPE":     {"max": 40,    "label": "前瞻P/E <40"},
}

CRITERIA_ASSEMBLY = {
    "revenueGrowth": {"min": 0.10,  "label": "營收成長率 >10%"},
    "grossMargins":  {"min": 0.06,  "label": "毛利率 >6%（代工）"},
    "debtToEquity":  {"max": 150,   "label": "負債比 <150"},
    "freeCashflow":  {"min": 0,     "label": "FCF 為正"},
    "forwardPE":     {"max": 40,    "label": "前瞻P/E <40"},
}

def get_institutional_change(ticker_obj):
    """抓法人持股變化：最近一季 vs 上一季"""
    try:
        inst = ticker_obj.institutional_holders
        if inst is None or inst.empty:
            return None, "無資料"
        # 取前5大法人持股加總
        total = inst["Shares"].iloc[:5].sum()
        return total, f"{total/1e6:.1f}M股（前5大）"
    except:
        return None, "無資料"

def score_ticker(symbol, info, ticker_obj):
    criteria = CRITERIA_ASSEMBLY if symbol in ASSEMBLY_TICKERS else CRITERIA_STANDARD
    score = 0
    max_score = 6  # 加入法人持股後滿分6
    details = {}

    # 營收成長率
    rev = info.get("revenueGrowth")
    if rev is not None:
        passed = rev >= criteria["revenueGrowth"]["min"]
        score += 1 if passed else 0
        details["營收成長率"] = f"{rev*100:.1f}% {'✅' if passed else '❌'}"
    else:
        details["營收成長率"] = "無資料 ⚠️"

    # 毛利率
    gm = info.get("grossMargins")
    if gm is not None:
        passed = gm >= criteria["grossMargins"]["min"]
        score += 1 if passed else 0
        details["毛利率"] = f"{gm*100:.1f}% {'✅' if passed else '❌'}"
    else:
        details["毛利率"] = "無資料 ⚠️"

    # 負債比
    de = info.get("debtToEquity")
    if de is not None:
        passed = de <= criteria["debtToEquity"]["max"]
        score += 1 if passed else 0
        details["負債比"] = f"{de:.1f} {'✅' if passed else '❌'}"
    else:
        details["負債比"] = "無資料 ⚠️"

    # FCF
    fcf = info.get("freeCashflow")
    if fcf is not None:
        passed = fcf >= 0
        score += 1 if passed else 0
        fcf_b = fcf / 1e9
        details["自由現金流"] = f"{'$' if fcf >= 0 else '-$'}{abs(fcf_b):.1f}B {'✅' if passed else '❌'}"
    else:
        details["自由現金流"] = "無資料 ⚠️"

    # 前瞻P/E
    pe = info.get("forwardPE")
    if pe is not None:
        passed = 0 < pe <= criteria["forwardPE"]["max"]
        score += 1 if passed else 0
        details["前瞻P/E"] = f"{pe:.1f} {'✅' if passed else '❌'}"
    else:
        details["前瞻P/E"] = "無資料 ⚠️"

    # 法人持股（第6個指標，加分項）
    inst_val, inst_label = get_institutional_change(ticker_obj)
    inst_pct = info.get("institutionPercentHeld")
    if inst_pct is not None:
        passed = inst_pct >= 0.30  # 法人持股比例 >30% 為健康
        score += 1 if passed else 0
        details["法人持股比例"] = f"{inst_pct*100:.1f}% {'✅' if passed else '❌'}"
    else:
        details["法人持股比例"] = f"{inst_label} ⚠️"
        max_score = 5  # 台股法人資料通常抓不到，不算入滿分

    return score, max_score, details

def fetch_all(ticker_groups, market):
    results = []
    for sector, tickers in ticker_groups.items():
        for symbol in tickers:
            print(f"  抓取 {symbol}...")
            try:
                t = yf.Ticker(symbol)
                info = t.info
                name = info.get("longName") or info.get("shortName") or symbol
                score, max_score, details = score_ticker(symbol, info, t)
                results.append({
                    "symbol":    symbol,
                    "name":      name,
                    "market":    market,
                    "sector":    sector,
                    "score":     score,
                    "max_score": max_score,
                    "score_pct": round(score / max_score * 100),
                    "details":   details,
                    "type":      "代工/組裝" if symbol in ASSEMBLY_TICKERS else "標準",
                })
            except Exception as e:
                print(f"  ⚠️  {symbol} 抓取失敗: {e}")
    return results

# ── 主程式 ───────────────────────────────────────────────
print("📊 開始篩選美股...")
us_results = fetch_all(US_TICKERS, "美股")

print("📊 開始篩選台股...")
tw_results = fetch_all(TW_TICKERS, "台股")

all_results = us_results + tw_results
all_results.sort(key=lambda x: x["score_pct"], reverse=True)

output = {
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "results":    all_results,
}

with open("screening_results.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ 完成！共篩選 {len(all_results)} 支股票")
print(f"📁 結果已輸出至 screening_results.json\n")

df = pd.DataFrame([{
    "代號":   r["symbol"],
    "市場":   r["market"],
    "板塊":   r["sector"],
    "類型":   r["type"],
    "評分":   f"{r['score']}/{r['max_score']} ({r['score_pct']}%)",
    "名稱":   r["name"][:18],
} for r in all_results])

print(df.to_string(index=False))
