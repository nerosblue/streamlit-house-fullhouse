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

# --- 1. DEFINE REGION HIERARCHY ---
# Since the CSV is flat, we map parents (Counties/Regions) to children (Cities/Districts) manually.
# You can expand this list.
REGION_HIERARCHY = {
    "Nottinghamshire": [
        "Nottingham", "Rushcliffe", "Broxtowe", "Gedling", 
        "Newark and Sherwood", "Mansfield", "Ashfield", "Bassetlaw", 
        "Nottinghamshire" # Include the county average itself
    ],
    "Derbyshire": [
        "Derby", "Amber Valley", "Bolsover", "Chesterfield", 
        "Derbyshire Dales", "Erewash", "High Peak", 
        "North East Derbyshire", "South Derbyshire"
    ],
    "London": [
        "London", "Barking and Dagenham", "Barnet", "Bexley", "Brent", 
        "Bromley", "Camden", "City of London", "Croydon", "Ealing", 
        "Enfield", "Greenwich", "Hackney", "Hammersmith and Fulham", 
        "Haringey", "Harrow", "Havering", "Hillingdon", "Hounslow", 
        "Islington", "Kensington and Chelsea", "Kingston upon Thames", 
        "Lambeth", "Lewisham", "Merton", "Newham", "Redbridge", 
        "Richmond upon Thames", "Southwark", "Sutton", "Tower Hamlets", 
        "Waltham Forest", "Wandsworth", "Westminster"
    ],
    "All Data": [] # Fallback to show everything if needed
}

# --- Data Loading and Preprocessing ---

@st.cache_data
def load_data():
    """Loads and preprocesses the UK HPI data."""
    # Load the CSV file (Make sure this matches your actual filename)
    df = pd.read_csv("UK-HPI-full-Shorted 2.csv")

    # Convert Date column
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
    
    # Drop rows where Date or RegionName is missing
    df = df.dropna(subset=['Date', 'RegionName'])

    # Ensure necessary columns are numeric
    numeric_cols = [
        'AveragePrice', '12m%Change', 
        'SemiDetachedPrice', 'TerracedPrice', 'FlatPrice', 
        'FTBPrice', 'FTBIndex', 'FTB12m%Change'
    ]
    for col in numeric_cols:
        # Clean up any non-numeric characters if they exist
        if df[col].dtype == 'object':
             df[col] = df[col].astype(str).str.replace(',', '', regex=False)
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

st.sidebar.header("Navigation Tab")
st.sidebar.subheader("Location Selection")

# 1. Select Parent Region (e.g., Nottinghamshire)
# We use the keys from our dictionary
parent_regions = list(REGION_HIERARCHY.keys())
# Remove 'All Data' from the top list to put it at the end or treat differently if desired
if "All Data" in parent_regions:
    parent_regions.remove("All Data")
    parent_regions.sort()
    parent_regions.append("All Data") # Add back at end

selected_parent = st.sidebar.selectbox(
    "1. Select Region / County:",
    options=parent_regions,
    index=parent_regions.index("Nottinghamshire") if "Nottinghamshire" in parent_regions else 0
)

# 2. Select Specific City/District based on Parent
if selected_parent == "All Data":
    # If "All Data" selected, show ALL unique regions in the CSV
    available_cities = sorted(df['RegionName'].unique())
else:
    # Otherwise, use the list from our Dictionary
    available_cities = sorted(REGION_HIERARCHY[selected_parent])

selected_region = st.sidebar.selectbox(
    f"2. Select City in {selected_parent}:",
    options=available_cities
)

# 3. Time Period Selection (Date Range)
st.sidebar.subheader("Time Period")
min_date = df['Date'].min().date()
max_date = df['Date'].max().date()

