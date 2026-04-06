import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math
import pydeck as pdk

# --- API Constants ---
BASE_URL = "https://environment.data.gov.uk/flood-monitoring"

# --- Helper Functions ---
@st.cache_data(ttl=3600)
def get_all_stations():
    url = f"{BASE_URL}/id/stations?_limit=10000"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get('items', [])
    except Exception as e:
        st.error(f"Error fetching stations: {e}")
        return []

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c

@st.cache_data(ttl=3600)
def geocode_place(place_name):
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "nosamaj_EA_API_Comparer_App/1.0"}
    params = {"q": place_name, "format": "json", "limit": 1}
    try:
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon']), data[0]['display_name']
    except Exception as e:
        return None
    return None

def search_stations(query, search_type="Text", radius_km=10):
    if not query:
        return []
    all_stations = get_all_stations()
    
    results = []
    if search_type == "Location":
        coord_data = geocode_place(query)
        if coord_data:
            lat, lon, display_name = coord_data
            st.sidebar.caption(f"📍 Found: {display_name}")
            for s in all_stations:
                s_lat = s.get('lat')
                s_lon = s.get('long')
                
                # EA API might occasionally return lists instead of single floats
                if isinstance(s_lat, list):
                    s_lat = s_lat[0] if s_lat else None
                if isinstance(s_lon, list):
                    s_lon = s_lon[0] if s_lon else None
                    
                if s_lat is not None and s_lon is not None:
                    try:
                        s_lat = float(s_lat)
                        s_lon = float(s_lon)
                        dist = haversine(lat, lon, s_lat, s_lon)
                        if dist <= radius_km:
                            s['_dist'] = dist
                            results.append(s)
                    except (ValueError, TypeError):
                        pass
            results.sort(key=lambda x: x.get('_dist', 0))
        else:
            st.sidebar.error("Could not find that location.")
    else:
        query = query.lower()
        for s in all_stations:
            label = str(s.get('label', '')).lower()
            town = str(s.get('town', '')).lower()
            river = str(s.get('riverName', '')).lower()
            station_ref = str(s.get('stationReference', '')).lower()
            grid_ref = str(s.get('gridReference', '')).lower()
            notation = str(s.get('notation', '')).lower()
            
            if query in label or query in town or query in river \
               or query in station_ref or query in grid_ref or query in notation:
                results.append(s)
            
    return results

@st.cache_data(ttl=3600)
def get_station_measures(station_uri):
    if station_uri.startswith("http://"):
        station_uri = station_uri.replace("http://", "https://")
    url = f"{station_uri}/measures"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get('items', [])
    except Exception as e:
        st.error(f"Error fetching measures for station: {e}")
        return []

@st.cache_data(ttl=3600)
def get_measure_readings(measure_uri, start_date, end_date):
    if measure_uri.startswith("http://"):
        measure_uri = measure_uri.replace("http://", "https://")
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    url = f"{measure_uri}/readings?startdate={start_str}&enddate={end_str}&_sorted"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get('items', [])
    except Exception as e:
        st.error(f"Error fetching readings: {e}")
        return []


# --- main UI ---
st.set_page_config(page_title="EA API Comparer", layout="wide")
st.title("Environment Agency API Comparer")

# Initialize session state for selected series
if 'selected_series' not in st.session_state:
    st.session_state.selected_series = []

st.sidebar.header("Add a Series")

# 1. Search Station
search_mode = st.sidebar.radio("Search Mode", ["Text (Name, River, Ref)", "Location (Town, Postcode)"])
search_query = st.sidebar.text_input("Search")
radius = 10
if search_mode == "Location (Town, Postcode)":
    radius = st.sidebar.slider("Radius (km)", 1, 50, 10)

