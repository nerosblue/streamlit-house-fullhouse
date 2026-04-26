import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import requests

# --- Opening Page ---
st.set_page_config(
    page_title="Manchester House Price Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Data Loading and Preprocessing ---
@st.cache_data
def load_data():
    """Loads and preprocesses the UK HPI data."""
    df = pd.read_csv("MCRActualFull2026.csv")

    # Convert Date into datetime objects, coerce errors to NaT
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')

    # Drop rows where Date or RegionName is missing
    df = df.dropna(subset=['Date', 'RegionName'])

    # Ensure necessary columns are numeric, coercing errors to NaN
    numeric_cols = [
        'AveragePrice',
        'SemiDetachedPrice',
        'TerracedPrice',
        'FlatPrice',
        'FTBPrice',
        '12m%Change',
        'SalesVolume'
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


data_load_state = st.text('Loading your data...')

try:
    df = load_data()
    data_load_state.success('Data loaded and processed successfully.')
except Exception as e:
    data_load_state.error(f"Error loading data: {e}")
    st.stop()


# --- Sidebar: Navigation & Filtering ---
all_regions = sorted(df['RegionName'].unique())

st.sidebar.header("Navigation Tab - Filter by region")
st.sidebar.subheader("Morning Davida")

# 1. Region Dropdown
default_region = (
    'Greater Manchester' if 'Greater Manchester' in all_regions
    else (all_regions[0] if all_regions else 'No Region')
)
selected_region = st.sidebar.selectbox(
    "Select City to Analyse:",
    options=all_regions,
    index=all_regions.index(default_region) if default_region in all_regions else 0
)

# 2. Time Period Selection
min_date = df['Date'].min().date()
max_date = df['Date'].max().date()

date_range = st.sidebar.date_input(
    "Select Time Period:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Ensure date_range has two elements
if len(date_range) == 2:
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
else:
    start_date = pd.to_datetime(min_date)
    end_date = pd.to_datetime(max_date)


# --- Data Filtering ---
filtered_df = df[
    (df['RegionName'] == selected_region) &
    (df['Date'] >= start_date) &
    (df['Date'] <= end_date)
].sort_values(by='Date')

# Get latest available data row
latest_date = filtered_df['Date'].max()
latest_data_rows = filtered_df[filtered_df['Date'] == latest_date]

if filtered_df.empty or latest_data_rows.empty:
    st.error(f"No data available for **{selected_region}** in the selected time period.")
    st.stop()

latest_data_row = latest_data_rows.iloc[0]


# --- Main Dashboard Content ---
st.title(f"HomeAgent Dashboard Home for {selected_region}")
st.markdown("This is the historic price change over time up to November 2025")

# --- Row 1: Two Charts ---
col_viz_1, col_viz_2 = st.columns([2, 1.5])

# Column 1: Average Price Time Series Chart
with col_viz_1:
    st.subheader("Price Trend Over Time")

    fig_price = px.line(
        filtered_df.dropna(subset=['AveragePrice']),
        x='Date',
        y='AveragePrice',
        title=f'Average House Price Trend ({filtered_df["Date"].min().strftime("%Y")} - {filtered_df["Date"].max().strftime("%Y")})',
        labels={'AveragePrice': 'Average Price (£)', 'Date': 'Date'},
        template="plotly_white"
    )
    fig_price.update_yaxes(tickprefix='£')
    fig_price.update_layout(hovermode="x unified", title_font_size=16)
    st.plotly_chart(fig_price, use_container_width=True)

# Column 2: House Type Prices Bar Chart
with col_viz_2:
    st.subheader("House type prices over time")

    house_type_prices = {
        'House Type': ['Semi-Detached', 'Terraced', 'Flat'],
        'Price': [
            latest_data_row['SemiDetachedPrice'],
            latest_data_row['TerracedPrice'],
            latest_data_row['FlatPrice']
        ]
    }
    df_house_types = pd.DataFrame(house_type_prices).dropna(subset=['Price'])

    if not df_house_types.empty:
        fig_types = px.bar(
            df_house_types,
            x='House Type',
            y='Price',
            title=f'Avg. Price by House Type ({latest_date.strftime("%b %Y")})',
            labels={'Price': 'Average Price (£)'},
            color='House Type',
            template="plotly_white",
        )
        fig_types.update_yaxes(tickprefix='£')
        fig_types.update_layout(showlegend=False, title_font_size=16)
        st.plotly_chart(fig_types, use_container_width=True)
    else:
        st.info("House type data (Semi-Detached, Terraced, Flat) is not available for the latest selected date.")


# --- Row 2: Key Metrics ---
st.subheader("First Time Buyer Key Price Metrics")
st.markdown(f"**Data for: {latest_date.strftime('%B %Y')}**")
st.markdown("---")

col_met_1, col_met_2, col_met_3 = st.columns(3)

# Metric 1: Latest Average Price
with col_met_1:
    latest_price = latest_data_row['AveragePrice']
    if not pd.isna(latest_price):
        st.metric(label="Average Price (All Types)", value=f"£{latest_price:,.0f}")
    else:
        st.metric(label="Average Price (All Types)", value="N/A")

# Metric 2: Latest 12-Month Change
with col_met_2:
    annual_change = latest_data_row['12m%Change']
    if not pd.isna(annual_change):
        delta_val = f"{annual_change:.1f}%"
        st.metric(
            label="Annual Price Change (12m%)",
            value=f"{annual_change:.1f}%",
            delta=delta_val,
            delta_color="normal" if annual_change < 0 else "inverse"
        )
    else:
        st.metric(label="Annual Price Change (12m%)", value="N/A")

# Metric 3: First Time Buyer Price
with col_met_3:
    ftb_price = latest_data_row['FTBPrice']
    if not pd.isna(ftb_price):
        st.metric(label="Avg. First Time Buyer Price", value=f"£{ftb_price:,.0f}")
    else:
        st.metric(label="Avg. First Time Buyer Price", value="N/A")


# --- Row 3: Sales Volume Bar Chart ---
st.markdown("---")
st.subheader("Monthly Sales Volume")

fig_volume = px.bar(
    filtered_df.dropna(subset=['SalesVolume']).assign(
        Date=filtered_df['Date'].dt.strftime('%b %Y')
    ),
    x='Date',
    y='SalesVolume',
    title='Monthly Sales Volume',
    labels={'SalesVolume': 'Number of Sales', 'Date': 'Date'},
    template="plotly_white",
    color='SalesVolume',
    color_continuous_scale='Blues'
)
st.plotly_chart(fig_volume, use_container_width=True)


# --- Footer ---
st.markdown("---")
st.caption(f"Showing data for: {selected_region}. Filter the time period using the sidebar.")


#n8n connection
N8N_WEBHOOK_URL = "https://kindred-rupture-onstage.ngrok-free.dev/webhook/nathanagent"

def send_message(user_message: str, chat_history: list) -> str:
    payload = {
        "message": user_message,
        "history": chat_history  # optional, for context
    }
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("output", "No response received.")  # adjust key to match your n8n output
    except requests.exceptions.Timeout:
        return "Request timed out. Please try again."
    except Exception as e:
        return f"Error: {str(e)}"


# --- Chat UI ---
st.title("AI Assistant")

# Initialise chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render existing messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle new input
if prompt := st.chat_input("Ask me anything..."):

    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get and show agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = send_message(prompt, st.session_state.messages)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

def send_message(user_message: str, chat_history: list) -> str:
    payload = {"message": user_message, "history": chat_history}
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=120)
        response.raise_for_status()
        # Handle both plain text and JSON responses
        try:
            data = response.json()
            return data.get("output", "No response received.")
        except:
            return response.text
    except requests.exceptions.Timeout:
        return "Request timed out. Please try again."
    except Exception as e:
        return f"Error: {str(e)}"