date_range = st.sidebar.date_input(
    "Select Dates:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(date_range) == 2:
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
else:
    start_date = pd.to_datetime(min_date)
    end_date = pd.to_datetime(max_date)

# --- Data Filtering ---
# We filter by 'selected_region' which is the specific city/district selected in dropdown #2
filtered_df = df[
    (df['RegionName'] == selected_region) &
    (df['Date'] >= start_date) &
    (df['Date'] <= end_date)
].sort_values(by='Date')

# Check if data exists for this selection
if filtered_df.empty:
    st.error(f"No data found for **{selected_region}**. It might be named differently in the CSV file.")
    st.stop()

latest_date = filtered_df['Date'].max()
latest_data_rows = filtered_df[filtered_df['Date'] == latest_date]

if latest_data_rows.empty:
    st.error(f"No data available for **{selected_region}** in the selected time period.")
    st.stop()

latest_data_row = latest_data_rows.iloc[0]


# --- Main Dashboard Content ---

st.title(f"HomeAgent Dashboard: {selected_region}")
st.caption(f"Region Group: {selected_parent}")
st.markdown("This is the historic price change over time up to June 2025")

# Split columns
col_viz_1, col_viz_2, col_metrics_3 = st.columns([2, 1.5, 1])

# --- Column 1: Average Price Time Series Chart ---
with col_viz_1:
    st.subheader("Price Trend Over Time")
    
    fig_price = px.line(
        filtered_df.dropna(subset=['AveragePrice']), 
        x='Date',
        y='AveragePrice',
        title=f'Average House Price Trend',
        labels={'AveragePrice': 'Average Price (£)', 'Date': 'Date'},
        template="plotly_white"
    )
    fig_price.update_yaxes(tickprefix='£')
    fig_price.update_layout(hovermode="x unified", title_font_size=16)
    st.plotly_chart(fig_price, use_container_width=True)

# --- Column 2: House Type Prices Bar Chart ---
with col_viz_2:
    st.subheader("Prices by Type")

    house_type_prices = {
        'House Type': ['Semi-Detached', 'Terraced', 'Flat'],
        'Price': [
            latest_data_row.get('SemiDetachedPrice', None),
            latest_data_row.get('TerracedPrice', None),
            latest_data_row.get('FlatPrice', None)
        ]
    }
    df_house_types = pd.DataFrame(house_type_prices).dropna(subset=['Price'])

    if not df_house_types.empty:
        fig_types = px.bar(
            df_house_types,
            x='House Type',
            y='Price',
            title=f'Avg. Price ({latest_date.strftime("%b %Y")})',
            labels={'Price': 'Average Price (£)'},
            color='House Type',
            template="plotly_white",
        )
        fig_types.update_yaxes(tickprefix='£')
        fig_types.update_layout(showlegend=False, title_font_size=16)
        st.plotly_chart(fig_types, use_container_width=True)
    else:
        st.info("House type data (Semi, Terraced, Flat) is not available for this specific selection.")

# --- Column 3: Key Metrics ---
with col_metrics_3:
    st.subheader("Key Metrics")
    st.markdown(f"**{latest_date.strftime('%B %Y')}**")
    st.markdown("---")

    # Metric 1: Average Price
    latest_price = latest_data_row['AveragePrice']
    if not pd.isna(latest_price):
        st.metric(
            label="Avg Price (All)",
            value=f"£{latest_price:,.0f}"
        )
    else:
         st.metric(label="Avg Price (All)", value="N/A")

    # Metric 2: 12m Change
    annual_change = latest_data_row['12m%Change']
    if not pd.isna(annual_change):
        st.metric(
            label="Annual Change",
            value=f"{annual_change:.1f}%",
            delta=f"{annual_change:.1f}%",
            delta_color="normal" if annual_change < 0 else "inverse" 
        )
    else:
        st.metric(label="Annual Change", value="N/A")

    st.markdown("### FTB Metrics")
    st.markdown("---")

    # Metric 3: FTB Price
    ftb_price = latest_data_row.get('FTBPrice', None)
    if not pd.isna(ftb_price):
        st.metric(
            label="First Time Buyer Price",
            value=f"£{ftb_price:,.0f}"
        )
    else:
        st.metric(label="FTB Price", value="N/A")
        
    # Metric 4: FTB Annual Change
    ftb_annual_change = latest_data_row.get('FTB12m%Change', None)
    if not pd.isna(ftb_annual_change):
        st.metric(
            label="FTB Annual Change",
            value=f"{ftb_annual_change:.1f}%",
            delta=f"{ftb_annual_change:.1f}%",
            delta_color="normal" if ftb_annual_change < 0 else "inverse" 
        )
    else:
        st.metric(label="FTB Annual Change", value="N/A")

st.markdown("---")
