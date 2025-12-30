"""
Oslo Parking Finder - Mobile-Friendly Streamlit App
"""
import streamlit as st
import pandas as pd
import numpy as np
import json
from math import radians, cos, sin, asin, sqrt
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
import base64

# Configure page for mobile
st.set_page_config(
    page_title="Oslo Zone D Grünerløkka Parking Finder",
    page_icon="🅿️",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# Convert the image to a base64 string
def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# Load your image from a local path
image_path = (r"cartoon.JPG")
# Get the base64 string of the image
image_base64 = image_to_base64(image_path)

# Display your image and name in the top right corner
st.markdown(
    f"""
    <style>
    .header {{
        position: fixed ;  /* Fix the position */
        top: 70px;  /* Adjust as needed */
        right: 20px;  /* Align to the right */
        display: flex;
        justify-content: flex-end;
        align-items: center;
        padding: 10px;
        flex-direction: column; /* Stack items vertically */
        text-align: center; /* Ensures text is centrally aligned */
        z-index: 999;
    }}
    .header img {{
        border-radius: 50%;
        width: 50px;
        height: 50px;
        margin-bottom: 5px; /* Space between image and text */
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}
    .header-text {{
        font-size: 12px;
        font-weight: normal; /* Regular weight for text */
        text-align: center;
        opacity: 0.8;
    }}
    </style>
    <div class="header">
        <img src="data:image/jpeg;base64,{image_base64}" alt="Mohsen Askar">
        <div class="header-text">Developed by: Mohsen Askar</div>
    </div>
    """,
    unsafe_allow_html=True
)


# Custom CSS for mobile-friendly design (theme-aware)
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    h1 {
        font-size: 1.8rem !important;
        margin-bottom: 1rem !important;
    }
    .stButton>button {
        width: 100%;
        background-color: #0066cc;
        color: white;
        font-size: 1.1rem;
        padding: 0.75rem;
        border-radius: 8px;
    }
    .parking-card {
        background-color: var(--background-color, rgba(128, 128, 128, 0.1));
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #0066cc;
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .parking-card {
            background-color: rgba(255, 255, 255, 0.05);
        }
    }
</style>
""", unsafe_allow_html=True)


def load_tariff_data(filepath='takstgruppe_lookup.json'):
    """Load tariff/pricing information"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tariff_data = json.load(f)
        return tariff_data
    except FileNotFoundError:
        return {}

def get_tariff_info(takstgruppe, tariff_data):
    """Get detailed pricing info for a tariff group"""
    if not tariff_data or not takstgruppe:
        return None
    
    # Convert to string and try to find match
    takst_str = str(int(takstgruppe)) if isinstance(takstgruppe, (int, float)) else str(takstgruppe)
    
    return tariff_data.get(takst_str)

def format_pricing_info(tariff_info, is_resident=False):
    """Format tariff information for display"""
    if not tariff_info:
        return "Ingen prisinformasjon tilgjengelig"
    
    if is_resident:
        # Resident parking info
        output = f"**{tariff_info.get('name', 'Beboerparkering')}**\n\n"
        
        if 'description' in tariff_info:
            output += f"ℹ️ {tariff_info['description']}\n\n"
        
        if 'avgiftstid' in tariff_info:
            output += f"🕐 **Avgiftstid:** {tariff_info['avgiftstid']}\n\n"
        
        if 'note' in tariff_info:
            output += f"📝 {tariff_info['note']}\n\n"
        
        if 'annual_fee' in tariff_info:
            fees = tariff_info['annual_fee']
            output += "💰 **Årlig avgift:**\n"
            for zone, price in fees.items():
                if zone != 'currency' and zone != 'note':
                    output += f"  - {zone.replace('_', ' ').title()}: {price} {fees.get('currency', 'NOK')}/år\n"
            if 'note' in fees:
                output += f"\n*{fees['note']}*\n"
        
        return output
    
    # Regular parking info
    output = f"**{tariff_info.get('name', 'Parkering')}**\n\n"
    
    if 'zone' in tariff_info:
        output += f"📍 **Sone:** {tariff_info['zone']}\n\n"
    
    if 'avgiftstid' in tariff_info:
        output += f"🕐 **Avgiftstid:** {tariff_info['avgiftstid']}\n\n"
    
    if 'maks_tid' in tariff_info:
        output += f"⏱️ **Maks tid:** {tariff_info['maks_tid']}\n\n"
    
    # Pricing for regular cars
    if 'prices_bensin_diesel' in tariff_info:
        output += "💰 **Pris bensin/diesel/hybrid/ladbar hybrid:**\n"
        prices = tariff_info['prices_bensin_diesel']
        for duration, price in prices.items():
            if duration != 'currency':
                hours = duration.replace('h', ' time' if duration == '1h' else ' timer')
                output += f"  - {hours}: {price} {prices.get('currency', 'NOK')}\n"
        output += "\n"
    
    # Pricing for electric cars
    if 'prices_elbil' in tariff_info:
        output += "⚡ **Pris elbil:**\n"
        prices = tariff_info['prices_elbil']
        for duration, price in prices.items():
            if duration != 'currency':
                hours = duration.replace('h', ' time' if duration == '1h' else ' timer')
                output += f"  - {hours}: {price} {prices.get('currency', 'NOK')}\n"
        output += "\n"
    
    return output

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) in meters
    """
    # Convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    
    # Radius of earth in meters
    r = 6371000
    return c * r


def load_parking_data(filepath='parking_data.json'):
    """Load parking data from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract features into a DataFrame
        features = data.get('features', [])
        
        parking_list = []
        for feature in features:
            attrs = feature.get('attributes', {})
            geom = feature.get('geometry', {})
            
            # Get coordinates (handle different geometry types)
            if 'x' in geom and 'y' in geom:
                # Point geometry
                lon, lat = geom['x'], geom['y']
            elif 'paths' in geom and len(geom['paths']) > 0:
                # Polyline - use midpoint of first path (street parking segments)
                coords = geom['paths'][0]
                if len(coords) > 0:
                    # Calculate midpoint
                    mid_idx = len(coords) // 2
                    lon, lat = coords[mid_idx][0], coords[mid_idx][1]
                else:
                    continue
            elif 'rings' in geom and len(geom['rings']) > 0:
                # Polygon - use centroid
                coords = geom['rings'][0]
                lon = np.mean([c[0] for c in coords])
                lat = np.mean([c[1] for c in coords])
            else:
                continue
            
            parking_list.append({
                'lat': lat,
                'lon': lon,
                **attrs  # Include all attributes
            })
        
        return pd.DataFrame(parking_list)
    
    except FileNotFoundError:
        return None


