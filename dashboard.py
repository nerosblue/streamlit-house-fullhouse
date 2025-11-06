import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# Set up the Streamlit page configuration
st.set_page_config(
    page_title="UK House Price Index Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Data Loading and Preprocessing ---

@st.cache_data
def load_data():
    """Loads and preprocesses the UK HPI data."""
    # Load the new CSV file
    df = pd.read_csv("UK-HPI-full-Shorted 2.csv")

    # Convert Date column to datetime objects using the expected format
    # Using 'coerce' for errors to turn invalid dates into NaT
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
    
    # Drop rows where Date or RegionName is missing
    df = df.dropna(subset=['Date', 'RegionName'])

    # Ensure necessary columns are numeric, coercing errors to NaN
    numeric_cols = [
        'AveragePrice', '12m%Change', 
        'SemiDetachedPrice', 'TerracedPrice', 'FlatPrice', 
        'FTBPrice', 'FTBIndex', 'FTB12m%Change'
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

data_load_state = st.text('Loading data...')
try:
    df = load_data()
    data_load_state.success('Data loaded and processed successfully.')
except Exception as e:
    data_load_state.error(f"Error loading data: {e}")
    st.stop()


# --- Sidebar (Navigation Tab) for Filtering ---

# Get unique regions for the dropdown
all_regions = sorted(df['RegionName'].unique())

st.sidebar.header("Navigation Tab: Filter by region")
st.sidebar.subheader("Afternoon Amber")
# 1. Region Dropdown
default_region = 'Nottinghamshire' if 'Nottinghamshire' in all_regions else (all_regions[0] if all_regions else 'No Region')
selected_region = st.sidebar.selectbox(
    "Select Region to Analyse:",
    options=all_regions,
    index=all_regions.index(default_region) if default_region in all_regions else 0
)

# 2. Time Period Selection (Date Range)
min_date = df['Date'].min().date()
max_date = df['Date'].max().date()

# Note: st.date_input behavior is typically to drop downwards by default.
date_range = st.sidebar.date_input(
    "Select Time Period:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Ensure date_range has two elements (start and end date)
if len(date_range) == 2:
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
else:
    # Fallback if the user only selected one date
    start_date = pd.to_datetime(min_date)
    end_date = pd.to_datetime(max_date)

# --- Data Filtering ---
filtered_df = df[
    (df['RegionName'] == selected_region) &
    (df['Date'] >= start_date) &
    (df['Date'] <= end_date)
].sort_values(by='Date')

# Filter for the latest month's data in the selected period for bar charts/metrics
latest_date = filtered_df['Date'].max()
# Ensure we have data for the latest date before proceeding
latest_data_rows = filtered_df[filtered_df['Date'] == latest_date]

if filtered_df.empty or latest_data_rows.empty:
    st.error(f"No data available for **{selected_region}** in the selected time period.")
    st.stop()

# We take the first row of the latest data (should only be one per date/region)
latest_data_row = latest_data_rows.iloc[0]


# --- Main Dashboard Content ---

st.title(f"HomeAgent Dashboard Home {selected_region}")
st.markdown("This is the historic price change over time up to June 2025")

# Split the main content into three columns
# [2, 1.5, 1] means the first column is widest, the second is medium, and the third (metrics) is narrowest
col_viz_1, col_viz_2, col_metrics_3 = st.columns([2, 1.5, 1])

# --- Column 1: Average Price Time Series Chart ---
with col_viz_1:
    st.subheader("Price Trend Over Time")
    
    fig_price = px.line(
        filtered_df.dropna(subset=['AveragePrice']), # Drop NaNs for cleaner line plot
        x='Date',
        y='AveragePrice',
        title=f'Average House Price Trend ({filtered_df["Date"].min().strftime("%Y")} - {filtered_df["Date"].max().strftime("%Y")})',
        labels={'AveragePrice': 'Average Price (£)', 'Date': 'Date'},
        template="plotly_white"
    )
    fig_price.update_yaxes(tickprefix='£')
    fig_price.update_layout(hovermode="x unified", title_font_size=16)
    st.plotly_chart(fig_price, use_container_width=True)

# --- Column 2: House Type Prices Bar Chart ---
with col_viz_2:
    st.subheader("House type prices over time")

    # Create a DataFrame for the latest month's house type prices
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

# --- Column 3: Key Metrics (Avg Price, 12m Change, FTB Metrics) ---
with col_metrics_3:
    st.subheader("First Time Buyer Key Price Metrics")
    st.markdown(f"**Data for: {latest_date.strftime('%B %Y')}**")
    st.markdown("---")

    # --- Metric 1: Latest Average Price ---
    latest_price = latest_data_row['AveragePrice']
    if not pd.isna(latest_price):
        st.metric(
            label="Average Price (All Types)",
            value=f"£{latest_price:,.0f}"
        )
    else:
         st.metric(label="Average Price (All Types)", value="N/A")


    # --- Metric 2: Latest 12-Month Change ---
    annual_change = latest_data_row['12m%Change']
    if not pd.isna(annual_change):
        delta_val = f"{annual_change:.1f}%"
        st.metric(
            label="Annual Price Change (12m%)",
            value=f"{annual_change:.1f}%",
            delta=delta_val,
            # Inverse color for property increases (red for negative, green for positive)
            delta_color="normal" if annual_change < 0 else "inverse" 
        )
    else:
        st.metric(label="Annual Price Change (12m%)", value="N/A")


    st.markdown("### FTB Metrics")
    st.markdown("---")

    # --- Metric 3: First Time Buyer (FTB) Price ---
    ftb_price = latest_data_row['FTBPrice']
    if not pd.isna(ftb_price):
        st.metric(
            label="Avg. First Time Buyer Price",
            value=f"£{ftb_price:,.0f}"
        )
    else:
        st.metric(label="Avg. First Time Buyer Price", value="N/A")

    # --- Metric 4: FTB Index ---
    ftb_index = latest_data_row['FTBIndex']
    if not pd.isna(ftb_index):
        st.metric(
            label="FTB Index Value",
            value=f"{ftb_index:.1f}"
        )
    else:
        st.metric(label="FTB Index Value", value="N/A")
        
    # --- Metric 5: FTB 12m% Change ---
    ftb_annual_change = latest_data_row['FTB12m%Change']
    if not pd.isna(ftb_annual_change):
        delta_val_ftb = f"{ftb_annual_change:.1f}%"
        st.metric(
            label="FTB Annual Change (12m%)",
            value=f"{ftb_annual_change:.1f}%",
            delta=delta_val_ftb,
            delta_color="normal" if ftb_annual_change < 0 else "inverse" 
        )
    else:
        st.metric(label="FTB Annual Change (12m%)", value="N/A")

st.markdown("---")
st.caption(f"Showing data for: {selected_region}. Filter the time period using the sidebar.")
