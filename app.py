import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

st.set_page_config(
    layout="wide",
    page_title="🚀 Marketing Analytics Dashboard",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(45deg, #ff6b6b, #ffa500, #ffff00, #32cd32, #1e90ff, #9370db, #ff1493);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        animation: rainbow 3s ease-in-out infinite;
        display: inline-block;
        padding: 10px 20px;
        border-radius: 15px;
        background-image: linear-gradient(45deg, #ff6b6b, #ffa500, #ffff00, #32cd32, #1e90ff, #9370db, #ff1493);
        background-size: 400% 400%;
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    @keyframes rainbow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 5px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 10px 0;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .positive-change {
        color: #00ff00;
        font-weight: bold;
    }
    .negative-change {
        color: #ff4444;
        font-weight: bold;
    }
    .sidebar-header {
        background: linear-gradient(45deg, #ff6b6b, #ffa500);
        color: white;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .chart-container {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin: 10px 0;
    }
    .dataframe-container {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #1e3c72;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header"><span class="emoji">🚀</span> <span class="title-text">Marketing Analytics Dashboard</span></h1>', unsafe_allow_html=True)

META_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/14KA90yocZci3ZJud3XYiM2-78HZFF3fcTbHpYNr_bY8/export?format=csv&gid=838145140"
)
GOOGLE_ADS_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/1HGOWbDKAZ7VxAK-1xeBhp7RYGcwg_7fkpmdShut1DyA/export?format=csv&gid=1730280898"
)


def load_data(sheet_url, upload_key):
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"], key=upload_key)
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            df.columns = df.columns.str.strip()
            return df, "Uploaded CSV"
        except Exception:
            st.warning("Could not read uploaded CSV. Please upload a valid CSV file.")
            return None, None

    try:
        df = pd.read_csv(sheet_url)
        df.columns = df.columns.str.strip()
        st.success("✅ Loaded daily Google Sheet data")
        return df, "Google Sheet"
    except Exception:
        st.warning("Could not load Google Sheet automatically. Upload a CSV to continue.")
        return None, None


def load_sheet_data(sheet_url, source_name):
    try:
        df = pd.read_csv(sheet_url)
        df.columns = df.columns.str.strip()
        return df, source_name
    except Exception:
        st.warning(f"Could not load {source_name} automatically.")
        return None, None


def normalize_columns(df):
    column_map = {
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
        "date": "Date"
    }
    return df.rename(columns={col: column_map.get(col.lower(), col) for col in df.columns})


def clean_data(df):
    day_col = next(
        (
            col for col in df.columns
            if "day" in col.lower() or "date" in col.lower()
        ),
        None
    )
    if day_col is None:
        st.error("❌ Date/Day column not found")
        st.write(df.columns)
        return None

    df = df.copy()
    if day_col.lower() == "day":
        df.rename(columns={day_col: "Day"}, inplace=True)
        df["Day"] = pd.to_datetime(df["Day"], errors="coerce")
    else:
        df["Day"] = pd.to_datetime(df[day_col], errors="coerce")
        if day_col.lower() != "date":
            df["Date"] = df[day_col]

    df = normalize_columns(df)

    numeric_cols = ["Spends", "Total Leads DB", "New Leads DB", "Old Leads DB", "Clicks", "Impression"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("₹", "", regex=False)
                .str.replace("â‚¹", "", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df[df["Day"].notna()]


def render_combined_dashboard():
    st.header("Google + Meta Ads Dashboard")

    meta_df, _ = load_sheet_data(META_SHEET_URL, "Meta Ads Sheet")
    google_df, _ = load_sheet_data(GOOGLE_ADS_SHEET_URL, "Google Ads Sheet")

    if meta_df is None and google_df is None:
        st.error("❌ Could not load Meta Ads and Google Ads data.")
        return
    if meta_df is None:
        st.warning("⚠️ Meta Ads data could not be loaded.")
    if google_df is None:
        st.warning("⚠️ Google Ads data could not be loaded.")

    combined_parts = []
    if meta_df is not None:
        meta_clean = clean_data(meta_df)
        if meta_clean is not None:
            meta_clean["Source"] = "Meta Ads"
            combined_parts.append(meta_clean)
    if google_df is not None:
        google_clean = clean_data(google_df)
        if google_clean is not None:
            google_clean["Source"] = "Google Ads"
            combined_parts.append(google_clean)

    if not combined_parts:
        st.warning("No combined data available")
        return

    combined_df = pd.concat(combined_parts, ignore_index=True, sort=False)

    if "Date" in combined_df.columns:
        combined_df["Date"] = combined_df["Date"].fillna(combined_df["Day"].dt.date)
    else:
        combined_df["Date"] = combined_df["Day"].dt.date

    for col in ["Spends", "Total Leads DB", "New Leads DB", "Old Leads DB", "Clicks", "Impression"]:
        if col not in combined_df.columns:
            combined_df[col] = 0

    sidebar_prefix = "Google_Meta"
    st.sidebar.markdown("**Google + Meta Ads Data source:** Combined Google + Meta")
    st.sidebar.markdown(
        f"Rows: {len(combined_df)}  \nDate range: {combined_df['Day'].min().date()} - {combined_df['Day'].max().date()}"
    )
    st.sidebar.header("📅 Filters - Google + Meta Ads")

    start_date = st.sidebar.date_input(
        "Start Date",
        combined_df["Day"].min(),
        key=f"start_{sidebar_prefix}"
    )
    end_date = st.sidebar.date_input(
        "End Date",
        combined_df["Day"].max(),
        key=f"end_{sidebar_prefix}"
    )

    filtered_df = combined_df[
        (combined_df["Day"] >= pd.to_datetime(start_date)) &
        (combined_df["Day"] <= pd.to_datetime(end_date))
    ]

    if "Campaign name" in filtered_df.columns:
        campaigns = sorted(filtered_df["Campaign name"].dropna().unique())
        selected_campaigns = st.sidebar.multiselect(
            "Campaign",
            ["All"] + campaigns,
            default=["All"],
            key=f"campaign_{sidebar_prefix}"
        )
        if "All" not in selected_campaigns:
            filtered_df = filtered_df[filtered_df["Campaign name"].isin(selected_campaigns)]

    if "Ad set name" in filtered_df.columns:
        adsets = sorted(filtered_df["Ad set name"].dropna().unique())
        selected_adsets = st.sidebar.multiselect(
            "Ad Set",
            ["All"] + adsets,
            default=["All"],
            key=f"adset_{sidebar_prefix}"
        )
        if "All" not in selected_adsets:
            filtered_df = filtered_df[filtered_df["Ad set name"].isin(selected_adsets)]

    if "Ad name" in filtered_df.columns:
        ads = sorted(filtered_df["Ad name"].dropna().unique())
        selected_ads = st.sidebar.multiselect(
            "Ad",
            ["All"] + ads,
            default=["All"],
            key=f"ad_{sidebar_prefix}"
        )
        if "All" not in selected_ads:
            filtered_df = filtered_df[filtered_df["Ad name"].isin(selected_ads)]

    ranking_metrics = st.sidebar.multiselect(
        "Top Performers Ranking Metrics",
        ["Leads", "CPL", "CTR", "Spend"],
        default=["Leads"],
        help="Choose one or more metrics to rank top creatives and campaigns. Lower CPL is better; higher others are better.",
        key=f"ranking_{sidebar_prefix}"
    )

    worst_metrics = st.sidebar.multiselect(
        "Worst Creatives Metrics",
        ["Leads", "CPL", "CTR", "Spend"],
        default=["CPL"],
        help="Choose one or more metrics to identify worst-performing creatives.",
        key=f"worst_{sidebar_prefix}"
    )

    if not ranking_metrics:
        ranking_metrics = ["Leads"]
    if not worst_metrics:
        worst_metrics = ["CPL"]

    if filtered_df.empty:
        st.warning("No data available")
        return

    spend = filtered_df["Spends"].sum()
    leads = filtered_df["Total Leads DB"].sum()
    new_leads = filtered_df["New Leads DB"].sum() if "New Leads DB" in filtered_df.columns else 0
    old_leads = filtered_df["Old Leads DB"].sum() if "Old Leads DB" in filtered_df.columns else 0
    clicks = filtered_df["Clicks"].sum()
    impressions = filtered_df["Impression"].sum()

    cpl = spend / leads if leads != 0 else 0
    ctr = (clicks / impressions * 100) if impressions != 0 else 0
    cpc = spend / clicks if clicks != 0 else 0
    conversion_rate = (leads / clicks * 100) if clicks != 0 else 0

    # Enhanced Key Metrics with Custom Cards
    st.markdown("### 📊 Key Performance Indicators")

    # Calculate week-over-week changes for metrics
    period_end = pd.to_datetime(end_date)
    current_week = filtered_df[filtered_df["Day"] >= (period_end - pd.Timedelta(days=6))]
    previous_week = filtered_df[
        (filtered_df["Day"] >= (period_end - pd.Timedelta(days=13))) &
        (filtered_df["Day"] < (period_end - pd.Timedelta(days=6)))
    ]

    def calculate_metrics(df):
        spend = df["Spends"].sum()
        leads = df["Total Leads DB"].sum()
        clicks = df["Clicks"].sum()
        impressions = df["Impression"].sum()
        cpl = spend / leads if leads != 0 else 0
        ctr = (clicks / impressions * 100) if impressions != 0 else 0
        cpc = spend / clicks if clicks != 0 else 0
        conversion_rate = (leads / clicks * 100) if clicks != 0 else 0
        return spend, leads, cpl, ctr, cpc, conversion_rate

    cw_spend, cw_leads, cw_cpl, cw_ctr, cw_cpc, cw_conv = calculate_metrics(current_week)
    pw_spend, pw_leads, pw_cpl, pw_ctr, pw_cpc, pw_conv = calculate_metrics(previous_week)

    def format_change(current, previous):
        if previous == 0:
            return "N/A"
        change = ((current - previous) / previous) * 100
        color_class = "positive-change" if change >= 0 else "negative-change"
        symbol = "📈" if change >= 0 else "📉"
        return f'<span class="{color_class}">{symbol} {change:+.1f}%</span>'

    # Create metric cards
    col1, col2, col3, col4 = st.columns(4)
    col5, col6, col7, col8 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">💰 Total Spend</div>
            <div class="metric-value">₹{spend:,.0f}</div>
            <div>{format_change(cw_spend, pw_spend)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📩 Total Leads</div>
            <div class="metric-value">{int(leads):,}</div>
            <div>{format_change(cw_leads, pw_leads)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🟢 New Leads</div>
            <div class="metric-value">{int(new_leads):,}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🟡 Old Leads</div>
            <div class="metric-value">{int(old_leads):,}</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📉 Cost per Lead</div>
            <div class="metric-value">₹{cpl:.1f}</div>
            <div>{format_change(cw_cpl, pw_cpl)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📊 Click-Through Rate</div>
            <div class="metric-value">{ctr:.1f}%</div>
            <div>{format_change(cw_ctr, pw_ctr)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col7:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">💸 Cost per Click</div>
            <div class="metric-value">₹{cpc:.1f}</div>
            <div>{format_change(cw_cpc, pw_cpc)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col8:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🔄 Conversion Rate</div>
            <div class="metric-value">{conversion_rate:.1f}%</div>
            <div>{format_change(cw_conv, pw_conv)}</div>
        </div>
        """, unsafe_allow_html=True)

    # Enhanced Leads Trend with Plotly
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.subheader("📈 Leads Trend Over Time")
    trend_df = filtered_df.groupby("Day")["Total Leads DB"].sum().reset_index()
    fig_trend = px.area(trend_df, x="Day", y="Total Leads DB",
                       title="Daily Leads Trend",
                       labels={"Total Leads DB": "Leads", "Day": "Date"},
                       color_discrete_sequence=["#1e3c72"])
    fig_trend.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_trend, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Additional Visual Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📊 Spend by Source")
        source_spend = filtered_df.groupby("Source")["Spends"].sum().reset_index()
        fig_source = px.pie(source_spend, values="Spends", names="Source",
                           title="Spend Distribution by Platform",
                           color_discrete_sequence=px.colors.qualitative.Set3)
        fig_source.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=10),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_source, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📈 Daily Spend Trend")
        spend_trend = filtered_df.groupby("Day")["Spends"].sum().reset_index()
        fig_spend = px.bar(spend_trend, x="Day", y="Spends",
                          title="Daily Advertising Spend",
                          labels={"Spends": "Spend (₹)", "Day": "Date"},
                          color_discrete_sequence=["#ff6b6b"])
        fig_spend.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=10),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_spend, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Campaign Performance Chart
    if "Campaign name" in filtered_df.columns:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("🏆 Campaign Performance Overview")
        campaign_perf = filtered_df.groupby("Campaign name").agg({
            "Spends": "sum",
            "Total Leads DB": "sum",
            "Clicks": "sum"
        }).reset_index()
        campaign_perf["CPL"] = campaign_perf["Spends"] / campaign_perf["Total Leads DB"].replace(0, pd.NA)
        campaign_perf = campaign_perf.dropna().sort_values("Total Leads DB", ascending=False).head(10)

        fig_campaign = go.Figure()
        fig_campaign.add_trace(go.Bar(
            name="Spend",
            x=campaign_perf["Campaign name"],
            y=campaign_perf["Spends"],
            marker_color="#1e3c72",
            yaxis="y1"
        ))
        fig_campaign.add_trace(go.Scatter(
            name="CPL",
            x=campaign_perf["Campaign name"],
            y=campaign_perf["CPL"],
            mode="lines+markers",
            marker_color="#ff6b6b",
            line=dict(width=3),
            yaxis="y2"
        ))

        fig_campaign.update_layout(
            title="Top 10 Campaigns: Spend vs Cost per Lead",
            xaxis=dict(title="Campaign"),
            yaxis=dict(title="Spend (₹)", side="left"),
            yaxis2=dict(title="CPL (₹)", side="right", overlaying="y"),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=10),
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(x=0.1, y=1.1, orientation="h")
        )
        st.plotly_chart(fig_campaign, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("📋 Data Table")
    table_df = filtered_df.copy()
    table_df["CPL"] = table_df["Spends"] / table_df["Total Leads DB"].replace(0, pd.NA)
    table_df["CPC"] = table_df["Spends"] / table_df["Clicks"].replace(0, pd.NA)
    table_df["CTR (%)"] = (table_df["Clicks"] / table_df["Impression"].replace(0, pd.NA)) * 100
    table_df["Conversion Rate (%)"] = (table_df["Total Leads DB"] / table_df["Clicks"].replace(0, pd.NA)) * 100
    table_df = table_df.replace([float("inf"), -float("inf")], 0).round(2)

    cols = [
        "Source", "Campaign name", "Campaign_state", "Campaign_type", "Ad set name", "Ad name", "Month", "Date",
        "Spends", "Total Leads DB", "New Leads DB", "Old Leads DB", "Clicks", "Impression", "Conversions",
        "CPL", "CTR (%)", "CPC", "Conversion Rate (%)"
    ]
    cols = [c for c in cols if c in table_df.columns]
    table_df = table_df[cols]

    total_spend = table_df["Spends"].sum()
    total_leads = table_df["Total Leads DB"].sum()
    total_clicks = table_df["Clicks"].sum()
    total_impressions = table_df["Impression"].sum()

    total_row = pd.DataFrame([{
        "Source": "TOTAL",
        "Campaign name": "",
        "Campaign_state": "",
        "Campaign_type": "",
        "Ad set name": "",
        "Ad name": "",
        "Month": "",
        "Date": "",
        "Spends": round(total_spend, 2),
        "Total Leads DB": int(total_leads),
        "Clicks": int(total_clicks),
        "Impression": int(total_impressions),
        "CPL": round(total_spend / total_leads, 2) if total_leads != 0 else 0,
        "CTR (%)": round((total_clicks / total_impressions) * 100, 2) if total_impressions != 0 else 0,
        "CPC": round(total_spend / total_clicks, 2) if total_clicks != 0 else 0,
        "Conversion Rate (%)": round((total_leads / total_clicks) * 100) if total_clicks != 0 else 0
    }])
    final_df = pd.concat([table_df, total_row], ignore_index=True)
    st.dataframe(final_df)

    st.subheader("📊 Current Week vs Last Week (Table)")
    weekly_df = filtered_df.sort_values("Day")
    period_end = pd.to_datetime(end_date)

    current_week = weekly_df[weekly_df["Day"] >= (period_end - pd.Timedelta(days=6))]
    previous_week = weekly_df[
        (weekly_df["Day"] >= (period_end - pd.Timedelta(days=13))) &
        (weekly_df["Day"] < (period_end - pd.Timedelta(days=6)))
    ]

    def calc(df):
        spend = df["Spends"].sum()
        leads = df["Total Leads DB"].sum()
        clicks = df["Clicks"].sum()
        impressions = df["Impression"].sum()
        cpl = spend / leads if leads != 0 else 0
        ctr = (clicks / impressions * 100) if impressions != 0 else 0
        cpc = spend / clicks if clicks != 0 else 0
        return spend, leads, cpl, ctr, cpc

    cw = calc(current_week)
    pw = calc(previous_week)

    def pct(curr, prev):
        return ((curr - prev) / prev * 100) if prev != 0 else 0

    weekly_table = pd.DataFrame({
        "Metric": ["Spend", "Leads", "CPL", "CTR (%)", "CPC"],
        "Current Week": [cw[0], cw[1], cw[2], cw[3], cw[4]],
        "Last Week": [pw[0], pw[1], pw[2], pw[3], pw[4]],
        "% Change": [
            pct(cw[0], pw[0]),
            pct(cw[1], pw[1]),
            pct(cw[2], pw[2]),
            pct(cw[3], pw[3]),
            pct(cw[4], pw[4])
        ]
    }).round(2)
    st.dataframe(weekly_table)

    st.subheader("🏆 Top Performing Creatives and Campaigns")
    sort_cols, ascending = get_sort_columns(ranking_metrics)

    if "Ad name" in filtered_df.columns:
        top_creatives = (
            filtered_df
            .groupby("Ad name", dropna=False)
            .agg(
                Spend=("Spends", "sum"),
                Leads=("Total Leads DB", "sum"),
                Clicks=("Clicks", "sum"),
                Impressions=("Impression", "sum")
            )
            .assign(
                CPL=lambda d: d["Spend"] / d["Leads"].replace(0, pd.NA),
                CTR=lambda d: (d["Clicks"] / d["Impressions"].replace(0, pd.NA)) * 100
            )
            .sort_values(sort_cols, ascending=ascending)
            .head(5)
            .round(2)
        )
        st.markdown(f"**Top 5 Creatives by {', '.join(ranking_metrics)}**")
        st.dataframe(top_creatives.reset_index())
    else:
        st.warning("Ad name column not found; top creatives cannot be calculated.")

    if "Campaign name" in filtered_df.columns:
        top_campaigns = (
            filtered_df
            .groupby("Campaign name", dropna=False)
            .agg(
                Spend=("Spends", "sum"),
                Leads=("Total Leads DB", "sum"),
                Clicks=("Clicks", "sum"),
                Impressions=("Impression", "sum")
            )
            .assign(
                CPL=lambda d: d["Spend"] / d["Leads"].replace(0, pd.NA),
                CTR=lambda d: (d["Clicks"] / d["Impressions"].replace(0, pd.NA)) * 100
            )
            .sort_values(sort_cols, ascending=ascending)
            .head(3)
            .round(2)
        )
        st.markdown(f"**Top 3 Campaigns by {', '.join(ranking_metrics)}**")
        st.dataframe(top_campaigns.reset_index())
    else:
        st.warning("Campaign name column not found; top campaigns cannot be calculated.")

    st.subheader("📉 Top 5 Worst Creatives")
    worst_sort_cols, worst_ascending = get_worst_sort_columns(worst_metrics)
    if "Ad name" in filtered_df.columns:
        worst_creatives = (
            filtered_df
            .groupby("Ad name", dropna=False)
            .agg(
                Spend=("Spends", "sum"),
                Leads=("Total Leads DB", "sum"),
                Clicks=("Clicks", "sum"),
                Impressions=("Impression", "sum")
            )
            .assign(
                CPL=lambda d: d["Spend"] / d["Leads"].replace(0, pd.NA),
                CTR=lambda d: (d["Clicks"] / d["Impressions"].replace(0, pd.NA)) * 100
            )
            .sort_values(worst_sort_cols, ascending=worst_ascending)
            .head(5)
            .round(2)
        )
        st.markdown(f"**Worst 5 Creatives by {', '.join(worst_metrics)}**")
        st.dataframe(worst_creatives.reset_index())
    else:
        st.warning("Ad name column not found; worst creatives cannot be calculated.")

    if "Campaign name" in filtered_df.columns:
        worst_campaigns = (
            filtered_df
            .groupby("Campaign name", dropna=False)
            .agg(
                Spend=("Spends", "sum"),
                Leads=("Total Leads DB", "sum"),
                Clicks=("Clicks", "sum"),
                Impressions=("Impression", "sum")
            )
            .assign(
                CPL=lambda d: d["Spend"] / d["Leads"].replace(0, pd.NA),
                CTR=lambda d: (d["Clicks"] / d["Impressions"].replace(0, pd.NA)) * 100
            )
            .sort_values(worst_sort_cols, ascending=worst_ascending)
            .head(5)
            .round(2)
        )
        st.subheader("📉 Top 5 Worst Campaigns")
        st.markdown(f"**Worst 5 Campaigns by {', '.join(worst_metrics)}**")
        st.dataframe(worst_campaigns.reset_index())
    else:
        st.warning("Campaign name column not found; worst campaigns cannot be calculated.")


def get_sort_columns(metrics):
    if isinstance(metrics, str):
        metrics = [metrics]

    cols = []
    ascending = []
    for metric in metrics:
        if metric == "Leads":
            cols.append("Leads")
            ascending.append(False)
        elif metric == "CPL":
            cols.append("CPL")
            ascending.append(True)
        elif metric == "CTR":
            cols.append("CTR")
            ascending.append(False)
        elif metric == "Spend":
            cols.append("Spend")
            ascending.append(False)

    if not cols:
        return ["Leads", "CTR"], [False, False]
    return cols, ascending


def get_worst_sort_columns(metrics):
    if isinstance(metrics, str):
        metrics = [metrics]

    cols = []
    ascending = []
    for metric in metrics:
        if metric == "Leads":
            cols.append("Leads")
            ascending.append(True)
        elif metric == "CPL":
            cols.append("CPL")
            ascending.append(False)
        elif metric == "CTR":
            cols.append("CTR")
            ascending.append(True)
        elif metric == "Spend":
            cols.append("Spend")
            ascending.append(True)

    if not cols:
        return ["CPL", "Leads"], [False, True]
    return cols, ascending


def render_dashboard(tab_name, sheet_url, upload_key):
    st.header(f"{tab_name}")

    df, data_source = load_data(sheet_url, upload_key)
    if df is None:
        return

    df = clean_data(df)
    if df is None or df.empty:
        return

    sidebar_prefix = tab_name.replace(" ", "_")
    st.sidebar.markdown(f"**{tab_name} Data source:** {data_source}")
    st.sidebar.markdown(
        f"Rows: {len(df)}  \nDate range: {df['Day'].min().date()} - {df['Day'].max().date()}"
    )
    st.sidebar.header(f"📅 Filters - {tab_name}")

    start_date = st.sidebar.date_input(
        "Start Date",
        df["Day"].min(),
        key=f"start_{sidebar_prefix}"
    )
    end_date = st.sidebar.date_input(
        "End Date",
        df["Day"].max(),
        key=f"end_{sidebar_prefix}"
    )

    filtered_df = df[
        (df["Day"] >= pd.to_datetime(start_date)) &
        (df["Day"] <= pd.to_datetime(end_date))
    ]

    if "Campaign name" in filtered_df.columns:
        campaigns = sorted(filtered_df["Campaign name"].dropna().unique())
        selected_campaigns = st.sidebar.multiselect(
            "Campaign",
            ["All"] + campaigns,
            default=["All"],
            key=f"campaign_{sidebar_prefix}"
        )
        if "All" not in selected_campaigns:
            filtered_df = filtered_df[filtered_df["Campaign name"].isin(selected_campaigns)]

    if "Ad set name" in filtered_df.columns:
        adsets = sorted(filtered_df["Ad set name"].dropna().unique())
        selected_adsets = st.sidebar.multiselect(
            "Ad Set",
            ["All"] + adsets,
            default=["All"],
            key=f"adset_{sidebar_prefix}"
        )
        if "All" not in selected_adsets:
            filtered_df = filtered_df[filtered_df["Ad set name"].isin(selected_adsets)]

    if "Ad name" in filtered_df.columns:
        ads = sorted(filtered_df["Ad name"].dropna().unique())
        selected_ads = st.sidebar.multiselect(
            "Ad",
            ["All"] + ads,
            default=["All"],
            key=f"ad_{sidebar_prefix}"
        )
        if "All" not in selected_ads:
            filtered_df = filtered_df[filtered_df["Ad name"].isin(selected_ads)]

    ranking_metrics = st.sidebar.multiselect(
        "Top Performers Ranking Metrics",
        ["Leads", "CPL", "CTR", "Spend"],
        default=["Leads"],
        help="Choose one or more metrics to rank top creatives and campaigns. Lower CPL is better; higher others are better.",
        key=f"ranking_{sidebar_prefix}"
    )

    worst_metrics = st.sidebar.multiselect(
        "Worst Creatives Metrics",
        ["Leads", "CPL", "CTR", "Spend"],
        default=["CPL"],
        help="Choose one or more metrics to identify worst-performing creatives.",
        key=f"worst_{sidebar_prefix}"
    )

    if not ranking_metrics:
        ranking_metrics = ["Leads"]
    if not worst_metrics:
        worst_metrics = ["CPL"]

    if filtered_df.empty:
        st.warning("No data available")
        return

    spend = filtered_df["Spends"].sum()
    leads = filtered_df["Total Leads DB"].sum()
    new_leads = filtered_df["New Leads DB"].sum() if "New Leads DB" in filtered_df.columns else 0
    old_leads = filtered_df["Old Leads DB"].sum() if "Old Leads DB" in filtered_df.columns else 0
    clicks = filtered_df["Clicks"].sum()
    impressions = filtered_df["Impression"].sum()

    cpl = spend / leads if leads != 0 else 0
    ctr = (clicks / impressions * 100) if impressions != 0 else 0
    cpc = spend / clicks if clicks != 0 else 0
    conversion_rate = (leads / clicks * 100) if clicks != 0 else 0

    st.subheader("📊 Key Metrics")
    c1, c2, c3, c4 = st.columns(4)
    c5, c6, c7, c8 = st.columns(4)

    c1.metric("💰 Spend", f"{spend:.1f}")
    c2.metric("📩 Total Leads", int(leads))
    c3.metric("🟢 New Leads", int(new_leads))
    c4.metric("🟡 Old Leads", int(old_leads))
    c5.metric("📉 CPL", f"{cpl:.1f}")
    c6.metric("📊 CTR (%)", f"{ctr:.1f}")
    c7.metric("💸 CPC", f"{cpc:.1f}")
    c8.metric("🔄 Conversion Rate (%)", f"{conversion_rate:.1f}")

    st.subheader("📈 Leads Trend")
    trend = filtered_df.groupby("Day")["Total Leads DB"].sum()
    st.line_chart(trend)

    st.subheader("📋 Data Table")
    table_df = filtered_df.copy()
    table_df["CPL"] = table_df["Spends"] / table_df["Total Leads DB"].replace(0, pd.NA)
    table_df["CPC"] = table_df["Spends"] / table_df["Clicks"].replace(0, pd.NA)
    table_df["CTR (%)"] = (table_df["Clicks"] / table_df["Impression"].replace(0, pd.NA)) * 100
    table_df["Conversion Rate (%)"] = (table_df["Total Leads DB"] / table_df["Clicks"].replace(0, pd.NA)) * 100

    table_df = table_df.replace([float("inf"), -float("inf")], 0)
    # Round only numeric columns
    numeric_cols = table_df.select_dtypes(include=[np.number]).columns
    table_df[numeric_cols] = table_df[numeric_cols].round(2)
    cols = [
        "Campaign name", "Campaign_state", "Campaign_type", "Ad set name", "Ad name", "Month", "Date",
        "Spends", "Total Leads DB", "New Leads DB", "Old Leads DB", "Clicks", "Impression", "Conversions",
        "CPL", "CTR (%)", "CPC", "Conversion Rate (%)"
    ]
    cols = [c for c in cols if c in table_df.columns]
    table_df = table_df[cols]

    total_spend = table_df["Spends"].sum()
    total_leads = table_df["Total Leads DB"].sum()
    total_clicks = table_df["Clicks"].sum()
    total_impressions = table_df["Impression"].sum()

    total_row = pd.DataFrame([{
        "Campaign name": "TOTAL",
        "Ad set name": "",
        "Ad name": "",
        "Spends": round(total_spend, 2),
        "Total Leads DB": int(total_leads),
        "Clicks": int(total_clicks),
        "Impression": int(total_impressions),
        "CPL": round(total_spend / total_leads, 2) if total_leads != 0 else 0,
        "CTR (%)": round((total_clicks / total_impressions) * 100, 2) if total_impressions != 0 else 0,
        "CPC": round(total_spend / total_clicks, 2) if total_clicks != 0 else 0,
        "Conversion Rate (%)": round((total_leads / total_clicks) * 100) if total_clicks != 0 else 0
    }])
    final_df = pd.concat([table_df, total_row], ignore_index=True)
    st.dataframe(final_df)

    st.subheader("📊 Current Week vs Last Week (Table)")
    weekly_df = filtered_df.sort_values("Day")
    max_date = weekly_df["Day"].max()

    current_week = weekly_df[weekly_df["Day"] >= (max_date - pd.Timedelta(days=6))]
    previous_week = weekly_df[
        (weekly_df["Day"] >= (max_date - pd.Timedelta(days=13))) &
        (weekly_df["Day"] < (max_date - pd.Timedelta(days=6)))
    ]

    def calc(df):
        spend = df["Spends"].sum()
        leads = df["Total Leads DB"].sum()
        clicks = df["Clicks"].sum()
        impressions = df["Impression"].sum()
        cpl = spend / leads if leads != 0 else 0
        ctr = (clicks / impressions * 100) if impressions != 0 else 0
        cpc = spend / clicks if clicks != 0 else 0
        return spend, leads, cpl, ctr, cpc

    cw = calc(current_week)
    pw = calc(previous_week)

    def pct(curr, prev):
        return ((curr - prev) / prev * 100) if prev != 0 else 0

    weekly_table = pd.DataFrame({
        "Metric": ["Spend", "Leads", "CPL", "CTR (%)", "CPC"],
        "Current Week": [cw[0], cw[1], cw[2], cw[3], cw[4]],
        "Last Week": [pw[0], pw[1], pw[2], pw[3], pw[4]],
        "% Change": [
            pct(cw[0], pw[0]),
            pct(cw[1], pw[1]),
            pct(cw[2], pw[2]),
            pct(cw[3], pw[3]),
            pct(cw[4], pw[4])
        ]
    }).round(2)
    st.dataframe(weekly_table)

    st.subheader("🏆 Top Performing Creatives and Campaigns")
    sort_cols, ascending = get_sort_columns(ranking_metrics)

    if "Ad name" in filtered_df.columns:
        top_creatives = (
            filtered_df
            .groupby("Ad name", dropna=False)
            .agg(
                Spend=("Spends", "sum"),
                Leads=("Total Leads DB", "sum"),
                Clicks=("Clicks", "sum"),
                Impressions=("Impression", "sum")
            )
            .assign(
                CPL=lambda d: d["Spend"] / d["Leads"].replace(0, pd.NA),
                CTR=lambda d: (d["Clicks"] / d["Impressions"].replace(0, pd.NA)) * 100
            )
            .sort_values(sort_cols, ascending=ascending)
            .head(5)
            .round(2)
        )
        st.markdown(f"**Top 5 Creatives by {', '.join(ranking_metrics)}**")
        st.dataframe(top_creatives.reset_index())
    else:
        st.warning("Ad name column not found; top creatives cannot be calculated.")

    if "Campaign name" in filtered_df.columns:
        top_campaigns = (
            filtered_df
            .groupby("Campaign name", dropna=False)
            .agg(
                Spend=("Spends", "sum"),
                Leads=("Total Leads DB", "sum"),
                Clicks=("Clicks", "sum"),
                Impressions=("Impression", "sum")
            )
            .assign(
                CPL=lambda d: d["Spend"] / d["Leads"].replace(0, pd.NA),
                CTR=lambda d: (d["Clicks"] / d["Impressions"].replace(0, pd.NA)) * 100
            )
            .sort_values(sort_cols, ascending=ascending)
            .head(3)
            .round(2)
        )
        st.markdown(f"**Top 3 Campaigns by {', '.join(ranking_metrics)}**")
        st.dataframe(top_campaigns.reset_index())
    else:
        st.warning("Campaign name column not found; top campaigns cannot be calculated.")

    st.subheader("📉 Top 5 Worst Creatives")
    worst_sort_cols, worst_ascending = get_worst_sort_columns(worst_metrics)
    if "Ad name" in filtered_df.columns:
        worst_creatives = (
            filtered_df
            .groupby("Ad name", dropna=False)
            .agg(
                Spend=("Spends", "sum"),
                Leads=("Total Leads DB", "sum"),
                Clicks=("Clicks", "sum"),
                Impressions=("Impression", "sum")
            )
            .assign(
                CPL=lambda d: d["Spend"] / d["Leads"].replace(0, pd.NA),
                CTR=lambda d: (d["Clicks"] / d["Impressions"].replace(0, pd.NA)) * 100
            )
            .sort_values(worst_sort_cols, ascending=worst_ascending)
            .head(5)
            .round(2)
        )
        st.markdown(f"**Worst 5 Creatives by {', '.join(worst_metrics)}**")
        st.dataframe(worst_creatives.reset_index())
    else:
        st.warning("Ad name column not found; worst creatives cannot be calculated.")

    if "Campaign name" in filtered_df.columns:
        worst_campaigns = (
            filtered_df
            .groupby("Campaign name", dropna=False)
            .agg(
                Spend=("Spends", "sum"),
                Leads=("Total Leads DB", "sum"),
                Clicks=("Clicks", "sum"),
                Impressions=("Impression", "sum")
            )
            .assign(
                CPL=lambda d: d["Spend"] / d["Leads"].replace(0, pd.NA),
                CTR=lambda d: (d["Clicks"] / d["Impressions"].replace(0, pd.NA)) * 100
            )
            .sort_values(worst_sort_cols, ascending=worst_ascending)
            .head(5)
            .round(2)
        )
        st.subheader("📉 Top 5 Worst Campaigns")
        st.markdown(f"**Worst 5 Campaigns by {', '.join(worst_metrics)}**")
        st.dataframe(worst_campaigns.reset_index())
    else:
        st.warning("Campaign name column not found; worst campaigns cannot be calculated.")


tabs = st.tabs(["📘 Meta Ads", "🔍 Google Ads", "🔄 Combined Dashboard"])
with tabs[0]:
    render_dashboard("Meta Ads", META_SHEET_URL, "upload_meta")
with tabs[1]:
    render_dashboard("Google Ads", GOOGLE_ADS_SHEET_URL, "upload_google")
with tabs[2]:
    render_combined_dashboard()

