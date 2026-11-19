import re
import time
import urllib.parse
import requests
import pandas as pd
import numpy as np
from datetime import datetime

def get_usd_twd_rate():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        return float(res.json()["rates"]["TWD"])
    except Exception:
        return 32.5

def fetch_ebay_sold_median_usd(query):
    url = f"https://www.ebay.com/sch/i.html?_nkw={urllib.parse.quote(query)}&LH_Sold=1&LH_Complete=1&_ipg=25"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        prices = re.findall(r'class="s-item__price"[^>]*>(?:<span[^>]*>)?\$([0-9,]+\.[0-9]{2})', resp.text)
        clean_prices = [float(p.replace(',', '')) for p in prices if float(p.replace(',', '')) > 1.0]
        if len(clean_prices) >= 2:
            sample = clean_prices[1:8] if len(clean_prices) > 3 else clean_prices
            return float(np.median(sample))
    except Exception as e:
        print(f"Fetch failed for {query}: {e}")
    return None

def main():
    csv_path = "cards_portfolio_cleaned.csv"
    df = pd.read_csv(csv_path)
    usd_twd = get_usd_twd_rate()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 目前 USD/TWD 匯率: {usd_twd:.2f}")

    for idx, row in df.iterrows():
        cost = float(row.get("購入成本_TWD", 0) or 0)
        grade = str(row.get("鑑定", ""))
        query = str(row.get("自動查價關鍵字", "")).strip()

        if (cost >= 1500 or grade != "裸卡(Raw)") and query:
            median_usd = fetch_ebay_sold_median_usd(query)
            if median_usd:
                est_twd = round(median_usd * usd_twd, 0)
                df.at[idx, "目前估值_TWD"] = est_twd
                df.at[idx, "未實現損益_TWD"] = est_twd - cost
                df.at[idx, "報酬率_pct"] = round(((est_twd - cost) / cost) * 100, 2) if cost > 0 else 0.0
            time.sleep(1.5)

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print("cards_portfolio_cleaned.csv 每日行情更新完成！")

if __name__ == "__main__":
    main()
