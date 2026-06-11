# GA Analytics Dashboard

An interactive analytics dashboard for the **Google Merchandise Store** dataset, built with [Streamlit](https://streamlit.io/) and powered by [Snowflake](https://www.snowflake.com/). It turns raw Google Analytics session and hit-level data into clear, decision-ready visuals covering traffic, acquisition, geography, e-commerce, and content performance.

🔗 **Live app:** https://ga-analytics-dashboard-mka6xgtx3z4oboyueqzrkj.streamlit.app

---

## Features

- **KPI overview** — Sessions, users, pageviews, revenue, and conversion rate at a glance, with period-over-period deltas.
- **Traffic trends** — Daily sessions and users over selectable time ranges (1W, 1M, 3M, 6M, YTD, All).
- **Acquisition channels** — Breakdown of how visitors arrive (Organic Search, Direct, Social, Referral, Paid, etc.).
- **Geography & devices** — Top countries and device-category distribution.
- **E-commerce funnel** — From sessions to transactions, with revenue metrics.
- **Content** — Top pages by pageviews and engagement.
- **About the Data** — Built-in documentation page describing the schema, views, raw data, and key analysis decisions.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend / app | Streamlit |
| Data warehouse | Snowflake |
| Charts | Altair |
| Data handling | pandas, NumPy |
| Connectivity | `snowflake-snowpark-python`, `snowflake-connector-python` |

---

## Data Model

The app reads from the `GOOGLE_ANALYTICS.PUBLIC` schema in Snowflake.

**Tables**
- `FACT_SESSIONS` — session-level facts (~903K rows)
- `FACT_HITS` — hit-level events (~4.15M rows)
- `DIM_DATE` — date dimension

**Views** (pre-aggregated for fast dashboard queries)
- `V_DAILY_TRAFFIC` — daily sessions/users/pageviews
- `V_ACQUISITION_CHANNELS` — sessions and revenue by channel
- `V_GEO_SUMMARY` — metrics by country
- `V_ECOMMERCE_FUNNEL` — funnel and revenue metrics
- `V_TOP_PAGES` — page-level engagement

---

## Running Locally

### Prerequisites
- Python 3.9+
- A Snowflake account with access to the `GOOGLE_ANALYTICS` database

### 1. Clone and install
```bash
git clone https://github.com/navaneethak08/ga-analytics-dashboard.git
cd ga-analytics-dashboard
pip install -r requirements.txt
```

### 2. Configure Snowflake credentials
Create `.streamlit/secrets.toml` (this file is git-ignored):
```toml
[connections.snowflake]
account = "SFEDU05-GYB84614"
user = "<your_user>"
password = "<your_password>"
warehouse = "<your_warehouse>"
database = "GOOGLE_ANALYTICS"
schema = "PUBLIC"
```

> **Note:** The `account` value uses the `ORG_NAME-ACCOUNT_NAME` format required for external connections.

### 3. Run
```bash
streamlit run streamlit_app.py
```

The app opens at `http://localhost:8501`.

---

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and create a new app from the repo.
3. Set the main file path to `streamlit_app.py`.
4. Under **App settings → Secrets**, paste the same `[connections.snowflake]` block shown above.
5. Deploy. The app auto-redeploys on every push to `main`.

---

## Project Structure

```
ga-analytics-dashboard/
├── streamlit_app.py          # Main Streamlit application
├── requirements.txt          # Python dependencies
├── .streamlit/
│   └── config.toml           # Dark theme configuration
└── README.md
```

---

## License

This project is for educational and demonstration purposes using the publicly available Google Merchandise Store dataset.
