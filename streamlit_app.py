"""
Google Analytics Intelligence Dashboard
Enterprise-grade analytics with Snowflake backend.
Deployed on Streamlit Community Cloud.
"""

from datetime import date, timedelta
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

st.set_page_config(
    page_title="Google Analytics Intelligence",
    page_icon=":material/monitoring:",
    layout="wide",
)

# Custom CSS
st.markdown("""
<style>
    .block-container { padding-top: 3rem; padding-bottom: 0; max-width: 100%; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1B1F2A 0%, #141820 100%);
        border: 1px solid rgba(41, 181, 232, 0.15);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    }
    [data-testid="stMetricValue"] { font-size: 1.5rem; font-weight: 700; }
    [data-testid="stMetricDelta"] { font-size: 0.75rem; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px; background: #141820; border-radius: 8px; padding: 4px;
        overflow-x: auto; -webkit-overflow-scrolling: touch; flex-wrap: nowrap;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px; padding: 8px 16px; white-space: nowrap; flex-shrink: 0;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0A0E14 0%, #0E1117 100%);
    }
    [data-testid="stVegaLiteChart"] { border-radius: 8px; overflow: hidden; }
    h1 { letter-spacing: -0.02em; }
    h2 { font-size: 1.3rem !important; font-weight: 600; color: #E0E0E0; }
    h3 { font-size: 1.05rem !important; font-weight: 500; color: #B0B0B0; }
    /* Pointer cursor on interactive elements */
    .stRadio label, .stCheckbox label,
    [data-baseweb="tab"],
    [data-baseweb="select"] *,
    .stButton button,
    .stSelectbox div[data-baseweb="select"],
    .stDownloadButton button { cursor: pointer !important; }
</style>
""", unsafe_allow_html=True)

# Constants
TIME_RANGES = ["1W", "1M", "3M", "6M", "YTD", "All"]
CHART_HEIGHT = 280

CHANNEL_COLORS = {
    "Organic Search": "#29B5E8",
    "Direct": "#6C63FF",
    "Social": "#FF6B9D",
    "Referral": "#45B7AA",
    "Paid Search": "#FFB347",
    "Affiliates": "#C4A3FF",
    "Display": "#FF8A65",
    "(Other)": "#78909C",
}

# Snowflake Connection
conn = st.connection("snowflake")


def run_query(sql):
    df = conn.query(sql)
    # Convert Decimal columns to float for pandas compatibility
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass
    return df


# Data Loading
@st.cache_data(ttl=600)
def load_daily_traffic():
    return run_query("SELECT * FROM GOOGLE_ANALYTICS.PUBLIC.V_DAILY_TRAFFIC ORDER BY DATE")


@st.cache_data(ttl=600)
def load_acquisition():
    return run_query("""
        SELECT CHANNEL_GROUPING, SUM(SESSIONS) as SESSIONS, SUM(NEW_USERS) as NEW_USERS,
               SUM(REVENUE) as REVENUE, SUM(BOUNCES) as BOUNCES, SUM(PAGEVIEWS) as PAGEVIEWS
        FROM GOOGLE_ANALYTICS.PUBLIC.V_ACQUISITION_CHANNELS GROUP BY CHANNEL_GROUPING ORDER BY SESSIONS DESC
    """)


@st.cache_data(ttl=600)
def load_acquisition_trend():
    return run_query("""
        SELECT DATE, CHANNEL_GROUPING, SUM(SESSIONS) as SESSIONS, SUM(REVENUE) as REVENUE
        FROM GOOGLE_ANALYTICS.PUBLIC.V_ACQUISITION_CHANNELS GROUP BY DATE, CHANNEL_GROUPING ORDER BY DATE
    """)