def find_nearest_parking(user_lat, user_lon, df, n=10):
    """Find n nearest parking locations"""
    df = df.copy()
    df['distance'] = df.apply(
        lambda row: haversine_distance(user_lat, user_lon, row['lat'], row['lon']),
        axis=1
    )
    df = df.sort_values('distance')
    return df.head(n)


def create_map(user_location, parking_df, show_user=True, tariff_data=None):
    """Create a folium map with parking locations"""
    
    # Create map centered on user location or Oslo
    center_lat = user_location[0] if user_location else 59.9139
    center_lon = user_location[1] if user_location else 10.7522
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14,
        tiles='OpenStreetMap'
    )
    
    # Add legend
    legend_html = '''
    <div style="
        position: fixed; 
        bottom: 50px; 
        left: 50px; 
        width: 220px; 
        height: auto; 
        background-color: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(128, 128, 128, 0.3); 
        border-radius: 8px; 
        z-index: 9999; 
        font-size: 14px;
        padding: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        color: #000;
    ">
        <h4 style="margin: 0 0 10px 0; font-size: 16px; color: #000;">🅿️ Parking Legend</h4>
        <div style="margin: 5px 0;">
            <i class="fa fa-map-marker fa-2x" style="color: red;"></i>
            <span style="margin-left: 10px;">Your Location</span>
        </div>
        <div style="margin: 5px 0;">
            <i class="fa fa-circle" style="color: green; font-size: 18px;"></i>
            <span style="margin-left: 10px;">< 200m away</span>
        </div>
        <div style="margin: 5px 0;">
            <i class="fa fa-circle" style="color: orange; font-size: 18px;"></i>
            <span style="margin-left: 10px;">200-500m away</span>
        </div>
        <div style="margin: 5px 0;">
            <i class="fa fa-circle" style="color: blue; font-size: 18px;"></i>
            <span style="margin-left: 10px;">> 500m away</span>
        </div>
    </div>
    
    <style>
        @media (prefers-color-scheme: dark) {
            .leaflet-container {
                background: #1a1a1a !important;
            }
        }
    </style>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add user location
    if show_user and user_location:
        folium.Marker(
            user_location,
            popup="Your Location",
            icon=folium.Icon(color='red', icon='user', prefix='fa'),
            tooltip="You are here"
        ).add_to(m)
    
    # Add parking locations
    for idx, row in parking_df.iterrows():
        # Customize popup based on available fields
        popup_text = f"<b>🅿️ Street Parking</b><br>"
        
        # Oslo-specific field names (Norwegian)
        if 'GATENAVN' in row and pd.notna(row['GATENAVN']):
            popup_text += f"<b>{row['GATENAVN']}</b><br>"
        elif 'name' in row and pd.notna(row['name']):
            popup_text += f"<b>{row['name']}</b><br>"
        elif 'NAME' in row and pd.notna(row['NAME']):
            popup_text += f"<b>{row['NAME']}</b><br>"
        
        if 'distance' in row:
            popup_text += f"📍 {row['distance']:.0f}m away<br>"
        
        # Add capacity if available
        if 'KAPASITET' in row and pd.notna(row['KAPASITET']):
            popup_text += f"🚗 Capacity: {row['KAPASITET']} spaces<br>"
        
        # Add type if available
        if 'TYPE' in row and pd.notna(row['TYPE']):
            popup_text += f"📋 Type: {row['TYPE']}<br>"
        
        # Add resident zone if available
        if 'beboerparkeringssone' in row and pd.notna(row['beboerparkeringssone']):
            popup_text += f"🏘️ Resident Zone: {row['beboerparkeringssone']}<br>"
        
        # Add tariff information if available
        if tariff_data:
            takst_field = None
            if 'takstgruppe1' in row and pd.notna(row['takstgruppe1']):
                takst_field = row['takstgruppe1']
            elif 'takstgruppe1_code' in row and pd.notna(row['takstgruppe1_code']):
                takst_field = row['takstgruppe1_code']
            
            if takst_field:
                tariff_info = get_tariff_info(takst_field, tariff_data)
                if tariff_info:
                    popup_text += f"<br><b>💰 Takstgruppe {takst_field}</b><br>"
                    
                    if 'avgiftstid' in tariff_info:
                        popup_text += f"🕐 {tariff_info['avgiftstid']}<br>"
                    
                    if 'maks_tid' in tariff_info:
                        popup_text += f"⏱️ Maks: {tariff_info['maks_tid']}<br>"
                    
                    # Show first few prices
                    if 'prices_bensin_diesel' in tariff_info:
                        prices = tariff_info['prices_bensin_diesel']
                        popup_text += f"<br><b>Bensin/Diesel:</b><br>"
                        count = 0
                        for duration, price in prices.items():
                            if duration != 'currency' and count < 3:
                                popup_text += f"  {duration}: {price} kr<br>"
                                count += 1
                    
                    popup_text += f"<small>Click parking for full details</small><br>"
        
        # Add comments if available
        if 'KOMMENTAR' in row and pd.notna(row['KOMMENTAR']):
            popup_text += f"<br>ℹ️ {row['KOMMENTAR']}<br>"
        
        # Color by distance if available
        if 'distance' in row:
            if row['distance'] < 200:
                color = 'green'
            elif row['distance'] < 500:
                color = 'orange'
            else:
                color = 'blue'
        else:
            color = 'blue'
        
        # Get name for tooltip
        name = row.get('GATENAVN', row.get('name', row.get('NAME', 'Parking')))
        tooltip_text = f"{name}"
        if 'distance' in row:
            tooltip_text += f" - {row['distance']:.0f}m"
        
        folium.Marker(
            [row['lat'], row['lon']],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color=color, icon='parking', prefix='fa'),
            tooltip=tooltip_text
        ).add_to(m)
    
    return m


# Main app
st.title("🅿️ Oslo Zone D Grünerløkka Parking Finder")

# Load parking data
parking_df = load_parking_data()

if parking_df is None:
    st.error("""
    ⚠️ Parking data not found!
    
    Please run `download_oslo_parking.py` or `download_zone_d_final.py` first to download the parking data.
    """)
    st.stop()

st.success(f"✓ Loaded {len(parking_df)} parking locations")

# Load tariff data
tariff_data = load_tariff_data()
if tariff_data:
    st.success(f"✓ Loaded tariff information for {len([k for k in tariff_data.keys() if not k.startswith('_')])} tariff groups")
else:
    st.info("ℹ️ Tariff information not available. Add 'takstgruppe_lookup.json' to show pricing details.")

# Add info expander
with st.expander("ℹ️ About Oslo Parking Zones & Types"):
    st.markdown("""
    ### 🅿️ Parking Information
    
    **Resident Parking Zones (Beboerparkering)**
    - Oslo is divided into resident parking zones (A, B, C, D, E, F, etc.)
    - Each zone requires a specific parking permit
    - Zone D covers specific neighborhoods in Oslo
    
    **Color Coding on Map:**
    - 🔴 **Red marker** = Your current location
    - 🟢 **Green markers** = Very close (less than 200 meters)
    - 🟠 **Orange markers** = Close (200-500 meters)
    - 🔵 **Blue markers** = Moderate distance (more than 500 meters)
    
    **Tips:**
    - Green parking spots are within easy walking distance
    - Orange spots are a short walk away
    - Blue spots might require a longer walk
    - Click on map markers for detailed information
    """)

# Input method selection
st.subheader("📍 Find Your Location")

location_method = st.radio(
    "How would you like to set your location?",
    ["📍 Use my current location (GPS)", "✏️ Enter coordinates manually"],
    label_visibility="collapsed"
)

user_location = None

if location_method == "📍 Use my current location (GPS)":
    st.info("""
    **Click the button below to get your GPS location**
    
    Your browser will ask for location permission. Click "Allow" to continue.
    """)
    
    # Get geolocation
    location = streamlit_geolocation()
    
    if location and location.get("latitude") is not None:
        # Location successfully retrieved
        user_lat = location["latitude"]
        user_lon = location["longitude"]
        user_location = (user_lat, user_lon)
        
        st.success(f"✅ Location detected: {user_lat:.6f}, {user_lon:.6f}")
        
        # Show on small map for confirmation
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"📍 Your coordinates: {user_lat:.4f}, {user_lon:.4f}")
        with col2:
            if st.button("🔄 Refresh Location"):
                st.rerun()
    else:
        # Waiting for location or permission denied
        st.warning("""
        ⏳ Waiting for location...
        
        **Troubleshooting:**
        - Make sure you clicked "Allow" when prompted
        - Check that location services are enabled on your device
        - Some browsers block location access on non-HTTPS sites
        - Try refreshing the page
        
        **Or use manual entry below:**
        """)
        
        # Fallback to manual input
        st.subheader("✏️ Manual Location Entry")
        st.info("""
        **How to get your coordinates:**
        1. Open [Google Maps](https://www.google.com/maps)
        2. Right-click on your location
        3. Click "What's here?"
        4. Copy the coordinates (e.g., 59.9139, 10.7522)
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            user_lat = st.number_input("Latitude", value=59.9139, format="%.6f", help="Your latitude coordinate")
        with col2:
            user_lon = st.number_input("Longitude", value=10.7522, format="%.6f", help="Your longitude coordinate")
        
        user_location = (user_lat, user_lon)

else:
    # Manual input
    st.info("""
    **How to get your coordinates:**
    1. Open [Google Maps](https://www.google.com/maps)
    2. Right-click on your location
    3. Click "What's here?"
    4. Copy the coordinates (e.g., 59.9139, 10.7522)
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        user_lat = st.number_input("Latitude", value=59.9139, format="%.6f", help="Your latitude coordinate")
    with col2:
        user_lon = st.number_input("Longitude", value=10.7522, format="%.6f", help="Your longitude coordinate")
    
    user_location = (user_lat, user_lon)

# Number of results
n_results = st.slider("Number of nearby parking spots to show", 5, 20, 10)

if user_location:
    # Find nearest parking
    nearest = find_nearest_parking(user_location[0], user_location[1], parking_df, n_results)
    
    # Display results
    st.subheader(f"🎯 {len(nearest)} Nearest Parking Spots")
    
    # Add color legend
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(0, 102, 204, 0.1) 0%, rgba(0, 102, 204, 0.05) 100%);
        padding: 15px; 
        border-radius: 10px; 
        margin-bottom: 20px;
        border: 1px solid rgba(0, 102, 204, 0.2);
    ">
        <h4 style="margin: 0 0 10px 0;">🎨 Color Guide</h4>
        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <div>
                <span style="color: red; font-size: 20px;">●</span>
                <strong>Your Location</strong>
            </div>
            <div>
                <span style="color: green; font-size: 20px;">●</span>
                <strong>Very Close</strong> (&lt; 200m)
            </div>
            <div>
                <span style="color: orange; font-size: 20px;">●</span>
                <strong>Close</strong> (200-500m)
            </div>
            <div>
                <span style="color: blue; font-size: 20px;">●</span>
                <strong>Moderate</strong> (&gt; 500m)
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for map and list views
    tab1, tab2 = st.tabs(["🗺️ Map View", "📋 List View"])
    
    with tab1:
        # Show map
        m = create_map(user_location, nearest, tariff_data=tariff_data)
        st_folium(m, width=None, height=500)
    
    with tab2:
        # Show list of parking spots
        for idx, row in nearest.iterrows():
            distance_m = row['distance']
            distance_str = f"{distance_m:.0f}m" if distance_m < 1000 else f"{distance_m/1000:.1f}km"
            
            # Determine color based on distance
            if distance_m < 200:
                badge_color = "#28a745"  # Green
                distance_label = "Very Close"
            elif distance_m < 500:
                badge_color = "#fd7e14"  # Orange
                distance_label = "Close"
            else:
                badge_color = "#007bff"  # Blue
                distance_label = "Moderate"
            
            # Get name from Oslo-specific fields or fallbacks
            name = row.get('GATENAVN', row.get('name', row.get('NAME', 'Street Parking')))
            
            # Get additional details
            details = []
            if 'KAPASITET' in row and pd.notna(row['KAPASITET']):
                details.append(f"🚗 {row['KAPASITET']} spaces")
            if 'TYPE' in row and pd.notna(row['TYPE']):
                details.append(f"📋 {row['TYPE']}")
            if 'beboerparkeringssone' in row and pd.notna(row['beboerparkeringssone']):
                details.append(f"🏠 Zone {row['beboerparkeringssone']}")
            if 'KOMMENTAR' in row and pd.notna(row['KOMMENTAR']):
                details.append(f"ℹ️ {row['KOMMENTAR']}")
            
            details_str = ' • '.join(details) if details else 'Street parking'
            
            st.markdown(f"""
            <div class="parking-card">
                <h3 style="margin: 0 0 0.5rem 0; color: #0066cc;">
                    🅿️ {name}
                </h3>
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
                    <span style="
                        background-color: {badge_color}; 
                        color: white; 
                        padding: 4px 12px; 
                        border-radius: 12px; 
                        font-weight: bold;
                        font-size: 0.9rem;
                    ">
                        {distance_label}
                    </span>
                    <span style="font-size: 1.1rem; font-weight: bold;">
                        📍 {distance_str}
                    </span>
                </div>
                <p style="margin: 0; opacity: 0.8;">
                    {details_str}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Add pricing details if available
            if tariff_data:
                takst_field = None
                if 'takstgruppe1' in row and pd.notna(row['takstgruppe1']):
                    takst_field = row['takstgruppe1']
                elif 'takstgruppe1_code' in row and pd.notna(row['takstgruppe1_code']):
                    takst_field = row['takstgruppe1_code']
                
                if takst_field:
                    tariff_info = get_tariff_info(takst_field, tariff_data)
                    if tariff_info:
                        # Check if this is resident parking
                        is_resident = 'beboerparkeringssone' in row and pd.notna(row['beboerparkeringssone'])
                        
                        with st.expander(f"💰 Pricing Details (Takstgruppe {takst_field})"):
                            pricing_text = format_pricing_info(tariff_info, is_resident)
                            st.markdown(pricing_text)
            
            if st.button(f"Navigate to {name}", key=f"nav_{idx}"):
                # Open Google Maps navigation
                maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"
                st.markdown(f"[🗺️ Open in Google Maps]({maps_url})")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; opacity: 0.7; padding: 1rem;">
    Made with ❤️ for Oslo drivers | Data from Oslo Municipality
</div>
""", unsafe_allow_html=True)
