import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ── Constants ─────────────────────────────────────────────────────────────────
META_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/14KA90yocZci3ZJud3XYiM2-78HZFF3fcTbHpYNr_bY8"
    "/export?format=csv&gid=838145140"
)
GOOGLE_ADS_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/1HGOWbDKAZ7VxAK-1xeBhp7RYGcwg_7fkpmdShut1DyA"
    "/export?format=csv&gid=1730280898"
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="Marketing Analytics Dashboard",
    page_icon="📊",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(90deg, #1e3c72, #2a5298, #764ba2);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 16px 12px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 4px 0;
        min-height: 100px;
    }
    .metric-value { font-size: 1.6rem; font-weight: bold; margin: 6px 0; }
    .metric-label { font-size: 0.8rem; opacity: 0.85; margin-bottom: 4px; }
    .metric-delta { font-size: 0.75rem; margin-top: 2px; }
    .section-header {
        border-left: 4px solid #2a5298;
        padding-left: 10px;
        margin: 24px 0 8px;
        font-size: 1.1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">📊 Marketing Analytics Dashboard</h1>', unsafe_allow_html=True)


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_sheet(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception:
        return None


def load_data(sheet_url, upload_key):
    uploaded = st.file_uploader("Upload CSV", type=["csv"], key=upload_key)
    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
            df.columns = df.columns.str.strip()
            return df, "Uploaded CSV"
        except Exception:
            st.warning("Could not read uploaded file.")
            return None, None
    df = fetch_sheet(sheet_url)
    if df is not None:
        st.success("Loaded from Google Sheet")
        return df, "Google Sheet"
    st.warning("Could not load data automatically. Upload a CSV to continue.")
    return None, None


# ── Column normalization & cleaning ───────────────────────────────────────────

_COLUMN_MAP = {
    "campaign": "Campaign name",
    "campaign name": "Campaign name",
    "campaign_state": "Campaign_state",
    "campaign state": "Campaign_state",
    "campaign_type": "Campaign_type",
    "campaign type": "Campaign_type",
    "adgroup": "Ad set name",
    "ad group": "Ad set name",
    "spends": "Spends",
    "cost": "Spends",
    "impr": "Impression",
    "impression": "Impression",
    "conversions": "Conversions",
    "total_lead_db": "Total Leads DB",
    "new_lead_db": "New Leads DB",
    "old_lead_db": "Old Leads DB",
    "month": "Month",
    "date": "Date",
}


def normalize_columns(df):
    return df.rename(columns={c: _COLUMN_MAP.get(c.lower(), c) for c in df.columns})


def clean_data(df):
    day_col = next(
        (c for c in df.columns if "day" in c.lower() or "date" in c.lower()), None
    )
    if day_col is None:
        st.error("Date/Day column not found. Columns available: " + ", ".join(df.columns))
        return None

    df = df.copy()
    df["Day"] = pd.to_datetime(df[day_col], errors="coerce")
    df = normalize_columns(df)

    for col in ["Spends", "Reach", "Frequency", "Clicks", "Conversions",
                "Total Leads DB", "New Leads DB", "Old Leads DB", "Impression"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("₹", "", regex=False)
                .str.replace("â‚¹", "", regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df[df["Day"].notna()].reset_index(drop=True)


# ── KPI computation ───────────────────────────────────────────────────────────

def compute_kpis(df):
    spend = df["Spends"].sum()
    leads = df["Total Leads DB"].sum()
    clicks = df["Clicks"].sum()
    impressions = df["Impression"].sum()
    new_leads = df["New Leads DB"].sum() if "New Leads DB" in df.columns else 0
    old_leads = df["Old Leads DB"].sum() if "Old Leads DB" in df.columns else 0
    return {
        "spend":     spend,
        "leads":     leads,
        "new_leads": new_leads,
        "old_leads": old_leads,
        "cpl":       spend / leads     if leads     else 0,
        "new_cpl":   spend / new_leads if new_leads else 0,
        "old_cpl":   spend / old_leads if old_leads else 0,
        "ctr":       (clicks / impressions * 100) if impressions else 0,
        "cpc":       spend / clicks if clicks else 0,
        "conv_rate": (leads / clicks * 100) if clicks else 0,
    }


def aggregate_by(df, group_col):
    """Group by a dimension and compute Spend, Leads, CPL, CTR."""
    if group_col not in df.columns:
        return pd.DataFrame()
    agg_spec = {
        "Spend":       ("Spends",         "sum"),
        "Leads":       ("Total Leads DB",  "sum"),
        "Clicks":      ("Clicks",          "sum"),
        "Impressions": ("Impression",      "sum"),
    }
    if "New Leads DB" in df.columns:
        agg_spec["New Leads"] = ("New Leads DB", "sum")
    if "Old Leads DB" in df.columns:
        agg_spec["Old Leads"] = ("Old Leads DB", "sum")
    if "Reach" in df.columns:
        agg_spec["Reach"] = ("Reach", "sum")

    result = (
        df.groupby(group_col, dropna=False)
        .agg(**agg_spec)
        .assign(
            CPL=lambda d: (d["Spend"] / d["Leads"].replace(0, np.nan)).round(2),
            CTR=lambda d: ((d["Clicks"] / d["Impressions"].replace(0, np.nan)) * 100).round(2),
        )
        .replace([np.inf, -np.inf], np.nan)
        .reset_index()
    )
    if "Reach" in result.columns:
        result["Frequency"] = (
            result["Impressions"] / result["Reach"].replace(0, np.nan)
        ).round(2)
    return result


# ── Sidebar filters ────────────────────────────────────────────────────────────

def sidebar_filters(df, prefix):
    st.sidebar.header(f"Filters — {prefix}")
    st.sidebar.caption(
        f"Rows: {len(df)} | {df['Day'].min().date()} → {df['Day'].max().date()}"
    )

    start = st.sidebar.date_input("Start Date", df["Day"].min(), key=f"start_{prefix}")
    end = st.sidebar.date_input("End Date", df["Day"].max(), key=f"end_{prefix}")
    fdf = df[
        (df["Day"] >= pd.Timestamp(start)) & (df["Day"] <= pd.Timestamp(end))
    ].copy()

    for col, label in [
        ("Campaign name", "Campaign"),
        ("Ad set name", "Ad Set"),
        ("Ad name", "Ad"),
    ]:
        if col in fdf.columns:
            opts = sorted(fdf[col].dropna().unique())
            sel = st.sidebar.multiselect(
                label, ["All"] + opts, default=["All"], key=f"{col}_{prefix}"
            )
            if "All" not in sel:
                fdf = fdf[fdf[col].isin(sel)]

    return fdf


# ── KPI cards ─────────────────────────────────────────────────────────────────

def render_kpi_cards(df, end_date):
    kpis = compute_kpis(df)
    period_end = pd.Timestamp(end_date)
    curr = df[df["Day"] >= (period_end - pd.Timedelta(days=6))]
    prev = df[
        (df["Day"] >= (period_end - pd.Timedelta(days=13)))
        & (df["Day"] < (period_end - pd.Timedelta(days=6)))
    ]
    ck, pk = compute_kpis(curr), compute_kpis(prev)

    def delta_html(key, lower_is_better=False):
        if pk[key] == 0:
            return ""
        pct = (ck[key] - pk[key]) / pk[key] * 100
        good = (pct < 0) if lower_is_better else (pct >= 0)
        color = "#4caf50" if good else "#f44336"
        arrow = "↑" if pct >= 0 else "↓"
        return f'<span style="color:{color};font-size:0.75rem">{arrow} {pct:+.1f}%</span>'

    row1_cards = [
        ("💰 Total Spend",  f"₹{kpis['spend']:,.0f}",     delta_html("spend")),
        ("📩 Total Leads",  f"{int(kpis['leads']):,}",     delta_html("leads")),
        ("🟢 New Leads",    f"{int(kpis['new_leads']):,}", ""),
        ("🟡 Old Leads",    f"{int(kpis['old_leads']):,}", ""),
        ("📉 Total CPL",    f"₹{kpis['cpl']:.1f}",        delta_html("cpl",     lower_is_better=True)),
    ]
    row2_cards = [
        ("🟢 New Lead CPL", f"₹{kpis['new_cpl']:.1f}",    delta_html("new_cpl", lower_is_better=True)),
        ("🟡 Old Lead CPL", f"₹{kpis['old_cpl']:.1f}",    delta_html("old_cpl", lower_is_better=True)),
        ("📊 CTR",          f"{kpis['ctr']:.2f}%",         delta_html("ctr")),
        ("💸 CPC",          f"₹{kpis['cpc']:.1f}",        delta_html("cpc",     lower_is_better=True)),
        ("🔄 Conv Rate",    f"{kpis['conv_rate']:.2f}%",   delta_html("conv_rate")),
    ]

    st.markdown("#### Key Performance Indicators")
    for cards in [row1_cards, row2_cards]:
        cols = st.columns(5)
        for col, (label, value, delta) in zip(cols, cards):
            with col:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">{label}</div>'
                    f'<div class="metric-value">{value}</div>'
                    f'<div class="metric-delta">{delta}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    st.markdown("<br>", unsafe_allow_html=True)


# ── Charts ────────────────────────────────────────────────────────────────────

def render_charts(df):
    # Spend vs Leads — dual-axis line chart
    st.markdown('<p class="section-header">📈 Spend vs Leads Over Time</p>', unsafe_allow_html=True)
    daily = (
        df.groupby("Day")
        .agg(Spend=("Spends", "sum"), Leads=("Total Leads DB", "sum"))
        .reset_index()
    )
    fig_dual = go.Figure()
    fig_dual.add_trace(
        go.Scatter(
            x=daily["Day"], y=daily["Spend"],
            name="Spend (₹)", line=dict(color="#1e3c72", width=2.5),
            yaxis="y1",
        )
    )
    fig_dual.add_trace(
        go.Scatter(
            x=daily["Day"], y=daily["Leads"],
            name="Leads", line=dict(color="#e74c3c", width=2.5, dash="dot"),
            yaxis="y2",
        )
    )
    fig_dual.update_layout(
        yaxis=dict(title="Spend (₹)", side="left", showgrid=False),
        yaxis2=dict(title="Leads", side="right", overlaying="y", showgrid=False),
        legend=dict(orientation="h", y=1.12),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=30, b=20),
        height=340,
    )
    st.plotly_chart(fig_dual, use_container_width=True)

    col1, col2 = st.columns(2)

    # CPL comparison bar chart by campaign
    with col1:
        st.markdown('<p class="section-header">💡 CPL by Campaign</p>', unsafe_allow_html=True)
        if "Campaign name" in df.columns:
            camp = (
                aggregate_by(df, "Campaign name")
                .dropna(subset=["CPL"])
                .sort_values("CPL")
                .head(12)
            )
            fig_cpl = px.bar(
                camp, x="Campaign name", y="CPL",
                color="CPL",
                color_continuous_scale="RdYlGn_r",
                labels={"CPL": "Cost per Lead (₹)", "Campaign name": "Campaign"},
            )
            fig_cpl.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=30, b=90),
                height=360,
                xaxis_tickangle=-35,
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_cpl, use_container_width=True)

    # Daily spend bar chart
    with col2:
        st.markdown('<p class="section-header">📊 Daily Spend</p>', unsafe_allow_html=True)
        spend_daily = df.groupby("Day")["Spends"].sum().reset_index()
        fig_spend = px.bar(
            spend_daily, x="Day", y="Spends",
            labels={"Spends": "Spend (₹)", "Day": "Date"},
            color_discrete_sequence=["#2a5298"],
        )
        fig_spend.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=30, b=20),
            height=360,
        )
        st.plotly_chart(fig_spend, use_container_width=True)