@st.cache_data(ttl=600)
def load_geo():
    return run_query("""
        SELECT COUNTRY, SUM(SESSIONS) as SESSIONS, SUM(REVENUE) as REVENUE,
               ROUND(AVG(BOUNCE_RATE_PCT), 1) as BOUNCE_RATE,
               ROUND(AVG(AVG_DURATION_SEC), 0) as AVG_DURATION
        FROM GOOGLE_ANALYTICS.PUBLIC.V_GEO_SUMMARY GROUP BY COUNTRY ORDER BY SESSIONS DESC
    """)


@st.cache_data(ttl=600)
def load_devices():
    return run_query("""
        SELECT DEVICE_CATEGORY, SUM(SESSIONS) as SESSIONS, SUM(REVENUE) as REVENUE,
               ROUND(AVG(BOUNCE_RATE_PCT), 1) as BOUNCE_RATE
        FROM GOOGLE_ANALYTICS.PUBLIC.V_GEO_SUMMARY GROUP BY DEVICE_CATEGORY ORDER BY SESSIONS DESC
    """)


@st.cache_data(ttl=600)
def load_browsers():
    return run_query("""
        SELECT BROWSER, SUM(SESSIONS) as SESSIONS
        FROM GOOGLE_ANALYTICS.PUBLIC.V_GEO_SUMMARY GROUP BY BROWSER ORDER BY SESSIONS DESC LIMIT 10
    """)


@st.cache_data(ttl=600)
def load_ecommerce():
    return run_query("SELECT * FROM GOOGLE_ANALYTICS.PUBLIC.V_ECOMMERCE_FUNNEL ORDER BY DATE")


@st.cache_data(ttl=600)
def load_top_pages():
    return run_query("""
        SELECT PAGE_PATH, TOTAL_HITS, ENTRANCES, EXITS, EXIT_RATE_PCT, UNIQUE_SESSIONS
        FROM GOOGLE_ANALYTICS.PUBLIC.V_TOP_PAGES ORDER BY TOTAL_HITS DESC LIMIT 50
    """)


# Utility Functions
def filter_by_time_range(df, date_col, time_range):
    if time_range == "All" or df.empty:
        return df
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    max_date = df[date_col].max()
    if time_range == "1W":
        min_date = max_date - timedelta(days=7)
    elif time_range == "1M":
        min_date = max_date - timedelta(days=30)
    elif time_range == "3M":
        min_date = max_date - timedelta(days=90)
    elif time_range == "6M":
        min_date = max_date - timedelta(days=180)
    elif time_range == "YTD":
        min_date = pd.Timestamp(date(max_date.year, 1, 1))
    else:
        return df
    return df[df[date_col] >= min_date]


def format_number(n):
    if n is None or pd.isna(n):
        return "0"
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:,.0f}"


def format_currency(n):
    if n is None or pd.isna(n):
        return "$0"
    if abs(n) >= 1_000_000:
        return f"${n/1_000_000:.2f}M"
    if abs(n) >= 1_000:
        return f"${n/1_000:.1f}K"
    return f"${n:,.0f}"


def compute_delta(df, col, date_col="DATE"):
    if len(df) < 14:
        return None
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    recent = df[col].tail(7).sum()
    prior = df[col].iloc[-14:-7].sum()
    if prior == 0:
        return None
    return round((recent - prior) / prior * 100, 1)


