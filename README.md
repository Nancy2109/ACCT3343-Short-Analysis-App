# ACCT 3343 — Short Analysis App

An interactive educational SELL-risk screener across 663 companies. Ranks potentially overvalued companies by accrual quality, gross profitability and valuation multiples, using transparent sector-relative percentiles and customizable weights.

## Launch locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

1. Create a public GitHub repository.
2. Upload `app.py`, `requirements.txt` and `ACCT3343_Short_App_Complete_Data.csv` to the **repository root**.
3. At https://share.streamlit.io/ choose **Create app** → **Deploy a public app from GitHub**.
4. Choose the repository and `app.py` as the main file. Deploy.
5. Open the public app URL in a private/incognito window and confirm it works.
6. Submit **only the public Streamlit app URL** to Brightspace.

## Data and methodology

Financial statement data and Yahoo Finance/yfinance valuation fields were assembled in Colab. Statement dates vary. Valuation multiples are snapshots and may not align to the fiscal dates. Invalid or negative multiples are excluded from valuation scoring. Within-sector or universe percentile scores are combined with adjustable weights. Scores indicate **relative screening risk, not proven overvaluation or a trading recommendation**.

The dataset intentionally excludes TJX, the previously pitched company.