# ── Best / Worst performers ───────────────────────────────────────────────────

def render_best_worst(df, tab_key):
    # metric → (sort column, best ascending, worst ascending)
    _SORT_MAP = {
        "CPL":   ("CPL",   True,  False),
        "Leads": ("Leads", False, True),
        "Spend": ("Spend", False, True),
        "CTR":   ("CTR",   False, True),
    }
    _DISP_COLS = ["Spend", "Leads", "CPL", "CTR"]

    # ── Creative Performance ──────────────────────────────────────────────────
    if "Ad name" in df.columns:
        st.markdown("---")
        st.markdown("#### Creative Performance")

        fd1, fd2, fd3, fd4, fd5, fd6 = st.columns([1, 1, 2, 2, 2, 1])
        cr_df = df.copy()

        with fd1:
            cr_start = st.date_input(
                "From", value=cr_df["Day"].min().date(),
                min_value=cr_df["Day"].min().date(), max_value=cr_df["Day"].max().date(),
                key=f"cr_start_{tab_key}",
            )
        with fd2:
            cr_end = st.date_input(
                "To", value=cr_df["Day"].max().date(),
                min_value=cr_df["Day"].min().date(), max_value=cr_df["Day"].max().date(),
                key=f"cr_end_{tab_key}",
            )
        cr_df = cr_df[
            (cr_df["Day"] >= pd.Timestamp(cr_start)) &
            (cr_df["Day"] <= pd.Timestamp(cr_end))
        ]

        with fd3:
            if "Campaign name" in cr_df.columns:
                opts = sorted(cr_df["Campaign name"].dropna().unique())
                sel = st.multiselect("Campaign", ["All"] + opts, default=["All"],
                                     key=f"cr_camp_{tab_key}")
                if "All" not in sel:
                    cr_df = cr_df[cr_df["Campaign name"].isin(sel)]

        with fd4:
            if "Ad set name" in cr_df.columns:
                opts = sorted(cr_df["Ad set name"].dropna().unique())
                sel = st.multiselect("Ad Set", ["All"] + opts, default=["All"],
                                     key=f"cr_adset_{tab_key}")
                if "All" not in sel:
                    cr_df = cr_df[cr_df["Ad set name"].isin(sel)]

        with fd5:
            cr_metrics = st.multiselect("Sort by", ["CPL", "Leads", "Spend", "CTR"],
                                        default=["CPL"], key=f"cr_sort_{tab_key}")
            if not cr_metrics:
                cr_metrics = ["CPL"]

        with fd6:
            cr_top_n = st.selectbox("Show top", [5, 10, 15, 20], key=f"cr_topn_{tab_key}")

        creatives = aggregate_by(cr_df, "Ad name").dropna(subset=["CPL"])
        if not creatives.empty:
            sort_cols_b = [_SORT_MAP[m][0] for m in cr_metrics]
            sort_asc_b  = [_SORT_MAP[m][1] for m in cr_metrics]
            sort_cols_w = [_SORT_MAP[m][0] for m in cr_metrics]
            sort_asc_w  = [_SORT_MAP[m][2] for m in cr_metrics]
            label = ", ".join(cr_metrics)
            spend_med = creatives["Spend"].median()

            best_cr  = (creatives[creatives["Spend"] >= spend_med]
                        .sort_values(sort_cols_b, ascending=sort_asc_b).head(cr_top_n))
            worst_cr = (creatives[creatives["Spend"] > 0]
                        .sort_values(sort_cols_w, ascending=sort_asc_w).head(cr_top_n))

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**🏆 Top {cr_top_n} Best Creatives** — by {label}")
                cols = ["Ad name"] + [c for c in _DISP_COLS if c in best_cr.columns]
                st.dataframe(best_cr[cols].reset_index(drop=True), use_container_width=True)
            with c2:
                st.markdown(f"**📉 Top {cr_top_n} Worst Creatives** — by {label}")
                cols = ["Ad name"] + [c for c in _DISP_COLS if c in worst_cr.columns]
                st.dataframe(worst_cr[cols].reset_index(drop=True), use_container_width=True)
        else:
            st.info("No creative data available for the selected filters.")

    # ── Campaign Performance ──────────────────────────────────────────────────
    if "Campaign name" in df.columns:
        st.markdown("#### Campaign Performance")

        fp1, fp2, fp3, fp4, fp5, fp6 = st.columns([1, 1, 2, 2, 2, 1])
        camp_df = df.copy()

        with fp1:
            camp_start = st.date_input(
                "From", value=camp_df["Day"].min().date(),
                min_value=camp_df["Day"].min().date(), max_value=camp_df["Day"].max().date(),
                key=f"camp_start_{tab_key}",
            )
        with fp2:
            camp_end = st.date_input(
                "To", value=camp_df["Day"].max().date(),
                min_value=camp_df["Day"].min().date(), max_value=camp_df["Day"].max().date(),
                key=f"camp_end_{tab_key}",
            )
        camp_df = camp_df[
            (camp_df["Day"] >= pd.Timestamp(camp_start)) &
            (camp_df["Day"] <= pd.Timestamp(camp_end))
        ]

        with fp3:
            if "Campaign name" in camp_df.columns:
                opts = sorted(camp_df["Campaign name"].dropna().unique())
                sel = st.multiselect("Campaign", ["All"] + opts, default=["All"],
                                     key=f"camp_camp_{tab_key}")
                if "All" not in sel:
                    camp_df = camp_df[camp_df["Campaign name"].isin(sel)]

        with fp4:
            if "Ad set name" in camp_df.columns:
                opts = sorted(camp_df["Ad set name"].dropna().unique())
                sel = st.multiselect("Ad Set", ["All"] + opts, default=["All"],
                                     key=f"camp_adset_{tab_key}")
                if "All" not in sel:
                    camp_df = camp_df[camp_df["Ad set name"].isin(sel)]

        with fp5:
            camp_metrics = st.multiselect("Sort by", ["CPL", "Leads", "Spend", "CTR"],
                                          default=["CPL"], key=f"camp_sort_{tab_key}")
            if not camp_metrics:
                camp_metrics = ["CPL"]

        with fp6:
            camp_top_n = st.selectbox("Show top", [5, 10, 15, 20], key=f"camp_topn_{tab_key}")

        campaigns = aggregate_by(camp_df, "Campaign name").dropna(subset=["CPL"])
        if not campaigns.empty:
            sort_cols_b = [_SORT_MAP[m][0] for m in camp_metrics]
            sort_asc_b  = [_SORT_MAP[m][1] for m in camp_metrics]
            sort_cols_w = [_SORT_MAP[m][0] for m in camp_metrics]
            sort_asc_w  = [_SORT_MAP[m][2] for m in camp_metrics]
            label = ", ".join(camp_metrics)
            spend_med = campaigns["Spend"].median()

            best_camps  = (campaigns[campaigns["Spend"] >= spend_med]
                           .sort_values(sort_cols_b, ascending=sort_asc_b).head(camp_top_n))
            worst_camps = (campaigns[campaigns["Spend"] > 0]
                           .sort_values(sort_cols_w, ascending=sort_asc_w).head(camp_top_n))

            c3, c4 = st.columns(2)
            with c3:
                st.markdown(f"**🏆 Top {camp_top_n} Best Campaigns** — by {label}")
                cols = ["Campaign name"] + [c for c in _DISP_COLS if c in best_camps.columns]
                st.dataframe(best_camps[cols].reset_index(drop=True), use_container_width=True)
            with c4:
                st.markdown(f"**📉 Top {camp_top_n} Worst Campaigns** — by {label}")
                cols = ["Campaign name"] + [c for c in _DISP_COLS if c in worst_camps.columns]
                st.dataframe(worst_camps[cols].reset_index(drop=True), use_container_width=True)
        else:
            st.info("No campaign data available for the selected filters.")


