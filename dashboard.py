import streamlit as st
import pandas as pd
import plotly.express as px
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
    """Loads and preprocesses the UK HPI data from the new 'UK-HPI-full-Shorted 2.csv' file."""
    # Load the new CSV file
    df = pd.read_csv("UK-HPI-full-Shorted 2.csv")

    # Convert Date column to datetime objects using the expected format
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
    
    # Drop rows where RegionName is missing
    df = df.dropna(subset=['RegionName'])

    # Ensure necessary columns are numeric
    # We rely on 'AveragePrice' and '12m%Change' for core visualizations
    numeric_cols = ['AveragePrice', '12m%Change']
    for col in numeric_cols:
        # Convert to numeric, coercing errors (like blank values) to NaN
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

data_load_state = st.text('Loading data...')
try:
    df = load_data()
    # Confirming which file was used
    data_load_state.success('Data loaded successfully! (using "UK-HPI-full-Shorted 2.csv")')
except Exception as e:
    data_load_state.error(f"Error loading data: {e}")
    st.stop()


# --- Sidebar (Navigation Bar) for Filtering ---

# Get unique regions for the dropdown
all_regions = sorted(df['RegionName'].unique())

st.sidebar.header("Filter & Select Region")

# 1. Region Dropdown (Dropdown bar menu)
default_region = 'London' if 'London' in all_regions else (all_regions[0] if all_regions else 'No Region')
selected_region = st.sidebar.selectbox(
    "Select Region to Analyse:",
    options=all_regions,
    index=all_regions.index(default_region) if default_region in all_regions else 0
)

# 2. Time Period Selection (Date Range)
min_date = df['Date'].min().date()
max_date = df['Date'].max().date()

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
    # If the user only selected one date, use the full range as fallback
    start_date = pd.to_datetime(min_date)
    end_date = pd.to_datetime(max_date)

# --- Data Filtering ---
filtered_df = df[
    (df['RegionName'] == selected_region) &
    (df['Date'] >= start_date) &
    (df['Date'] <= end_date)
].sort_values(by='Date')

# Check if data is available after filtering
if filtered_df.empty:
    st.error(f"No data available for **{selected_region}** in the selected time period.")
    st.stop()


# --- Main Dashboard Content ---

st.title(f"🏠 UK House Price Index Analysis for {selected_region}")
st.markdown("Use the navigation bar on the left to select a region and adjust the time period for analysis.")

# --- Key Metrics ---
col1, col2, col3 = st.columns(3)

# Filter out rows where AveragePrice is NaN to find meaningful metrics
metric_df = filtered_df.dropna(subset=['AveragePrice', '12m%Change'])

if not metric_df.empty:
    latest_data = metric_df.iloc[-1]
    earliest_data = metric_df.iloc[0]

    # 1. Latest Average Price
    latest_price = latest_data['AveragePrice']
    col1.metric(
        label=f"Latest Avg. Price ({latest_data['Date'].strftime('%b %Y')})",
        value=f"£{latest_price:,.0f}"
    )

    # 2. Latest 12-Month Change
    annual_change = latest_data['12m%Change']
    if not pd.isna(annual_change):
        # Determine the delta format for visual representation (red for negative, green for positive)
        delta_val = f"{annual_change:.1f}%"
        col2.metric(
            label="Latest 12-Month Price Change",
            value=f"{annual_change:.1f}%",
            # delta_color="normal" (green/positive) if change is negative, "inverse" (red/negative) if change is positive
            # This is inverted because property value increases are often seen as positive.
            delta=delta_val,
            delta_color="normal" if annual_change < 0 else "inverse"
        )
    else:
        col2.metric(label="Latest 12-Month Price Change", value="N/A")


    # 3. Total Price Change over selected period
    if len(metric_df) > 1:
        start_price = earliest_data['AveragePrice']
        end_price = latest_price
        
        if not pd.isna(start_price) and not pd.isna(end_price) and start_price != 0:
            total_change_percent = ((end_price - start_price) / start_price) * 100
            
            delta_val = f"{total_change_percent:.1f}%"
            
            col3.metric(
                label=f"Price Change ({earliest_data['Date'].strftime('%Y')} - {latest_data['Date'].strftime('%Y')})",
                value=f"{total_change_percent:.1f}%",
                delta=delta_val,
                delta_color="normal" if total_change_percent < 0 else "inverse"
            )
        else:
            col3.metric(label="Total Price Change", value="Insufficient Price Data")
    else:
        col3.metric(label="Total Price Change", value="N/A (Need more data points)")
