#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  KrishiMitra — Farmer Advisory Test Script

  Run:  python farmer_advisory.py

  Enter your crop, market, and quantity. Get the EXACT output
  a farmer would see: predicted price, 7-day forecast, sell/wait
  decision, MSP check, nearby market comparison, revenue estimate.
═══════════════════════════════════════════════════════════════
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, r'c:\agri\backend')

from services.karnataka_predictor import GroundnutPredictor, CoconutPredictor, PaddyPredictor, KarnatakaForecaster
from datetime import datetime, timedelta

# ── ANSI colors for pretty terminal output ───────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def divider(char="─", width=60):
    print(f"{DIM}{char * width}{RESET}")

def header(text, width=60):
    print()
    print(f"{BOLD}{GREEN}{'═' * width}{RESET}")
    print(f"{BOLD}{GREEN}  {text}{RESET}")
    print(f"{BOLD}{GREEN}{'═' * width}{RESET}")

def sub_header(text):
    print(f"\n{BOLD}{CYAN}  ▸ {text}{RESET}")
    divider()


def run_advisory():
    # ── Load models on startup ────────────────────────────────
    print(f"\n{DIM}Loading Karnataka crop models...{RESET}")
    gp = GroundnutPredictor()
    cp = CoconutPredictor()
    pp = PaddyPredictor()
    print(f"{GREEN}✅ All models loaded successfully{RESET}\n")

    while True:
        header("KrishiMitra — Farmer Advisory")

        # ── 1. Collect inputs ─────────────────────────────────
        print(f"\n{BOLD}  Select your crop:{RESET}")
        print(f"    1. Groundnut")
        print(f"    2. Coconut")
        print(f"    3. Paddy (Rice)")
        choice = input(f"\n  Enter choice (1/2/3): ").strip()

        if choice == "1":
            crop = "groundnut"
            predictor = gp
        elif choice == "2":
            crop = "coconut"
            predictor = cp
        elif choice == "3":
            crop = "paddy"
            predictor = pp
        else:
            print(f"{RED}  Invalid choice. Try again.{RESET}")
            continue

        # Show only FRESH markets (data < 60 days old)
        fresh = predictor.fresh_markets()
        all_markets = predictor.available_markets()
        stale_count = len(all_markets) - len(fresh)

        print(f"\n{BOLD}  Markets with recent data ({len(fresh)} active, {stale_count} stale excluded):{RESET}")
        for i, m in enumerate(fresh, 1):
            print(f"    {i:2d}. {m}")

        market_input = input(f"\n  Enter market number or name: ").strip()
        try:
            idx = int(market_input) - 1
            if 0 <= idx < len(fresh):
                market = fresh[idx]
            else:
                print(f"{RED}  Invalid number.{RESET}")
                continue
        except ValueError:
            # Try matching by name in all markets (user might type a known name)
            matches = [m for m in all_markets if market_input.lower() in m.lower()]
            if matches:
                market = matches[0]
                if not predictor._is_market_fresh(market):
                    print(f"{YELLOW}  ⚠️  {market} has stale data (>60 days old). Results may be less accurate.{RESET}")
            else:
                print(f"{RED}  Market not found. Using first fresh market.{RESET}")
                market = fresh[0] if fresh else all_markets[0]

        qty_str = input(f"  Enter quantity (quintals) [default: 50]: ").strip()
        quantity = float(qty_str) if qty_str else 50.0

        storage_str = input(f"  Do you have storage? (y/n) [default: n]: ").strip().lower()
        has_storage = storage_str in ("y", "yes")
        storage_days = 30 if has_storage else 0

        # ── 2. Run predictions ────────────────────────────────
        print(f"\n{DIM}  Running model predictions...{RESET}")

        today_result = predictor.predict(market=market, quantity=quantity)
        forecast_7d  = predictor.forecast(market=market, days=7, quantity=quantity, storage_days=storage_days)
        day_30       = predictor.predict(market=market, date=datetime.now() + timedelta(days=30), quantity=quantity)

        # Nearby market comparison — ONLY fresh markets
        nearby = []
        for m in fresh:
            if m != market:
                try:
                    p = predictor.predict(market=m, quantity=quantity)
                    nearby.append({"market": m, "price": p["predicted_price"]})
                except Exception:
                    pass
        nearby.sort(key=lambda x: x["price"], reverse=True)
        top_nearby = nearby[:5]

        today_price = today_result["predicted_price"]
        fc_list     = forecast_7d["forecast"]

        # ── 3. Display: TODAY'S PREDICTION ────────────────────
        header(f"Advisory for {crop.upper()} — {market}")

        sub_header("TODAY'S PREDICTED PRICE")
        print(f"    📅 Date       : {today_result['date']}")
        print(f"    💰 Price      : {BOLD}₹{today_price:,}/quintal{RESET}")
        print(f"    📦 Quantity   : {quantity} quintals")
        print(f"    💵 Revenue    : {BOLD}₹{today_result['revenue']:,}{RESET}")

        if today_result.get("festival"):
            print(f"    🎉 Festival   : {today_result['festival']} (+{today_result['festival_boost']}%)")

        print(f"    🌾 Season     : {today_result['season']}")

        # ── 4. MSP CHECK ─────────────────────────────────────
        sub_header("MSP (Minimum Support Price) CHECK")
        if crop in ("groundnut", "paddy"):
            msp = predictor.MSP_2025
            above = today_result.get("above_msp", today_price >= msp)
            if above:
                diff = today_price - msp
                print(f"    {GREEN}✅ ₹{diff:,.0f} ABOVE MSP (₹{msp:,}){RESET}")
                print(f"    {DIM}Market price is healthy — selling in open market is fine.{RESET}")
            else:
                diff = msp - today_price
                print(f"    {RED}⚠️  ₹{diff:,.0f} BELOW MSP (₹{msp:,}){RESET}")
                print(f"    {YELLOW}→ Check government procurement / NAFED centers{RESET}")
                print(f"    {YELLOW}→ You could get ₹{msp:,}/quintal via MSP instead of ₹{today_price:,}{RESET}")
                govt_revenue = msp * quantity
                print(f"    {YELLOW}→ MSP revenue: ₹{govt_revenue:,} vs Market: ₹{today_result['revenue']:,} = ₹{govt_revenue - today_result['revenue']:,} more{RESET}")
            # FCI procurement note for paddy
            if crop == "paddy" and today_result.get("fci_note"):
                print(f"    {CYAN}📋 {today_result['fci_note']}{RESET}")
        else:
            print(f"    {DIM}No MSP defined for coconut by central government.{RESET}")
            print(f"    {DIM}Check state-level procurement prices if available.{RESET}")

        # ── 5. 7-DAY FORECAST ─────────────────────────────────
        sub_header("7-DAY PRICE FORECAST")
        trend_pct = forecast_7d["trend_pct"]
        if trend_pct > 3:
            trend_label = f"{GREEN}📈 RISING (+{trend_pct}%){RESET}"
        elif trend_pct < -3:
            trend_label = f"{RED}📉 FALLING ({trend_pct}%){RESET}"
        else:
            trend_label = f"{YELLOW}→ STABLE ({trend_pct:+.1f}%){RESET}"

        print(f"    Trend: {trend_label}")
        print()

        # Price chart
        prices = [f["price"] for f in fc_list]
        min_p, max_p = min(prices), max(prices)
        bar_width = 30

        for f in fc_list:
            p = f["price"]
            if max_p > min_p:
                bar_len = int((p - min_p) / (max_p - min_p) * bar_width) + 1
            else:
                bar_len = bar_width // 2
            bar = "█" * bar_len
            fest = f" 🎉 {f['festival']}" if f.get("festival") else ""
            msp_icon = ""
            if crop in ("groundnut", "paddy"):
                msp = predictor.MSP_2025
                msp_icon = f" {GREEN}✅{RESET}" if f.get("above_msp", p >= msp) else f" {RED}⚠️{RESET}"
            print(f"    {f['day']:<14} ₹{p:>7,}  {GREEN}{bar}{RESET}{msp_icon}{fest}")

        # ── 6. DAY 30 PREDICTION ──────────────────────────────
        sub_header("30-DAY OUTLOOK")
        d30_price = day_30["predicted_price"]
        d30_diff  = d30_price - today_price
        d30_pct   = (d30_diff / today_price * 100) if today_price else 0

        if d30_diff > 0:
            print(f"    Day 30 price : {GREEN}₹{d30_price:,} ({d30_pct:+.1f}% from today){RESET}")
        else:
            print(f"    Day 30 price : {RED}₹{d30_price:,} ({d30_pct:+.1f}% from today){RESET}")

        d30_revenue = d30_price * quantity
        print(f"    Revenue @30d : ₹{d30_revenue:,}")
        print(f"    Today revenue: ₹{today_result['revenue']:,}")
        rev_diff = d30_revenue - today_result["revenue"]
        if rev_diff > 0:
            print(f"    {GREEN}Potential gain by waiting: +₹{rev_diff:,}{RESET}")
        else:
            print(f"    {RED}Loss by waiting: ₹{rev_diff:,}{RESET}")

        # ── 7. STORAGE ANALYSIS ───────────────────────────────
        sub_header("STORAGE ANALYSIS")
        loss_rate = predictor.LOSS_PER_DAY
        if has_storage:
            best = forecast_7d["best_day"]
            print(f"    Storage available: ✅ Yes")
            print(f"    Spoilage rate   : {loss_rate}% per day")
            print(f"    Best sell day   : {BOLD}{best['day']}{RESET}")
            print(f"    Best gross price: ₹{best['price']:,}")
            print(f"    Best net price  : ₹{best['net_price']:,} (after spoilage)")
            gain = best["gain_pct"]
            if gain > 0:
                print(f"    Net gain vs today: {GREEN}+{gain}%{RESET}")
                net_revenue = best['net_price'] * quantity
                revenue_gain = net_revenue - today_result['revenue']
                print(f"    Revenue gain    : {GREEN}+₹{revenue_gain:,.0f}{RESET}")
            else:
                print(f"    Net gain vs today: {RED}{gain}% — no benefit from waiting{RESET}")
        else:
            print(f"    Storage available : ❌ No")
            print(f"    Spoilage rate    : {loss_rate}% per day (if stored)")
            print(f"    {DIM}Without storage, sell within 1-2 days to minimize spoilage.{RESET}")

        # ── 8. SELL / WAIT / PROCUREMENT DECISION ─────────────
        sub_header("🎯 RECOMMENDATION")

        # Decision logic
        if crop in ("groundnut", "paddy") and not today_result.get("above_msp", True):
            decision = "GOVT_PROCUREMENT"
            msp = predictor.MSP_2025
            reason = f"Price is below MSP. Sell via government procurement for ₹{msp:,}/quintal."
            if crop == "paddy" and today_result.get("fci_note"):
                reason += " FCI procurement window is open."
            color = YELLOW
        elif has_storage and forecast_7d["best_day"]["gain_pct"] > 1.0:
            decision = "WAIT"
            best = forecast_7d["best_day"]
            reason = (
                f"Prices trending up. Best day: {best['day']} "
                f"(₹{best['net_price']:,} net after {loss_rate}%/day spoilage, +{best['gain_pct']}% gain). "
                f"Store and sell later."
            )
            color = CYAN
        elif trend_pct > 3 and not has_storage:
            decision = "SELL (but consider storage)"
            reason = f"Prices are rising (+{trend_pct}%) but you have no storage. Sell now or arrange storage."
            color = YELLOW
        elif trend_pct < -3:
            decision = "SELL NOW"
            reason = f"Prices are falling ({trend_pct}%). Sell today to avoid further loss."
            color = GREEN
        else:
            decision = "SELL"
            reason = f"Prices are stable. No significant gain expected from waiting."
            color = GREEN

        print(f"\n    {color}{BOLD}  ╔═══════════════════════════════════════╗")
        print(f"    ║  Decision:  {decision:<28}║")
        print(f"    ╚═══════════════════════════════════════╝{RESET}")
        print(f"\n    {reason}")
        print(f"\n    💰 If you sell today  : ₹{today_result['revenue']:,}")
        if has_storage and forecast_7d["best_day"]["gain_pct"] > 0:
            best = forecast_7d["best_day"]
            print(f"    💰 If you wait ({best['day']}) : ₹{best['net_price'] * quantity:,.0f}")
        if crop in ("groundnut", "paddy") and not today_result.get("above_msp", True):
            print(f"    💰 Via MSP procurement : ₹{predictor.MSP_2025 * quantity:,}")

        # ── 9. NEARBY MARKET COMPARISON ───────────────────────
        sub_header("NEARBY MARKETS — Higher Prices (fresh data only)")
        better_markets = [m for m in top_nearby if m["price"] > today_price]
        if better_markets:
            for i, m in enumerate(better_markets[:5], 1):
                diff = m["price"] - today_price
                extra_rev = diff * quantity
                print(f"    {i}. {m['market']:<30} ₹{m['price']:>7,}  {GREEN}+₹{diff:,}/q  (+₹{extra_rev:,.0f} total){RESET}")
            print(f"\n    {DIM}Note: Transport costs not included. Factor in ₹50-200/quintal for transport.{RESET}")
        else:
            print(f"    {GREEN}✅ Your market ({market}) has one of the best prices!{RESET}")

        # ── 10. MODEL CONFIDENCE ──────────────────────────────
        sub_header("MODEL INFO")
        print(f"    Model MAE    : ₹{today_result['model_mae']:,.0f} (average error margin)")
        print(f"    Model built  : {today_result['model_built_at']}")
        print(f"    Spoilage rate: {loss_rate}% per day ({crop})")
        print(f"    {DIM}Predictions are estimates. Actual prices may vary by ±₹{today_result['model_mae']:,.0f}{RESET}")

        divider("═")
        print()

        # ── Continue? ─────────────────────────────────────────
        again = input(f"  Run another advisory? (y/n): ").strip().lower()
        if again not in ("y", "yes"):
            print(f"\n{GREEN}  Thank you for using KrishiMitra! Happy farming! 🌾{RESET}\n")
            break


if __name__ == "__main__":
    run_advisory()