# ── Weekly comparison ─────────────────────────────────────────────────────────

def render_weekly_comparison(df, tab_key):
    max_day    = df["Day"].max()
    curr_start = max_day - pd.Timedelta(days=6)
    prev_start = max_day - pd.Timedelta(days=13)
    prev_end   = max_day - pd.Timedelta(days=7)

    fmt = lambda d: f"{d.day} {d.strftime('%b %Y')}"
    st.markdown(
        f"#### 📅 Current Week vs Last Week"
        f"<span style='font-size:0.82rem; color:#888; font-weight:400; margin-left:12px;'>"
        f"Current: {fmt(curr_start)} – {fmt(max_day)}"
        f"&nbsp;&nbsp;|&nbsp;&nbsp;"
        f"Last week: {fmt(prev_start)} – {fmt(prev_end)}"
        f"</span>",
        unsafe_allow_html=True,
    )

    # Dimension filters
    wf1, wf2, wf3 = st.columns(3)
    fdf = df.copy()

    with wf1:
        if "Campaign name" in fdf.columns:
            opts = sorted(fdf["Campaign name"].dropna().unique())
            sel = st.multiselect("Campaign Name", ["All"] + opts, default=["All"],
                                 key=f"wk_camp_{tab_key}")
            if "All" not in sel:
                fdf = fdf[fdf["Campaign name"].isin(sel)]

    with wf2:
        if "Ad set name" in fdf.columns:
            opts = sorted(fdf["Ad set name"].dropna().unique())
            sel = st.multiselect("Ad Set Name", ["All"] + opts, default=["All"],
                                 key=f"wk_adset_{tab_key}")
            if "All" not in sel:
                fdf = fdf[fdf["Ad set name"].isin(sel)]

    with wf3:
        if "Ad name" in fdf.columns:
            opts = sorted(fdf["Ad name"].dropna().unique())
            sel = st.multiselect("Ad Name", ["All"] + opts, default=["All"],
                                 key=f"wk_ad_{tab_key}")
            if "All" not in sel:
                fdf = fdf[fdf["Ad name"].isin(sel)]

    curr = fdf[fdf["Day"] >= curr_start]
    prev = fdf[(fdf["Day"] >= prev_start) & (fdf["Day"] <= prev_end)]
    ck, pk = compute_kpis(curr), compute_kpis(prev)

    def pct(c, p):
        return f"{(c - p) / p * 100:+.1f}%" if p else "N/A"

    rows = [
        ("Spend (₹)", f"₹{ck['spend']:,.0f}", f"₹{pk['spend']:,.0f}", pct(ck["spend"], pk["spend"])),
        ("Leads", f"{int(ck['leads']):,}", f"{int(pk['leads']):,}", pct(ck["leads"], pk["leads"])),
        ("CPL (₹)", f"₹{ck['cpl']:.1f}", f"₹{pk['cpl']:.1f}", pct(ck["cpl"], pk["cpl"])),
        ("CTR (%)", f"{ck['ctr']:.2f}%", f"{pk['ctr']:.2f}%", pct(ck["ctr"], pk["ctr"])),
        ("CPC (₹)", f"₹{ck['cpc']:.1f}", f"₹{pk['cpc']:.1f}", pct(ck["cpc"], pk["cpc"])),
        ("Conv Rate (%)", f"{ck['conv_rate']:.2f}%", f"{pk['conv_rate']:.2f}%", pct(ck["conv_rate"], pk["conv_rate"])),
    ]
    st.dataframe(
        pd.DataFrame(rows, columns=["Metric", "Current Week", "Last Week", "% Change"]),
        use_container_width=True,
    )


