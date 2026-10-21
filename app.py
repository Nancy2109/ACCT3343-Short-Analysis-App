"""ACCT 3343 | Educational short-analysis SELL risk screener."""
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="ACCT 3343 | Short Analysis", page_icon="📉", layout="wide")
st.markdown('''<style>
.block-container {padding-top: 1.5rem; max-width: 1450px}
[data-testid="stMetric"] {background:#f3f6fa; border-radius:12px; padding:15px}
h1,h2,h3 {letter-spacing:-.025em}
</style>''', unsafe_allow_html=True)

@st.cache_data
def load_data():
    path = Path(__file__).with_name("ACCT3343_Short_App_Complete_Data.csv")
    df = pd.read_csv(path)
    for c in ["total_assets", "gross_profit", "net_income", "operating_cf", "sta", "gpa", "pe_ratio", "pb_ratio", "ev_ebitda"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["sector"] = df["sector"].fillna("Unclassified")
    df["industry"] = df["industry"].fillna("Unclassified")
    df["fiscal_date"] = pd.to_datetime(df["fiscal_date"], errors="coerce")
    df = df.loc[(df.total_assets > 0) & df.ticker.notna()].drop_duplicates("ticker").copy()
    # Recalculate from raw financial statement fields instead of relying on precomputed ratios.
    df["STA"] = (df.net_income - df.operating_cf) / df.total_assets
    df["GPA"] = df.gross_profit / df.total_assets
    for name, src in [("P/E", "pe_ratio"), ("P/B", "pb_ratio"), ("EV/EBITDA", "ev_ebitda")]:
        df[name] = df[src].where(df[src] > 0, np.nan)
    return df

def percentile_scores(universe, peer_basis, minimum_peers):
    out = universe.copy()
    for metric in ["STA", "GPA", "P/E", "P/B", "EV/EBITDA"]:
        score_col = "score_" + metric
        if peer_basis == "Sector":
            peer_count = out.groupby("sector")[metric].transform("count")
            score = out.groupby("sector")[metric].rank(pct=True, method="average")
            # Insufficient peer groups have no score, rather than a misleading percentile.
            out[score_col] = score.where(peer_count >= minimum_peers)
        else:
            out[score_col] = out[metric].rank(pct=True, method="average").where(out[metric].count() >= minimum_peers)
        if metric == "GPA":
            out[score_col] = 1 - out[score_col]  # Low profitability is a higher risk signal.
    return out

full = load_data()
st.title("📉 Short Analysis | Potentially Overvalued Stocks")
st.caption("ACCT 3343 • Financial statement quality × market valuation • Educational screening, not a trade recommendation")
st.markdown("**Research question:** Which companies combine comparatively weak accounting quality with expensive market valuations—and therefore deserve further investigation as potential SELL candidates?")

with st.sidebar:
    st.header("Screen settings")
    peer_basis = st.radio("Compare against", ["Sector", "Entire universe"], help="Percentiles are computed using the full dataset, before applying filters.")
    min_peers = st.slider("Minimum peers for a valid metric", 5, 40, 10)
    sectors = st.multiselect("Sectors", sorted(full.sector.unique()), default=[] , placeholder="All sectors")
    selected = full[full.sector.isin(sectors)] if sectors else full
    industries = st.multiselect("Industries", sorted(selected.industry.unique()), default=[], placeholder="All industries")
    min_sta = st.slider("Minimum STA (accrual intensity)", -0.30, 0.30, -0.30, 0.01, help="Higher STA suggests earnings rely more on accruals relative to cash flow.")
    max_gpa = st.slider("Maximum GPA (profitability)", 0.05, 1.20, 1.20, 0.01, help="Lower GPA can suggest weaker asset-level gross profitability; sector context matters.")
    min_pe = st.number_input("Minimum positive P/E (optional)", min_value=0.0, max_value=1000.0, value=0.0, step=5.0)
    require_valuation = st.checkbox("Require at least one valid valuation multiple", value=True)
    require_both = st.checkbox("Require both quality signals", value=True, help="When enabled, the screen requires STA and GPA to be available for scoring.")
    st.divider()
    st.subheader("Signal weights")
    w_sta = st.slider("STA: high accruals", 0, 100, 25, 5)
    w_gpa = st.slider("GPA: low profitability", 0, 100, 25, 5)
    w_pe = st.slider("P/E: expensive earnings", 0, 100, 20, 5)
    w_pb = st.slider("P/B: expensive book value", 0, 100, 15, 5)
    w_ev = st.slider("EV/EBITDA: expensive operations", 0, 100, 15, 5)
    top_n = st.slider("Number of displayed candidates", 5, 100, 20, 5)

# Score on the complete comparison universe, never on the already filtered candidates.
scored = percentile_scores(full, peer_basis, min_peers)
weights = {"STA": w_sta, "GPA": w_gpa, "P/E": w_pe, "P/B": w_pb, "EV/EBITDA": w_ev}
if not any(weights.values()):
    st.warning("Select at least one positive signal weight to calculate a ranking.")
    st.stop()
score_cols = ["score_" + x for x in weights]
weight_array = np.array(list(weights.values()), dtype=float)
score_matrix = scored[score_cols].to_numpy(dtype=float)
valid = np.isfinite(score_matrix)
used_weight = (valid * weight_array).sum(axis=1)
weighted_sum = np.nansum(score_matrix * weight_array, axis=1)
scored["Risk score"] = np.divide(100 * weighted_sum, used_weight, out=np.full(len(scored), np.nan), where=used_weight > 0)
scored["Signals scored"] = (valid & (weight_array > 0)).sum(axis=1)
scored["Valuation coverage"] = scored[["P/E", "P/B", "EV/EBITDA"]].notna().sum(axis=1)

mask = (scored.STA >= min_sta) & (scored.GPA <= max_gpa)
if sectors:
    mask &= scored.sector.isin(sectors)
if industries:
    mask &= scored.industry.isin(industries)
if min_pe > 0:
    mask &= scored["P/E"] >= min_pe
if require_valuation:
    mask &= scored["Valuation coverage"] >= 1
if require_both:
    mask &= scored[["score_STA", "score_GPA"]].notna().all(axis=1)
mask &= scored["Risk score"].notna()
filtered = scored.loc[mask].sort_values(["Risk score", "ticker"], ascending=[False, True]).copy()

m1,m2,m3,m4 = st.columns(4)
m1.metric("Companies analyzed", f"{len(full):,}")
m2.metric("Matching current screen", f"{len(filtered):,}")
m3.metric("Valid positive P/E", f"{full['P/E'].notna().sum():,}")
m4.metric("Latest fiscal statement", full.fiscal_date.max().strftime("%b %Y") if full.fiscal_date.notna().any() else "Unknown")

st.subheader("Ranked SELL-risk watchlist")
st.write("**Higher score = stronger combination of relative red flags**, not a prediction that a stock will fall. Percentiles are computed across the selected peer basis; missing metrics are excluded and the remaining weights are normalized.")
if filtered.empty:
    st.info("No companies match the current settings. Widen your thresholds, select more sectors, or reduce minimum peer count.")
else:
    view = filtered.head(top_n)
    display_cols = ["ticker", "sector", "industry", "Risk score", "Signals scored", "STA", "GPA", "P/E", "P/B", "EV/EBITDA"]
    st.dataframe(view[display_cols], use_container_width=True, hide_index=True, column_config={
        "ticker": "Ticker", "Risk score": st.column_config.ProgressColumn("Risk score / 100", min_value=0, max_value=100, format="%.1f"),
        "STA": st.column_config.NumberColumn("STA", format="%.3f"),
        "GPA": st.column_config.NumberColumn("GPA", format="%.3f"),
        "P/E": st.column_config.NumberColumn("P/E", format="%.1f"),
        "P/B": st.column_config.NumberColumn("P/B", format="%.1f"),
        "EV/EBITDA": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
    })
    st.download_button("⬇️ Download matching candidates (CSV)", filtered[["ticker", "sector", "industry", "fiscal_date", "Risk score", "Signals scored", "STA", "GPA", "P/E", "P/B", "EV/EBITDA"]].to_csv(index=False).encode("utf-8"), "ACCT3343_sell_screen_results.csv", "text/csv")

    left, right = st.columns([1.1,1])
    with left:
        st.subheader("Highest-ranked candidates")
        st.bar_chart(view.head(15).set_index("ticker")["Risk score"], horizontal=True)
    with right:
        st.subheader("Accounting quality vs valuation")
        scatter = filtered.loc[filtered["P/E"].notna() & filtered.GPA.notna(), ["ticker", "GPA", "P/E"]].copy()
        if len(scatter):
            # Clip chart display only, to keep extreme P/E values from flattening the view.
            scatter["P/E (display capped)"] = scatter["P/E"].clip(upper=scatter["P/E"].quantile(.95))
            st.scatter_chart(scatter, x="GPA", y="P/E (display capped)")
            st.caption("Chart-only P/E cap at the 95th percentile; actual P/E is unchanged in ranking and tables.")
        else:
            st.info("No valid positive P/E values among matching companies.")

    st.subheader("Company investigation")
    chosen = st.selectbox("Select a company", view.ticker.tolist())
    row = filtered.loc[filtered.ticker == chosen].iloc[0]
    a,b,c,d = st.columns(4)
    a.metric("Relative risk score", f"{row['Risk score']:.1f}/100")
    b.metric("STA", f"{row.STA:.3f}")
    c.metric("GPA", f"{row.GPA:.3f}")
    d.metric("Valuation signals available", f"{int(row['Valuation coverage'])}/3")
    observations = []
    for name, direction in [("STA", "higher accrual dependence"), ("GPA", "weaker gross profitability"), ("P/E", "higher earnings multiple"), ("P/B", "higher book-value multiple"), ("EV/EBITDA", "higher enterprise-value multiple")]:
        score = row["score_" + name]
        if pd.notna(score) and weights[name] > 0:
            observations.append(f"**{name}**: {score:.0%} relative risk percentile ({direction})")
    st.markdown("**Why it appeared in the screen**")
    for observation in observations:
        st.markdown("- " + observation)
    if row["Risk score"] >= 75 and row["Valuation coverage"] >= 1:
        st.markdown("**Interpretation:** Elevated relative SELL-risk watchlist priority. Investigate valuation assumptions, earnings-to-cash conversion, and company-specific catalysts before any conclusion.")
    else:
        st.markdown("**Interpretation:** A relative screening candidate, not sufficient evidence of overvaluation. Review fundamentals and the applicable sector before making a decision.")
    st.caption(f"Fiscal statement date: {row.fiscal_date.strftime('%Y-%m-%d') if pd.notna(row.fiscal_date) else 'unknown'} • Sector: {row.sector} • Industry: {row.industry}")

with st.expander("Methodology, formulas, and limitations", expanded=False):
    st.markdown(r"""
**1. Financial statement measures**
- **STA (simplified scaled total accruals)** = (Net income − Operating cash flow) / Total assets. Higher values may indicate weaker cash backing for reported earnings. This is a simplified proxy, **not** a full balance-sheet total-accruals or SNOA calculation.
- **GPA** = Gross profit / Total assets. Lower values may signal weaker gross profitability, though accounting conventions vary by sector.

**2. Valuation measures**
- **P/E** = trailing price-to-earnings ratio; **P/B** = price-to-book ratio; **EV/EBITDA** = enterprise value relative to EBITDA, as provided by the market-data source at collection time.
- Zero, negative, and missing multiples are treated as **unavailable** for comparative valuation, not as cheap or expensive. Very large positive multiples can be unstable when earnings are close to zero.

**3. Transparent ranking**
- For each metric, compute a within-sector or whole-universe percentile. High STA and high valuation multiples indicate greater risk; **low** GPA indicates greater risk (reverse percentile).
- Composite risk score = 100 × weighted mean of **available** risk percentiles. The denominator uses only the weights of available, valid metrics. The weights can be adjusted in the sidebar.
- Peer percentiles are calculated **before** filtering so that narrowing the list does not artificially change each stock's benchmark. A metric is not scored for groups below the minimum peer threshold.
- Screening thresholds are applied **after** the ranking calculation. A high score identifies an investigation priority, **not** a verified overvaluation or a guaranteed SELL.

**4. Data integrity and interpretation**
- Financial statements reflect different fiscal dates; valuation ratios are market snapshots from the collection period. The two are **not** synchronized to a historical as-of date.
- Cross-sector comparisons of GPA, P/B and EV/EBITDA can be misleading, especially for banks, insurers, real estate and businesses with different accounting conventions. Prefer sector peers and manual follow-up.
- No SNOA, Piotroski F-score, bankruptcy model, DCF, short-sale feasibility, borrow costs or forward return forecasts are calculated because the dataset does not support them.
- This is an educational research screener, not individualized investment advice.
""")
    st.write("**Data provenance:** Colab financial-statement collection and Yahoo Finance/yfinance valuation and classification fields, exported as a static CSV. Verify any result against current filings and market data before use.")
