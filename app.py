import streamlit as st
import pandas as pd
import requests
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# ----------- 1) Title -----------
st.set_page_config(page_title="RoadSense AI", layout="wide")
st.title("RoadSense AI — Toronto Road Events")
st.markdown("Mobile-friendly interactive map with event clustering and date filter.")

# ----------- 2) Fetch and Clean Data -----------
@st.cache_data(ttl=3600)
def fetch_clean_511():
    url = "https://511on.ca/api/v2/get/event"
    params = {"format": "json", "lang": "en"}
    response = requests.get(url, params=params)
    df = pd.DataFrame(response.json())
    df.columns = [c.lower() for c in df.columns]

    # Convert datetime columns
    for col in ["starttime", "endtime"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Convert coordinates
    for coord in ["latitude", "longitude"]:
        if coord in df.columns:
            df[coord] = pd.to_numeric(df[coord], errors="coerce")

    df = df[df["starttime"].notnull() & df["latitude"].notnull() & df["longitude"].notnull()]

    # Event types
    df["is_collision"] = df["eventtype"].str.contains("Collision|Accident", case=False, na=False)
    df["is_stopped_vehicle"] = df["eventsubtype"].str.contains("Stopped|Stalled|Disabled", case=False, na=False)
    df["is_lane_closed"] = df["eventsubtype"].str.contains("Lane", case=False, na=False)

    def event_color(row):
        if row["is_collision"]: return "red"
        elif row["is_stopped_vehicle"]: return "orange"
        elif row["is_lane_closed"]: return "blue"
        else: return "green"
    df["color"] = df.apply(event_color, axis=1)

    return df

# Fetch data
_df = fetch_clean_511()

# ----------- 3) Filter by Date -----------
min_date = _df['starttime'].min().date()
max_date = _df['starttime'].max().date()
selected_date = st.date_input("Select Date", min_value=min_date, max_value=max_date, value=min_date)
df = _df[_df['starttime'].dt.date == selected_date]

# ----------- 4) Create Map with MarkerCluster -----------
toronto_coords = [43.651070, -79.347015]
m = folium.Map(location=toronto_coords, zoom_start=11, tiles='OpenStreetMap')
marker_cluster = MarkerCluster().add_to(m)

for _, row in df.iterrows():
    folium.CircleMarker(
        location=[row['latitude'], row['longitude']],
        radius=8,
        color='black',
        fill=True,
        fill_color=row['color'],
        fill_opacity=0.9,
        weight=1.5,
        popup=f"Event: {row['eventtype']}\nSubtype: {row['eventsubtype']}\nStartTime: {row['starttime']}"
    ).add_to(marker_cluster)

# Legend
legend_html = """
 <div style="position: fixed; 
     bottom: 50px; left: 50px; width: 150px; height: 120px; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:white; padding: 10px;">
     <b>Event Colors</b><br>
     <i style="color:red">■ Collision</i><br>
     <i style="color:orange">■ Stalled Vehicle</i><br>
     <i style="color:blue">■ Lane Closure</i>
 </div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# ----------- 5) Display Map -----------
st_folium(m, width=700, height=500)