# ── Data table + CSV download ─────────────────────────────────────────────────

def render_data_table(df, tab_key):
    st.markdown("#### 📋 Data Table")
    tdf = df.copy()

    # Ensure optional columns exist
    for col in ["Reach", "Conversions", "New Leads DB", "Old Leads DB"]:
        if col not in tdf.columns:
            tdf[col] = 0

    # Frequency = Impressions / Reach (row-level, for display only)
    tdf["Frequency"] = (
        tdf["Impression"] / tdf["Reach"].replace(0, np.nan)
    ).round(2).fillna(0)

    # Derived metrics
    tdf["CPL"]          = (tdf["Spends"] / tdf["Total Leads DB"].replace(0, np.nan)).round(2)
    tdf["CPC"]          = (tdf["Spends"] / tdf["Clicks"].replace(0, np.nan)).round(2)
    tdf["CTR (%)"]      = ((tdf["Clicks"] / tdf["Impression"].replace(0, np.nan)) * 100).round(2)
    tdf["Conv Rate (%)"]= ((tdf["Total Leads DB"] / tdf["Clicks"].replace(0, np.nan)) * 100).round(2)
    tdf = tdf.replace([np.inf, -np.inf], 0)

    # Rename raw column names for display
    tdf = tdf.rename(columns={"Spends": "Spend", "Impression": "Impressions"})

    wanted = [
        "Campaign name", "Ad set name", "Ad name", "Day",
        "Spend", "Reach", "Impressions", "Frequency", "Clicks", "Conversions",
        "New Leads DB", "Old Leads DB", "Total Leads DB",
        "CPL", "CTR (%)", "CPC", "Conv Rate (%)",
    ]
    cols = [c for c in wanted if c in tdf.columns]
    display = tdf[cols]

    # ── Total row with correct aggregation formulas ───────────────────────────
    num_cols   = display.select_dtypes(include="number").columns.tolist()
    total_vals = display[num_cols].sum()

    total_spend       = total_vals.get("Spend", 0)
    total_impressions = total_vals.get("Impressions", 0)
    total_reach       = total_vals.get("Reach", 0)
    total_clicks      = total_vals.get("Clicks", 0)
    total_leads       = total_vals.get("Total Leads DB", 0)

    total_row = {c: "" for c in cols}
    # Label
    label_col = next((c for c in ["Campaign name", "Ad set name", "Ad name", "Day"] if c in cols), cols[0])
    total_row[label_col] = "TOTAL"
    # Summable columns
    for c in ["Spend", "Reach", "Impressions", "Clicks", "Conversions",
              "New Leads DB", "Old Leads DB", "Total Leads DB"]:
        if c in cols:
            total_row[c] = round(total_vals[c], 2)
    # Derived — must use aggregated sums, not average of row values
    if total_reach:
        total_row["Frequency"]    = round(total_impressions / total_reach, 2)
    if total_leads:
        total_row["CPL"]          = round(total_spend / total_leads, 2)
    if total_impressions:
        total_row["CTR (%)"]      = round(total_clicks / total_impressions * 100, 2)
    if total_clicks:
        total_row["CPC"]          = round(total_spend / total_clicks, 2)
        total_row["Conv Rate (%)"]= round(total_leads / total_clicks * 100, 2)

    total_df = pd.DataFrame([total_row])

    # Number format spec shared by both tables
    fmt = {}
    for c in cols:
        if c in ("Spend", "CPL", "CPC"):
            fmt[c] = "₹{:,.2f}"
        elif c in ("Reach", "Impressions", "Clicks", "Conversions",
                   "New Leads DB", "Old Leads DB", "Total Leads DB"):
            fmt[c] = "{:,.0f}"
        elif c == "Frequency":
            fmt[c] = "{:.2f}"
        elif c in ("CTR (%)", "Conv Rate (%)"):
            fmt[c] = "{:.2f}%"
    # Only format numeric cells; text cells (Campaign name etc.) stay as-is
    total_fmt = {k: v for k, v in fmt.items() if total_row.get(k, "") != ""}

    # Render total row as a pinned header table (always visible above scroll)
    styled_total = (
        total_df.style
        .format(total_fmt, na_rep="—")
        .set_properties(**{
            "background-color": "#1e3c72",
            "color": "white",
            "font-weight": "bold",
        })
        .hide(axis="index")
    )
    st.dataframe(styled_total, use_container_width=True, hide_index=True)

    # Scrollable data rows below — same format spec
    styled_display = display.style.format(fmt, na_rep="—")
    st.dataframe(styled_display, use_container_width=True, hide_index=True, height=400)

    csv_bytes = pd.concat([total_df, display], ignore_index=True).to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download filtered data as CSV",
        data=csv_bytes,
        file_name=f"marketing_data_{tab_key}.csv",
        mime="text/csv",
        key=f"download_{tab_key}",
    )