if search_query:
    search_type = "Location" if search_mode == "Location (Town, Postcode)" else "Text"
    stations = search_stations(search_query, search_type, radius)
    if stations:
        station_options = {}
        for s in stations:
            title = s.get('label', 'Unnamed')
            ref = s.get('stationReference', s.get('notation', ''))
            loc = s.get('town', s.get('gridReference', 'Unknown location'))
            river = s.get('riverName', 'Unknown river')
            
            display_name = f"{title} [{ref}] - {loc} ({river})"
            if '_dist' in s:
                display_name += f" ({s['_dist']:.1f} km)"
                
            station_options[display_name] = s
            
        selected_station_label = st.sidebar.selectbox("Select Station", options=list(station_options.keys()))
        selected_station = station_options[selected_station_label]
        
        # 2. Select Measure
        measures = get_station_measures(selected_station['@id'])
        if measures:
            measure_options = {f"{m.get('parameterName')} ({m.get('unitName')}) - {m.get('qualifier')}": m for m in measures}
            selected_measure_label = st.sidebar.selectbox("Select Measure", options=list(measure_options.keys()))
            selected_measure = measure_options[selected_measure_label]

            if st.sidebar.button("Add to Comparison"):
                s_lat = selected_station.get('lat')
                s_lon = selected_station.get('long')
                if isinstance(s_lat, list): s_lat = s_lat[0] if s_lat else None
                if isinstance(s_lon, list): s_lon = s_lon[0] if s_lon else None
                try:
                    s_lat = float(s_lat) if s_lat is not None else None
                    s_lon = float(s_lon) if s_lon is not None else None
                except:
                    s_lat, s_lon = None, None
                    
                series_info = {
                    'station_name': selected_station.get('label'),
                    'measure_name': f"{selected_measure.get('parameterName')} - {selected_measure.get('qualifier')}",
                    'unit': selected_measure.get('unitName'),
                    'measure_uri': selected_measure['@id'],
                    'id': f"{selected_station.get('notation')}_{selected_measure.get('notation')}",
                    'lat': s_lat,
                    'lon': s_lon
                }
                
                # Check for duplicates
                if not any(s['id'] == series_info['id'] for s in st.session_state.selected_series):
                    st.session_state.selected_series.append(series_info)
                    st.sidebar.success("Added!")
                else:
                    st.sidebar.warning("Already in comparison.")
        else:
            st.sidebar.warning("No measures found for this station.")
    else:
        st.sidebar.warning("No stations found.")

