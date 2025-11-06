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
    """Loads and preprocesses the UK HPI data."""
    # Load the CSV file provided in the environment
    df = pd.read_csv("UK-HPI-full-file-2025-06.csv")

    # Convert Date column to datetime objects using the expected format
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
    
    # Drop rows where RegionName is missing
    df = df.dropna(subset=['RegionName'])

    # Ensure necessary columns are numeric
    numeric_cols = ['AveragePrice', '12m%Change']
    for col in numeric_cols:
        # Convert to numeric, coercing errors (like blank values) to NaN
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

data_load_state = st.text('Loading data...')
try:
    df = load_data()
    data_load_state.success('Data loaded successfully! (using "UK-HPI-full-file-2025-06.csv")')
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

latest_data = filtered_df.iloc[-1]
earliest_data = filtered_df.iloc[0]

# 1. Latest Average Price
latest_price = latest_data['AveragePrice']
col1.metric(
    label=f"Latest Avg. Price ({latest_data['Date'].strftime('%b %Y')})",
    value=f"£{latest_price:,.0f}"
)

# 2. Latest 12-Month Change
annual_change = latest_data['12m%Change']
if not pd.isna(annual_change):
    # Determine the delta format for visual representation
    delta_val = f"{annual_change:.1f}%"
    col2.metric(
        label="Latest 12-Month Price Change",
        value=f"{annual_change:.1f}%",
        delta=delta_val,
        delta_color="normal" if annual_change < 0 else "inverse"
    )
else:
    col2.metric(label="Latest 12-Month Price Change", value="N/A")


# 3. Total Price Change over selected period
if len(filtered_df) > 1:
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
        col3.metric(label="Total Price Change", value="Insufficient Data")
else:
    col3.metric(label="Total Price Change", value="N/A (Need more data points)")


st.markdown("---")


# --- Visualizations ---

# 1. Average Price Over Time (Line Chart)
st.subheader("Average House Price (£) Over Time")
fig_price = px.line(
    filtered_df,
    x='Date',
    y='AveragePrice',
    title=f'Monthly Average House Price in {selected_region}',
    labels={'AveragePrice': 'Average Price (£)', 'Date': 'Date'},
    template="plotly_white"
)
fig_price.update_yaxes(tickprefix='£')
fig_price.update_layout(hovermode="x unified")
st.plotly_chart(fig_price, use_container_width=True)


# 2. 12-Month Percentage Change Over Time (Bar Chart)
st.subheader("12-Month Percentage Change (%)")
fig_change = px.bar(
    filtered_df,
    x='Date',
    y='12m%Change',
    title=f'Annual House Price Growth in {selected_region}',
    labels={'12m%Change': 'Annual Change (%)', 'Date': 'Date'},
    template="plotly_white",
    # Set the color based on whether the change is positive or negative
    color='12m%Change',
    color_continuous_scale=['red', 'green'], 
    color_continuous_midpoint=0
)
fig_change.update_yaxes(ticksuffix='%')
fig_change.update_layout(hovermode="x unified", coloraxis_showscale=False)
st.plotly_chart(fig_change, use_container_width=True)

st.markdown("---")
st.caption("Data source: UK House Price Index (HPI). Prices are non-seasonally adjusted. The dashboard updates instantly when you change the filters on the left.")