# Documentation Page
def render_documentation():
    st.markdown("## :material/menu_book: Data Documentation")
    st.caption("Everything behind the GA Intelligence dashboard - data lineage, schema, and the modeling decisions.")

    st.info("This dashboard models the public Google Merchandise Store GA dataset (Aug 2016 - Aug 2017) into a star schema in Snowflake: 903K sessions and 4.1M hits.", icon=":material/lightbulb:")

    doc_tab1, doc_tab2, doc_tab3, doc_tab4 = st.tabs([
        ":material/source: Raw Data",
        ":material/schema: Data Model",
        ":material/visibility: Analytics Views",
        ":material/insights: Key Decisions",
    ])

    with doc_tab1:
        st.markdown("### Source Dataset")
        st.markdown("""
        Based on the **Google Analytics Sample** (Google Merchandise Store) - real
        clickstream data for an online store selling Google-branded merchandise.

        | Property | Value |
        |---|---|
        | **Source** | Google Merchandise Store (GA Sample) |
        | **Period** | Aug 2016 - Aug 2017 (396 days) |
        | **Sessions** | 903,653 |
        | **Hits** | 4,153,675 |
        | **Grain** | Session-level + hit-level event data |
        """)
        st.markdown("""
        GA exports are deeply nested (sessions contain arrays of hits, each hit
        containing page, e-commerce, and traffic structs). The raw export was
        **flattened into two fact tables** plus a date dimension.
        """)

    with doc_tab2:
        st.markdown("### Star Schema")
        st.markdown("**`FACT_SESSIONS`** - one row per session (903,653 rows)")
        st.dataframe(pd.DataFrame({
            "Column": ["SESSION_ID", "VISITOR_ID", "DATE", "CHANNEL_GROUPING", "SESSIONS",
                       "PAGEVIEWS", "BOUNCES", "TIME_ON_SITE_SEC", "TRANSACTIONS", "TOTAL_REVENUE",
                       "DEVICE_CATEGORY", "BROWSER", "COUNTRY", "TRAFFIC_SOURCE", "TRAFFIC_MEDIUM"],
            "Type": ["TEXT", "TEXT", "DATE", "TEXT", "NUMBER", "NUMBER", "NUMBER", "NUMBER",
                     "NUMBER", "FLOAT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT"],
            "Group": ["Key", "Key", "Date", "Acquisition", "Traffic", "Traffic", "Traffic",
                      "Engagement", "E-commerce", "E-commerce", "Tech", "Tech", "Geo", "Acquisition", "Acquisition"],
        }), hide_index=True, use_container_width=True)
        st.caption("(plus geo, OS, campaign, referral, and is_mobile/is_true_direct flags)")

        st.markdown("**`FACT_HITS`** - one row per hit/event (4,153,675 rows)")
        st.dataframe(pd.DataFrame({
            "Column": ["SESSION_ID", "DATE", "HIT_NUMBER", "HIT_TYPE", "PAGE_PATH", "PAGE_TITLE",
                       "IS_ENTRANCE", "IS_EXIT", "ECOMMERCE_ACTION_TYPE", "TRANSACTION_ID", "TRANSACTION_REVENUE"],
            "Type": ["TEXT", "DATE", "NUMBER", "TEXT", "TEXT", "TEXT", "BOOLEAN", "BOOLEAN",
                     "TEXT", "TEXT", "FLOAT"],
            "Description": ["FK to session", "Event date", "Sequence in session", "PAGE / EVENT / etc.",
                            "URL path", "Page title", "First hit of session", "Last hit of session",
                            "Funnel step", "Order ID", "Order revenue"],
        }), hide_index=True, use_container_width=True)

        st.markdown("**`DIM_DATE`** - calendar dimension (396 rows)")
        st.markdown("Day-of-week, month, quarter, year, and weekend flag for time roll-ups.")

    with doc_tab3:
        st.markdown("### Analytics Views")
        st.markdown("Pre-aggregated views keep the 4M+ row scans in Snowflake, not the app.")
        st.dataframe(pd.DataFrame({
            "View": ["V_DAILY_TRAFFIC", "V_ACQUISITION_CHANNELS", "V_GEO_SUMMARY",
                     "V_ECOMMERCE_FUNNEL", "V_TOP_PAGES"],
            "Purpose": [
                "Daily sessions, pageviews, bounce rate, duration, new/returning users",
                "Sessions, revenue & bounces per marketing channel (by day)",
                "Sessions, revenue, bounce by country / device / browser",
                "Daily revenue, transactions, conversion rate, avg order value",
                "Page-level hits, entrances, exits, exit rate",
            ],
            "Feeds": ["Traffic tab", "Acquisition tab", "Geography & Devices tab",
                      "E-Commerce tab", "Content tab"],
        }), hide_index=True, use_container_width=True)

    with doc_tab4:
        st.markdown("### Key Data Analysis Decisions")
        st.markdown("""
        **1. Two-grain fact model**
        Sessions and hits live in **separate fact tables** (`FACT_SESSIONS`, `FACT_HITS`).
        Session-level metrics (bounce, revenue, channel) don't mix with hit-level
        page/event analysis, avoiding fan-out and double counting.

        **2. Aggregate in the warehouse, not the app**
        Every dashboard tab reads from a **view** that pre-aggregates the 4M+ hit rows.
        The app pulls compact result sets, keeping it fast on Community Cloud.

        **3. 7-day rolling averages**
        Daily web traffic is noisy (weekday/weekend swings), so trend lines use a
        **7-day moving average** for sessions, pageviews, bounce, revenue, and conversion.

        **4. Week-over-week deltas**
        KPI cards compare the **last 7 days vs the prior 7 days**. Bounce rate uses
        an *inverse* delta color (down = good).

        **5. Channel grouping**
        Traffic is bucketed into standard GA channels (Organic Search, Direct, Social,
        Referral, Paid Search, Affiliates, Display) each with a fixed brand color.

        **6. Decimal handling**
        Snowflake returns numerics as `Decimal`; `run_query()` auto-casts object
        columns to numeric so pandas math and Altair charts work.
        """)

    st.divider()
    st.caption("GA Intelligence | Data documentation for the Snowflake data model.")