# Display selected series
if st.session_state.selected_series:
    st.subheader("Selected Series")
    
    # Render selected series list with remove buttons
    cols = st.columns(len(st.session_state.selected_series))
    for idx, series in enumerate(list(st.session_state.selected_series)):
        with cols[idx]:
            st.info(f"**{series['station_name']}**\n\n{series['measure_name']} ({series['unit']})")
            if st.button("Remove", key=f"remove_{series['id']}"):
                st.session_state.selected_series.remove(series)
                st.rerun()

    # Time frame selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime.today() - timedelta(days=7))
    with col2:
        end_date = st.date_input("End Date", value=datetime.today())
    
    if st.button("Plot Comparison"):
        if start_date > end_date:
            st.error("Start date must be before end date.")
        else:
            with st.spinner("Fetching data and generating plot..."):
                axes_groups = {}
                yaxis_count = 1
                
                has_rainfall = any("rain" in s['measure_name'].lower() or s['unit'] == "mm" for s in st.session_state.selected_series)
                has_other = any(not("rain" in s['measure_name'].lower() or s['unit'] == "mm") for s in st.session_state.selected_series)
                
                domain_other = [0.0, 0.70] if (has_rainfall and has_other) else [0.0, 1.0]
                domain_rain  = [0.75, 1.0] if (has_rainfall and has_other) else [0.0, 1.0]
                
                fig = go.Figure()
                
                for idx, series in enumerate(st.session_state.selected_series):
                    readings = get_measure_readings(series['measure_uri'], start_date, end_date)
                    if not readings:
                        st.warning(f"No readings found for {series['station_name']} - {series['measure_name']}")
                        continue
                    
                    df = pd.DataFrame(readings)
                    df['dateTime'] = pd.to_datetime(df['dateTime'])
                    df = df.sort_values('dateTime')
                    
                    unit = series['unit']
                    is_rainfall = "rain" in series['measure_name'].lower() or unit == "mm"
                    
                    # Calculate order of magnitude
                    max_abs_val = df['value'].abs().max()
                    magnitude = int(np.floor(np.log10(max_abs_val))) if max_abs_val > 0 and not pd.isna(max_abs_val) else 0
                    
                    # Group by both unit and magnitude (and reverse state)
                    axis_group_key = f"{unit}_mag{magnitude}_{'rev' if is_rainfall else 'norm'}"
                    
                    if axis_group_key not in axes_groups:
                        axes_groups[axis_group_key] = {
                            "unit": unit,
                            "magnitude": magnitude,
                            "is_reversed": is_rainfall,
                            "yaxis": f"y{yaxis_count}"
                        }
                        yaxis_count += 1
                    
                    yaxis_ref = axes_groups[axis_group_key]["yaxis"]
                    
                    if is_rainfall:
                        fig.add_trace(go.Bar(
                            x=df['dateTime'], 
                            y=df['value'], 
                            name=f"{series['station_name']} - {series['measure_name']} ({unit})",
                            yaxis=yaxis_ref
                        ))
                    else:
                        fig.add_trace(go.Scatter(
                            x=df['dateTime'], 
                            y=df['value'], 
                            mode='lines',
                            name=f"{series['station_name']} - {series['measure_name']} ({unit})",
                            yaxis=yaxis_ref
                        ))
                
            # Layout configuration for multiple y-axes
            layout_args = {
                'title': "Measure Comparison",
                'xaxis': {'title': "Date/Time"}
            }
            
            primary_other = None
            primary_rain = None
            other_offset_count = 0
            rain_offset_count = 0
            
            for axis_group_key, axis_info in axes_groups.items():
                unit = axis_info["unit"]
                yaxis_ref = axis_info["yaxis"]
                is_rainfall = axis_info["is_reversed"]
                
                axis_config = {
                    'title': f"Value ({unit})",
                    'side': 'left' if yaxis_ref == 'y1' else 'right',
                    'domain': domain_rain if is_rainfall else domain_other
                }
                
                if is_rainfall:
                    if not primary_rain:
                        primary_rain = yaxis_ref.replace('y', 'y') if yaxis_ref == 'y1' else yaxis_ref
                    else:
                        axis_config['overlaying'] = 'y' if primary_rain == 'y1' else primary_rain
                        rain_offset_count += 1
                        axis_config['position'] = 1 - (rain_offset_count * 0.1)
                else:
                    if not primary_other:
                        primary_other = yaxis_ref.replace('y', 'y') if yaxis_ref == 'y1' else yaxis_ref
                    else:
                        axis_config['overlaying'] = 'y' if primary_other == 'y1' else primary_other
                        other_offset_count += 1
                        axis_config['position'] = 1 - (other_offset_count * 0.1)
                
                if is_rainfall:
                    axis_config['autorange'] = 'reversed'
                
                axis_key = 'yaxis' if yaxis_ref == 'y1' else f'yaxis{yaxis_ref[1:]}'
                layout_args[axis_key] = axis_config
                
            fig.update_layout(
                **layout_args,
                legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.5)'),
                hovermode='x unified',
                barmode='group'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show map
            st.subheader("Selected Stations Map")
            
            selected_coords = []
            for series in st.session_state.selected_series:
                if series.get('lat') is not None and series.get('lon') is not None:
                    selected_coords.append({"lat": series['lat'], "lon": series['lon'], "name": series['station_name']})
                    
            unselected_coords = []
            search_is_location = False
            search_lat = None
            search_lon = None
            search_radius_m = 0
            
            if search_query:
                s_type = "Location" if search_mode == "Location (Town, Postcode)" else "Text"
                if 'stations' in locals() and stations:
                    for stn in stations:
                        s_lat, s_lon = stn.get('lat'), stn.get('long')
                        if isinstance(s_lat, list): s_lat = s_lat[0] if s_lat else None
                        if isinstance(s_lon, list): s_lon = s_lon[0] if s_lon else None
                        if s_lat is not None and s_lon is not None:
                            try:
                                s_lat, s_lon = float(s_lat), float(s_lon)
                                unselected_coords.append({"lat": s_lat, "lon": s_lon, "name": stn.get('label', 'Unnamed')})
                            except:
                                pass
                                
                if s_type == "Location":
                    coord = geocode_place(search_query) 
                    if coord:
                        search_lat, search_lon, _ = coord
                        search_is_location = True
                        search_radius_m = radius * 1000

            layers = []
            
            if search_is_location:
                layers.append(
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=[{"lat": search_lat, "lon": search_lon}],
                        get_position="[lon, lat]",
                        get_radius=search_radius_m,
                        get_fill_color=[100, 150, 250, 40],
                        pickable=False
                    )
                )
            
            if unselected_coords:
                layers.append(
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=unselected_coords,
                        get_position="[lon, lat]",
                        get_radius=300,
                        get_fill_color=[150, 150, 150, 150],
                        pickable=True
                    )
                )
                
            if selected_coords:
                layers.append(
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=selected_coords,
                        get_position="[lon, lat]",
                        get_radius=600,
                        get_fill_color=[250, 50, 50, 255],
                        pickable=True
                    )
                )

            if selected_coords:
                vp_lat = np.mean([c['lat'] for c in selected_coords])
                vp_lon = np.mean([c['lon'] for c in selected_coords])
                zoom = 10
            elif search_is_location:
                vp_lat = search_lat
                vp_lon = search_lon
                zoom = 10
            elif unselected_coords:
                vp_lat = np.mean([c['lat'] for c in unselected_coords])
                vp_lon = np.mean([c['lon'] for c in unselected_coords])
                zoom = 8
            else:
                vp_lat = 52.5
                vp_lon = -1.5
                zoom = 6
                
            st.pydeck_chart(pdk.Deck(
                map_style=None,
                initial_view_state=pdk.ViewState(
                    latitude=vp_lat,
                    longitude=vp_lon,
                    zoom=zoom,
                    pitch=0,
                ),
                layers=layers,
                tooltip={"text": "{name}"}
            ))
else:
    st.info("Search and add stations from the sidebar to compare them.")