# ── Day-by-day trend matrix ───────────────────────────────────────────────────

def render_trend_matrix(df, tab_key):
    st.markdown("#### 📆 Day-by-Day Trend Matrix")

    tf1, tf2, tf3 = st.columns(3)
    tdf = df.copy()

    with tf1:
        if "Campaign name" in tdf.columns:
            opts = sorted(tdf["Campaign name"].dropna().unique())
            sel = st.multiselect("Campaign Name", ["All"] + opts, default=["All"],
                                 key=f"tm_camp_{tab_key}")
            if "All" not in sel:
                tdf = tdf[tdf["Campaign name"].isin(sel)]

    with tf2:
        if "Ad set name" in tdf.columns:
            opts = sorted(tdf["Ad set name"].dropna().unique())
            sel = st.multiselect("Ad Set Name", ["All"] + opts, default=["All"],
                                 key=f"tm_adset_{tab_key}")
            if "All" not in sel:
                tdf = tdf[tdf["Ad set name"].isin(sel)]

    with tf3:
        if "Ad name" in tdf.columns:
            opts = sorted(tdf["Ad name"].dropna().unique())
            sel = st.multiselect("Ad Name", ["All"] + opts, default=["All"],
                                 key=f"tm_ad_{tab_key}")
            if "All" not in sel:
                tdf = tdf[tdf["Ad name"].isin(sel)]

    # Daily aggregation — sort ascending so pct_change compares to previous day
    agg_spec = {
        "Spend":       ("Spends",         "sum"),
        "Impressions": ("Impression",     "sum"),
        "Clicks":      ("Clicks",         "sum"),
        "Leads":       ("Total Leads DB", "sum"),
    }
    if "Reach" in tdf.columns:
        agg_spec["Reach"] = ("Reach", "sum")

    daily = (
        tdf.groupby("Day")
        .agg(**agg_spec)
        .assign(
            CPM=lambda d: (d["Spend"] / d["Impressions"].replace(0, np.nan) * 1000).round(2),
            CTR=lambda d: (d["Clicks"] / d["Impressions"].replace(0, np.nan) * 100).round(2),
            CPC=lambda d: (d["Spend"] / d["Clicks"].replace(0, np.nan)).round(2),
            CPL=lambda d: (d["Spend"] / d["Leads"].replace(0, np.nan)).round(2),
        )
        .replace([np.inf, -np.inf], np.nan)
        .reset_index()
        .sort_values("Day")
    )

    if daily.empty:
        st.info("No data available for the selected filters.")
        return

    if "Reach" in daily.columns:
        daily["Frequency"] = (
            daily["Impressions"] / daily["Reach"].replace(0, np.nan)
        ).round(2)

    # ── Date filter ───────────────────────────────────────────────────────────
    date_min = daily["Day"].min().date()
    date_max = daily["Day"].max().date()
    dc1, dc2 = st.columns(2)
    with dc1:
        start_date = st.date_input(
            "📅 Start Date", value=date_min,
            min_value=date_min, max_value=date_max,
            key=f"tm_start_{tab_key}",
        )
    with dc2:
        end_date = st.date_input(
            "📅 End Date", value=date_max,
            min_value=date_min, max_value=date_max,
            key=f"tm_end_{tab_key}",
        )
    if start_date > end_date:
        st.warning("Start date cannot be after end date.")
        return
    daily = daily[
        (daily["Day"].dt.date >= start_date) &
        (daily["Day"].dt.date <= end_date)
    ]
    if daily.empty:
        st.info("No data for the selected date range.")
        return

    # Day-over-day % change
    for col in ["Spend", "Impressions", "CPM", "Clicks", "Frequency", "CTR", "CPC", "Leads", "CPL"]:
        if col in daily.columns:
            daily[f"Δ {col}"] = daily[col].pct_change().mul(100).round(1)

    # Newest first for display
    daily = daily.sort_values("Day", ascending=False)
    daily.insert(0, "Date", daily["Day"].apply(
        lambda d: f"{d.day} {d.strftime('%b %Y')}" if pd.notna(d) else ""
    ))

    col_order = [
        "Date",
        "Spend",       "Δ Spend",
        "Impressions", "Δ Impressions",
        "CPM",         "Δ CPM",
        "Clicks",      "Δ Clicks",
        "Frequency",   "Δ Frequency",
        "CTR",         "Δ CTR",
        "CPC",         "Δ CPC",
        "Leads",       "Δ Leads",
        "CPL",         "Δ CPL",
    ]
    col_order = [c for c in col_order if c in daily.columns]

    rename_map = {
        "CTR":         "CTR (%)",
        "Δ CTR":       "Δ CTR (%)",
        "Frequency":   "Ad Frequency",
        "Δ Frequency": "Δ Ad Frequency",
    }
    matrix = daily[col_order].rename(columns=rename_map)

    fmt = {
        "Spend":          "₹{:,.0f}",  "Δ Spend":          "{:+.1f}%",
        "Impressions":    "{:,.0f}",   "Δ Impressions":    "{:+.1f}%",
        "CPM":            "₹{:.2f}",   "Δ CPM":            "{:+.1f}%",
        "Clicks":         "{:,.0f}",   "Δ Clicks":         "{:+.1f}%",
        "Ad Frequency":   "{:.2f}",    "Δ Ad Frequency":   "{:+.1f}%",
        "CTR (%)":        "{:.2f}%",   "Δ CTR (%)":        "{:+.1f}%",
        "CPC":            "₹{:.1f}",   "Δ CPC":            "{:+.1f}%",
        "Leads":          "{:,.0f}",   "Δ Leads":          "{:+.1f}%",
        "CPL":            "₹{:.1f}",   "Δ CPL":            "{:+.1f}%",
    }
    fmt = {k: v for k, v in fmt.items() if k in matrix.columns}

    # Per-column colour gradient (direction-aware)
    gradient_cfg = [
        ("Spend",          "Blues"),    ("Δ Spend",          "Blues"),
        ("Impressions",    "Blues"),    ("Δ Impressions",    "Blues"),
        ("CPM",            "RdYlGn_r"), ("Δ CPM",            "RdYlGn_r"),
        ("Clicks",         "Blues"),    ("Δ Clicks",         "Blues"),
        ("Ad Frequency",   "RdYlGn_r"), ("Δ Ad Frequency",  "RdYlGn_r"),
        ("CTR (%)",        "RdYlGn"),   ("Δ CTR (%)",        "RdYlGn"),
        ("CPC",            "RdYlGn_r"), ("Δ CPC",            "RdYlGn_r"),
        ("Leads",          "RdYlGn"),   ("Δ Leads",          "RdYlGn"),
        ("CPL",            "RdYlGn_r"), ("Δ CPL",            "RdYlGn_r"),
    ]

    # ── Column filter (below table) ──────────────────────────────────────────
    metric_options = [c for c in [
        "Spend", "Impressions", "CPM", "Clicks",
        "Ad Frequency", "CTR (%)", "CPC", "Leads", "CPL",
    ] if c in matrix.columns]

    selected_metrics = st.multiselect(
        "📊 Select columns",
        options=metric_options,
        default=metric_options,
        key=f"tm_cols_{tab_key}",
    )

    if selected_metrics:
        keep_cols = ["Date"]
        for m in selected_metrics:
            keep_cols.append(m)
            delta = f"Δ {m}" if f"Δ {m}" in matrix.columns else None
            if delta:
                keep_cols.append(delta)
        matrix = matrix[[c for c in keep_cols if c in matrix.columns]]
        fmt    = {k: v for k, v in fmt.items() if k in matrix.columns}
        gradient_cfg = [(c, cm) for c, cm in gradient_cfg if c in matrix.columns]

    styled = matrix.style.format(fmt, na_rep="—")
    for col, cmap in gradient_cfg:
        if col in matrix.columns and matrix[col].notna().any():
            styled = styled.background_gradient(cmap=cmap, subset=[col], axis=0)

    st.dataframe(styled, use_container_width=True, height=420,
                 hide_index=True)