# Sidebar
with st.sidebar:
    st.markdown("### :material/monitoring: Analytics")
    st.markdown("*Google Merchandise Store*")
    st.divider()

    page = st.radio(
        "Navigate",
        ["Dashboard", "About the Data"],
        key="nav_page",
        label_visibility="collapsed",
    )
    st.divider()

    time_range = st.selectbox(
        "Time Range",
        TIME_RANGES,
        index=5,
        help="Filter all dashboard data by time window",
    )

    st.divider()
    st.markdown("**Dataset Info**")
    st.markdown("Aug 2016 - Aug 2017")
    st.markdown("903K sessions | 4.1M hits")
    st.divider()

    if st.button(":material/restart_alt: Reset Cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Render documentation page and stop if selected
if page == "About the Data":
    render_documentation()
    st.stop()

# Header
st.markdown("## :material/monitoring: Google Analytics Intelligence")
st.markdown("*Real-time analytics for the Google Merchandise Store | Powered by Snowflake*")

# KPI Row
traffic_df = load_daily_traffic()
filtered_traffic = filter_by_time_range(traffic_df, "DATE", time_range)

total_sessions = int(filtered_traffic["TOTAL_SESSIONS"].sum()) if not filtered_traffic.empty else 0
total_pageviews = int(filtered_traffic["TOTAL_PAGEVIEWS"].sum()) if not filtered_traffic.empty else 0
avg_bounce = round(filtered_traffic["BOUNCE_RATE_PCT"].mean(), 1) if not filtered_traffic.empty else 0
avg_duration = round(filtered_traffic["AVG_SESSION_DURATION_SEC"].mean(), 0) if not filtered_traffic.empty else 0

ecom_df = load_ecommerce()
filtered_ecom = filter_by_time_range(ecom_df, "DATE", time_range)
total_revenue = filtered_ecom["REVENUE"].sum() if not filtered_ecom.empty else 0
total_transactions = int(filtered_ecom["TRANSACTIONS"].sum()) if not filtered_ecom.empty else 0

delta_sessions = compute_delta(filtered_traffic, "TOTAL_SESSIONS")
delta_revenue = compute_delta(filtered_ecom, "REVENUE")
delta_bounce = compute_delta(filtered_traffic, "BOUNCE_RATE_PCT")

cols = st.columns(4)
cols[0].metric("Sessions", format_number(total_sessions), f"{delta_sessions}% vs prior week" if delta_sessions else None)
cols[1].metric("Bounce Rate", f"{avg_bounce}%", f"{delta_bounce}%" if delta_bounce else None, delta_color="inverse")
cols[2].metric("Revenue", format_currency(total_revenue), f"{delta_revenue}% vs prior week" if delta_revenue else None)
cols[3].metric("Transactions", format_number(total_transactions))

st.divider()

# Tabs
tab_traffic, tab_acquisition, tab_geo, tab_ecommerce, tab_content = st.tabs([
    ":material/show_chart: Traffic",
    ":material/target: Acquisition",
    ":material/public: Geography & Devices",
    ":material/shopping_cart: E-Commerce",
    ":material/article: Content",
])

# --- Traffic Tab ---
with tab_traffic:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Sessions & Pageviews Over Time")
        chart_df = filtered_traffic.copy()
        if not chart_df.empty:
            chart_df["DATE"] = pd.to_datetime(chart_df["DATE"])
            chart_df["sessions_7d"] = chart_df["TOTAL_SESSIONS"].rolling(7, min_periods=1).mean()
            chart_df["pageviews_7d"] = chart_df["TOTAL_PAGEVIEWS"].rolling(7, min_periods=1).mean()

            melted = chart_df.melt(
                id_vars=["DATE"],
                value_vars=["sessions_7d", "pageviews_7d"],
                var_name="metric",
                value_name="value",
            )
            melted["metric"] = melted["metric"].map({
                "sessions_7d": "Sessions (7-day avg)",
                "pageviews_7d": "Pageviews (7-day avg)",
            })

            chart = (
                alt.Chart(melted)
                .mark_area(opacity=0.3, line=True)
                .encode(
                    x=alt.X("DATE:T", title=None, axis=alt.Axis(format="%b %Y")),
                    y=alt.Y("value:Q", title=None, scale=alt.Scale(zero=False)),
                    color=alt.Color("metric:N", title=None,
                                    scale=alt.Scale(range=["#29B5E8", "#6C63FF"]),
                                    legend=alt.Legend(orient="bottom")),
                    tooltip=[
                        alt.Tooltip("DATE:T", format="%Y-%m-%d"),
                        alt.Tooltip("metric:N"),
                        alt.Tooltip("value:Q", format=",.0f"),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(chart, use_container_width=True)

    with col2:
        st.markdown("### Bounce Rate Trend")
        if not chart_df.empty:
            chart_df["bounce_7d"] = chart_df["BOUNCE_RATE_PCT"].rolling(7, min_periods=1).mean()
            bounce_chart = (
                alt.Chart(chart_df)
                .mark_line(color="#FF6B9D", strokeWidth=2)
                .encode(
                    x=alt.X("DATE:T", title=None, axis=alt.Axis(format="%b")),
                    y=alt.Y("bounce_7d:Q", title=None, scale=alt.Scale(domain=[40, 60])),
                    tooltip=[
                        alt.Tooltip("DATE:T", format="%Y-%m-%d"),
                        alt.Tooltip("bounce_7d:Q", title="Bounce %", format=".1f"),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(bounce_chart, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("### New vs Returning Users")
        if not filtered_traffic.empty:
            new_total = int(filtered_traffic["NEW_USERS"].sum())
            returning_total = int(filtered_traffic["RETURNING_USERS"].sum())
            pie_df = pd.DataFrame({
                "type": ["New Users", "Returning Users"],
                "count": [new_total, returning_total],
            })
            pie = (
                alt.Chart(pie_df)
                .mark_arc(innerRadius=50, outerRadius=100)
                .encode(
                    theta=alt.Theta("count:Q"),
                    color=alt.Color("type:N", scale=alt.Scale(range=["#29B5E8", "#6C63FF"]),
                                    legend=alt.Legend(orient="bottom")),
                    tooltip=["type:N", alt.Tooltip("count:Q", format=",")],
                )
                .properties(height=220)
            )
            st.altair_chart(pie, use_container_width=True)

    with col4:
        st.markdown("### Session Duration Distribution")
        if not filtered_traffic.empty:
            dur_chart = (
                alt.Chart(chart_df)
                .mark_bar(color="#45B7AA", opacity=0.7)
                .encode(
                    x=alt.X("DATE:T", title=None, axis=alt.Axis(format="%b")),
                    y=alt.Y("AVG_SESSION_DURATION_SEC:Q", title="Seconds"),
                    tooltip=[
                        alt.Tooltip("DATE:T", format="%Y-%m-%d"),
                        alt.Tooltip("AVG_SESSION_DURATION_SEC:Q", title="Avg Duration (s)", format=".0f"),
                    ],
                )
                .properties(height=220)
            )
            st.altair_chart(dur_chart, use_container_width=True)

# --- Acquisition Tab ---
with tab_acquisition:
    acq_df = load_acquisition()
    acq_trend = load_acquisition_trend()
    filtered_trend = filter_by_time_range(acq_trend, "DATE", time_range)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### Channel Performance Over Time")
        if not filtered_trend.empty:
            filtered_trend["DATE"] = pd.to_datetime(filtered_trend["DATE"])
            weekly = filtered_trend.groupby(
                [pd.Grouper(key="DATE", freq="W"), "CHANNEL_GROUPING"]
            )["SESSIONS"].sum().reset_index()

            channel_chart = (
                alt.Chart(weekly)
                .mark_area(opacity=0.6, line=True)
                .encode(
                    x=alt.X("DATE:T", title=None, axis=alt.Axis(format="%b %Y")),
                    y=alt.Y("SESSIONS:Q", title=None, stack=True),
                    color=alt.Color("CHANNEL_GROUPING:N", title=None,
                                    scale=alt.Scale(
                                        domain=list(CHANNEL_COLORS.keys()),
                                        range=list(CHANNEL_COLORS.values())
                                    ),
                                    legend=alt.Legend(orient="bottom", columns=4)),
                    tooltip=[
                        alt.Tooltip("DATE:T", format="%Y-%m-%d"),
                        alt.Tooltip("CHANNEL_GROUPING:N", title="Channel"),
                        alt.Tooltip("SESSIONS:Q", format=","),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(channel_chart, use_container_width=True)

    with col2:
        st.markdown("### Channel Split")
        if not acq_df.empty:
            channel_pie = (
                alt.Chart(acq_df)
                .mark_arc(innerRadius=50, outerRadius=100)
                .encode(
                    theta=alt.Theta("SESSIONS:Q"),
                    color=alt.Color("CHANNEL_GROUPING:N", title=None,
                                    scale=alt.Scale(
                                        domain=list(CHANNEL_COLORS.keys()),
                                        range=list(CHANNEL_COLORS.values())
                                    ),
                                    legend=alt.Legend(orient="bottom", columns=2)),
                    tooltip=["CHANNEL_GROUPING:N", alt.Tooltip("SESSIONS:Q", format=",")],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(channel_pie, use_container_width=True)

    st.markdown("### Channel Metrics")
    if not acq_df.empty:
        display_df = acq_df.copy()
        display_df.columns = ["Channel", "Sessions", "New Users", "Revenue", "Bounces", "Pageviews"]
        for c in ["Sessions", "New Users", "Revenue", "Bounces", "Pageviews"]:
            display_df[c] = pd.to_numeric(display_df[c], errors="coerce")
        display_df["Conv. Rate"] = (display_df["Revenue"] / display_df["Sessions"]).round(2)
        st.dataframe(display_df[["Channel", "Sessions", "New Users", "Revenue", "Conv. Rate"]], hide_index=True)

# --- Geography & Devices Tab ---
with tab_geo:
    geo_df = load_geo()
    devices_df = load_devices()
    browsers_df = load_browsers()

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### Top Countries by Sessions")
        if not geo_df.empty:
            top_geo = geo_df.head(15)
            geo_chart = (
                alt.Chart(top_geo)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                .encode(
                    x=alt.X("SESSIONS:Q", title=None),
                    y=alt.Y("COUNTRY:N", title=None, sort="-x"),
                    color=alt.Color("SESSIONS:Q", scale=alt.Scale(scheme="teals"), legend=None),
                    tooltip=[
                        alt.Tooltip("COUNTRY:N"),
                        alt.Tooltip("SESSIONS:Q", format=","),
                        alt.Tooltip("REVENUE:Q", title="Revenue", format="$,.0f"),
                        alt.Tooltip("BOUNCE_RATE:Q", title="Bounce %", format=".1f"),
                    ],
                )
                .properties(height=380)
            )
            st.altair_chart(geo_chart, use_container_width=True)

    with col2:
        st.markdown("### Device Category")
        if not devices_df.empty:
            device_pie = (
                alt.Chart(devices_df)
                .mark_arc(innerRadius=45, outerRadius=90)
                .encode(
                    theta=alt.Theta("SESSIONS:Q"),
                    color=alt.Color("DEVICE_CATEGORY:N", title=None,
                                    scale=alt.Scale(range=["#29B5E8", "#6C63FF", "#FF6B9D"]),
                                    legend=alt.Legend(orient="bottom")),
                    tooltip=["DEVICE_CATEGORY:N", alt.Tooltip("SESSIONS:Q", format=",")],
                )
                .properties(height=200)
            )
            st.altair_chart(device_pie, use_container_width=True)

        st.markdown("### Top Browsers")
        if not browsers_df.empty:
            browser_chart = (
                alt.Chart(browsers_df.head(8))
                .mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3, color="#6C63FF")
                .encode(
                    x=alt.X("SESSIONS:Q", title=None),
                    y=alt.Y("BROWSER:N", title=None, sort="-x"),
                    tooltip=["BROWSER:N", alt.Tooltip("SESSIONS:Q", format=",")],
                )
                .properties(height=180)
            )
            st.altair_chart(browser_chart, use_container_width=True)

# --- E-Commerce Tab ---
with tab_ecommerce:
    filtered_ecom_chart = filtered_ecom.copy()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Revenue Over Time")
        if not filtered_ecom_chart.empty:
            filtered_ecom_chart["DATE"] = pd.to_datetime(filtered_ecom_chart["DATE"])
            filtered_ecom_chart["revenue_7d"] = filtered_ecom_chart["REVENUE"].rolling(7, min_periods=1).mean()

            rev_chart = (
                alt.Chart(filtered_ecom_chart)
                .mark_area(opacity=0.3, line={"color": "#29B5E8"}, color="#29B5E8")
                .encode(
                    x=alt.X("DATE:T", title=None, axis=alt.Axis(format="%b %Y")),
                    y=alt.Y("revenue_7d:Q", title=None, scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip("DATE:T", format="%Y-%m-%d"),
                        alt.Tooltip("revenue_7d:Q", title="Revenue (7d avg)", format="$,.0f"),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(rev_chart, use_container_width=True)

    with col2:
        st.markdown("### Conversion Rate Trend")
        if not filtered_ecom_chart.empty:
            filtered_ecom_chart["conv_7d"] = filtered_ecom_chart["CONVERSION_RATE_PCT"].rolling(7, min_periods=1).mean()
            conv_chart = (
                alt.Chart(filtered_ecom_chart)
                .mark_line(color="#45B7AA", strokeWidth=2)
                .encode(
                    x=alt.X("DATE:T", title=None, axis=alt.Axis(format="%b %Y")),
                    y=alt.Y("conv_7d:Q", title="Conversion %", scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip("DATE:T", format="%Y-%m-%d"),
                        alt.Tooltip("conv_7d:Q", title="Conv. Rate %", format=".3f"),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(conv_chart, use_container_width=True)

    col3, col4, col5 = st.columns(3)
    if not filtered_ecom_chart.empty:
        avg_aov = filtered_ecom_chart["AVG_ORDER_VALUE"].dropna().mean()
        avg_conv = filtered_ecom_chart["CONVERSION_RATE_PCT"].mean()
        col3.metric("Avg Order Value", f"${avg_aov:.2f}" if avg_aov else "$0")
        col4.metric("Avg Conversion Rate", f"{avg_conv:.3f}%")
        col5.metric("Revenue per Session", f"${total_revenue / max(total_sessions, 1):.2f}")

    st.markdown("### Transactions by Day of Week")
    if not filtered_ecom_chart.empty:
        filtered_ecom_chart["dow"] = filtered_ecom_chart["DATE"].dt.day_name()
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_df = filtered_ecom_chart.groupby("dow")["TRANSACTIONS"].mean().reindex(dow_order).reset_index()
        dow_df.columns = ["day", "avg_transactions"]

        dow_chart = (
            alt.Chart(dow_df)
            .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color="#6C63FF")
            .encode(
                x=alt.X("day:N", title=None, sort=dow_order),
                y=alt.Y("avg_transactions:Q", title="Avg Transactions"),
                tooltip=["day:N", alt.Tooltip("avg_transactions:Q", format=".1f")],
            )
            .properties(height=200)
        )
        st.altair_chart(dow_chart, use_container_width=True)

# --- Content Tab ---
with tab_content:
    pages_df = load_top_pages()

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### Top Pages by Traffic")
        if not pages_df.empty:
            top10 = pages_df.head(10).copy()
            top10["page_short"] = top10["PAGE_PATH"].str[:50]

            pages_chart = (
                alt.Chart(top10)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                .encode(
                    x=alt.X("TOTAL_HITS:Q", title="Total Hits"),
                    y=alt.Y("page_short:N", title=None, sort="-x"),
                    color=alt.Color("TOTAL_HITS:Q", scale=alt.Scale(scheme="blues"), legend=None),
                    tooltip=[
                        alt.Tooltip("PAGE_PATH:N", title="Page"),
                        alt.Tooltip("TOTAL_HITS:Q", title="Hits", format=","),
                        alt.Tooltip("ENTRANCES:Q", format=","),
                        alt.Tooltip("EXITS:Q", format=","),
                        alt.Tooltip("EXIT_RATE_PCT:Q", title="Exit Rate %", format=".1f"),
                    ],
                )
                .properties(height=320)
            )
            st.altair_chart(pages_chart, use_container_width=True)

    with col2:
        st.markdown("### Entry vs Exit Pages")
        if not pages_df.empty:
            entry_exit = pages_df.head(10).copy()
            scatter = (
                alt.Chart(entry_exit)
                .mark_circle(opacity=0.7)
                .encode(
                    x=alt.X("ENTRANCES:Q", title="Entrances"),
                    y=alt.Y("EXITS:Q", title="Exits"),
                    size=alt.Size("TOTAL_HITS:Q", legend=None, scale=alt.Scale(range=[50, 500])),
                    color=alt.Color("EXIT_RATE_PCT:Q", title="Exit %",
                                    scale=alt.Scale(scheme="redyellowgreen", reverse=True)),
                    tooltip=[
                        alt.Tooltip("PAGE_PATH:N", title="Page"),
                        alt.Tooltip("ENTRANCES:Q", format=","),
                        alt.Tooltip("EXITS:Q", format=","),
                        alt.Tooltip("EXIT_RATE_PCT:Q", title="Exit %", format=".1f"),
                    ],
                )
                .properties(height=320)
            )
            st.altair_chart(scatter, use_container_width=True)

    st.markdown("### All Pages")
    if not pages_df.empty:
        st.dataframe(pages_df, hide_index=True)