# ── Tab renderers ─────────────────────────────────────────────────────────────

def render_tab(tab_name, sheet_url, upload_key):
    st.header(tab_name)
    df, _source = load_data(sheet_url, upload_key)
    if df is None:
        return
    df = clean_data(df)
    if df is None or df.empty:
        st.warning("No valid data found.")
        return

    fdf = sidebar_filters(df, tab_name.replace(" ", "_"))
    if fdf.empty:
        st.warning("No data in the selected date range.")
        return

    render_kpi_cards(fdf, fdf["Day"].max())
    render_charts(fdf)
    render_best_worst(fdf, tab_key=upload_key)
    render_weekly_comparison(fdf, tab_key=upload_key)
    render_data_table(fdf, tab_key=upload_key)
    render_trend_matrix(fdf, tab_key=upload_key)


def render_combined_tab():
    st.header("Combined: Google + Meta Ads")
    meta_raw = fetch_sheet(META_SHEET_URL)
    google_raw = fetch_sheet(GOOGLE_ADS_SHEET_URL)

    parts = []
    for raw, label in [(meta_raw, "Meta Ads"), (google_raw, "Google Ads")]:
        if raw is None:
            st.warning(f"Could not load {label}.")
            continue
        cleaned = clean_data(raw)
        if cleaned is not None:
            cleaned["Source"] = label
            parts.append(cleaned)

    if not parts:
        st.error("No data available for either platform.")
        return

    combined = pd.concat(parts, ignore_index=True, sort=False)
    for col in ["Spends", "Total Leads DB", "New Leads DB", "Old Leads DB", "Clicks", "Impression"]:
        if col not in combined.columns:
            combined[col] = 0

    fdf = sidebar_filters(combined, "Combined")
    if fdf.empty:
        st.warning("No data in the selected date range.")
        return

    # Platform spend breakdown
    if "Source" in fdf.columns:
        src_spend = fdf.groupby("Source")["Spends"].sum().reset_index()
        fig_pie = px.pie(
            src_spend, values="Spends", names="Source",
            title="Spend by Platform",
            color_discrete_sequence=["#1e3c72", "#e74c3c"],
        )
        fig_pie.update_layout(
            height=260, margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        _, mid, _ = st.columns([1, 1, 1])
        with mid:
            st.plotly_chart(fig_pie, use_container_width=True)

    render_kpi_cards(fdf, fdf["Day"].max())
    render_charts(fdf)
    render_best_worst(fdf, tab_key="combined")
    render_weekly_comparison(fdf, tab_key="combined")
    render_data_table(fdf, tab_key="combined")
    render_trend_matrix(fdf, tab_key="combined")


# ── Entry point ───────────────────────────────────────────────────────────────

tabs = st.tabs(["📘 Meta Ads", "🔍 Google Ads", "🔄 Combined"])
with tabs[0]:
    render_tab("Meta Ads", META_SHEET_URL, "upload_meta")
with tabs[1]:
    render_tab("Google Ads", GOOGLE_ADS_SHEET_URL, "upload_google")
with tabs[2]:
    render_combined_tab()
