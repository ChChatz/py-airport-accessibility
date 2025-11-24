"""
Name:       Christos Chatziioannou
Data:       Airports Around the World (airport-codes.csv)

Description:
This program explores airport density and accessibility around the world.
It lets the user filter airports by continent, country, and type, shows
airport counts and charts, and includes a feature where the user chooses
a world city from a dropdown. The app finds the three closest airports and
also shows all airports within a selected radius around that city.
"""

import math
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import pydeck as pdk

# -----------------------------
# World cities (name -> (lat, lon)) for airport finder functionality
# -----------------------------
WORLD_CITIES = {
    "New York, USA": (40.7128, -74.0060),
    "Boston, USA": (42.3601, -71.0589),
    "Los Angeles, USA": (34.0522, -118.2437),
    "Chicago, USA": (41.8781, -87.6298),
    "London, UK": (51.5074, -0.1278),
    "Paris, France": (48.8566, 2.3522),
    "Berlin, Germany": (52.5200, 13.4050),
    "Athens, Greece": (37.9838, 23.7275),
    "Tokyo, Japan": (35.6895, 139.6917),
    "Sydney, Australia": (-33.8688, 151.2093),
    "Rio de Janeiro, Brazil": (-22.9068, -43.1729),
    "Johannesburg, South Africa": (-26.2041, 28.0473),
    "Toronto, Canada": (43.6532, -79.3832),
    "Mexico City, Mexico": (19.4326, -99.1332),
    "Dubai, UAE": (25.2048, 55.2708),
    "Singapore": (1.3521, 103.8198),
    "Hong Kong": (22.3193, 114.1694),
}

# ----------------------------
# Helper functions
# ----------------------------

# #[FUNC2P]
# Formula to calculate distance between two points on earth, using the radius of the earth in kilometers
# source: Stack Overflow https://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
def haversine_km(lat1, lon1, lat2, lon2, radius_km=6371.0):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius_km * 2 * math.asin(math.sqrt(a))

# #[FUNCRETURN2]
def get_country_min_max(counts_df):
    if counts_df.empty:
        return None, None
    max_row = counts_df.iloc[0]
    min_row = counts_df.iloc[-1]
    max_info = (max_row["country_name"], max_row["airport_count"])
    min_info = (min_row["country_name"], min_row["airport_count"])
    return max_info, min_info

# #[LAMBDA]
def add_large_flag(df):
    df["is_large"] = df["type"].apply(lambda t: 1 if "large" in str(t).lower() else 0)
    return df

# #[LISTCOMP]
def get_sorted_types(df):
    return sorted([t for t in df["type"].dropna().unique()])

# #[FUNCCALL2] + #[ITERLOOP]
def compute_distances_to_pin(df, pin_lat, pin_lon):
    distances = []
    for idx, row in df.iterrows():
        d = haversine_km(pin_lat, pin_lon, row["latitude_deg"], row["longitude_deg"])
        distances.append((idx, d))
    return distances

def find_closest_airports(df, pin_lat, pin_lon, k=3):
    dist_list = compute_distances_to_pin(df, pin_lat, pin_lon)
    dist_list.sort(key=lambda x: x[1])
    closest_idx = [idx for idx, d in dist_list[:k]]
    closest_df = df.loc[closest_idx].copy()
    # #[COLUMNS]
    closest_df["distance_km"] = [d for idx, d in dist_list[:k]]
    return closest_df

# #[DICTMETHOD]
def get_continent_full_name(code):
    mapping = {
        "AF": "Africa",
        "AN": "Antarctica",
        "AS": "Asia",
        "EU": "Europe",
        "NA": "North America",
        "OC": "Oceania",
        "SA": "South America",
    }
    return mapping.get(code, code)

# ----------------------------
# Load data
# ----------------------------
def load_airports():
    df = pd.read_csv("airport-codes.csv")

    # If coordinates need to be split
    if "latitude_deg" not in df.columns or "longitude_deg" not in df.columns:
        coords = df["coordinates"].str.split(",", expand=True)
        df["longitude_deg"] = pd.to_numeric(coords[0].str.strip(), errors="coerce")
        df["latitude_deg"] = pd.to_numeric(coords[1].str.strip(), errors="coerce")

    df = df[
        [
            "name",
            "type",
            "continent",
            "iso_country",
            "municipality",
            "latitude_deg",
            "longitude_deg",
        ]
    ].dropna(subset=["latitude_deg", "longitude_deg"])

    # Add country names
    iso_df = pd.read_csv("wikipedia-iso-country-codes.csv")
    iso_df.columns = iso_df.columns.str.lower().str.strip()

    # Use known column names
    iso2_col = "alpha-2 code"
    name_col = "english short name lower case"

    iso_map = dict(zip(iso_df[iso2_col].str.upper(), iso_df[name_col]))

    df["country_name"] = df["iso_country"].str.upper().map(lambda c: iso_map.get(c, c))
    df = add_large_flag(df)
    return df

# --------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Airport Density and Accessibility", layout="wide")
    st.title("Airport Density and Accessibility")

    airports = load_airports()

    st.write(
        "Explore airport density worldwide, filter by continent/country/type, "
        "and select a world city to find nearby airports and accessibility."
    )

    # ---------------- Sidebar Filters ----------------
    st.sidebar.header("Filters")

    # #[ST3] (overall page layout uses sidebar + tabs)
    # Full continent names
    codes = sorted(airports["continent"].dropna().unique())
    code_to_name = {c: get_continent_full_name(c) for c in codes}
    name_to_code = {v: k for k, v in code_to_name.items()}

    cont_display = ["All continents"] + list(code_to_name.values())
    # #[ST1]
    selected_cont = st.sidebar.selectbox("Continent", cont_display)

    # #[FILTER1]
    if selected_cont == "All continents":
        selected_cont_code = None
        df_cont = airports
    else:
        selected_cont_code = name_to_code[selected_cont]
        df_cont = airports[airports["continent"] == selected_cont_code]

    # Country filter
    country_list = sorted(df_cont["country_name"].dropna().unique())
    country_display = ["All countries"] + country_list
    selected_country = st.sidebar.selectbox("Country", country_display)

    # #[FILTER2]
    if selected_country == "All countries":
        df_country = df_cont
    else:
        df_country = df_cont[df_cont["country_name"] == selected_country]

    # Type filter
    types = get_sorted_types(df_country)
    selected_types = st.sidebar.multiselect("Airport type", types, default=types)

    df_filtered = df_country[df_country["type"].isin(selected_types)]

    # ---------------- Tabs ----------------
    tab1, tab2 = st.tabs(["Density Overview", "Closest Airports"])

    # ---------- TAB 1 ----------
    with tab1:
        st.header("Airport Density Overview")
        if df_filtered.empty:
            st.warning("No airports match these filters.")
            return

        counts = df_filtered.groupby("country_name")["name"].count().reset_index(name="airport_count")
        counts = counts.sort_values("airport_count", ascending=False)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Counts by Country")
            st.dataframe(counts)
            # #[MAXMIN] and #[FUNCRETURN2]
            max_info, min_info = get_country_min_max(counts)
            if max_info and min_info:
                max_country, max_count = max_info
                min_country, min_count = min_info
                st.write(f"Highest: {max_country} ({max_count})")
                st.write(f"Lowest: {min_country} ({min_count})")

        with col2:
            st.subheader("Top 15 Countries")
            top15 = counts.head(15)
            # #[CHART1]
            fig, ax = plt.subplots()
            ax.bar(top15["country_name"], top15["airport_count"], color="skyblue")
            plt.xticks(rotation=45)
            st.pyplot(fig)

        st.subheader("Map of Airports")
        # #[MAP]
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_filtered,
            get_position="[longitude_deg, latitude_deg]",
            get_radius=3000,
            get_fill_color=[0, 120, 255],
            pickable=True,
        )
        view = pdk.ViewState(
            latitude=float(df_filtered["latitude_deg"].mean()),
            longitude=float(df_filtered["longitude_deg"].mean()),
            zoom=2 if selected_cont_code is None else 3,
        )
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view))

    # ---------- TAB 2 ----------
    with tab2:
        st.header("Closest Airports to a World City")

        if df_filtered.empty:
            st.warning("No airports available.")
            return

        # #[ST2]
        city_name = st.selectbox("Choose a city", list(WORLD_CITIES.keys()))
        pin_lat, pin_lon = WORLD_CITIES[city_name]

        st.write(f"Selected city: **{city_name}**")
        st.write(f"Latitude: {pin_lat}, Longitude: {pin_lon}")

        closest_df = find_closest_airports(df_filtered, pin_lat, pin_lon, k=3)

        st.subheader("Closest 3 Airports")
        st.dataframe(
            closest_df[
                ["name", "type", "country_name", "municipality", "distance_km"]
            ].round({"distance_km": 2})
        )

        # Radius selection
        distances = compute_distances_to_pin(df_filtered, pin_lat, pin_lon)
        dist_values = [d for idx, d in distances]
        max_dist = max(dist_values) if dist_values else 1000

        # #[ST2] (slider widget)
        radius = st.slider("Radius (km)", 100, int(max_dist), 500, step=50)

        dist_map = {idx: d for idx, d in distances}
        df_with_dist = df_filtered.copy()
        df_with_dist["distance_km"] = df_with_dist.index.map(dist_map)

        df_radius = df_with_dist[df_with_dist["distance_km"] <= radius]

        st.subheader(f"Airports within {radius} km")
        st.write(f"Count: {len(df_radius)}")

        if len(df_radius) > 0:
            st.dataframe(
                df_radius[
                    ["name", "type", "country_name", "municipality", "distance_km"]
                ].sort_values("distance_km").round({"distance_km": 2})
            )

            # Pie Chart (CHART2)
            st.subheader("Airport Type Breakdown")
            # #[CHART2]
            type_counts = df_radius["type"].value_counts()
            fig2, ax2 = plt.subplots()
            ax2.pie(type_counts.values, labels=type_counts.index, autopct="%1.1f%%")
            st.pyplot(fig2)

            # Map
            st.subheader("Map of City and Airports in Radius")

            pin_df = pd.DataFrame({
                "name": ["Selected City"],
                "latitude_deg": [pin_lat],
                "longitude_deg": [pin_lon]
            })

            city_layer = pdk.Layer(
                "ScatterplotLayer",
                data=pin_df,
                get_position="[longitude_deg, latitude_deg]",
                get_radius=9000,
                get_fill_color=[255, 0, 0],
            )

            airport_layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_radius,
                get_position="[longitude_deg, latitude_deg]",
                get_radius=6000,
                get_fill_color=[0, 0, 255],
            )

            view2 = pdk.ViewState(latitude=pin_lat, longitude=pin_lon, zoom=4)
            st.pydeck_chart(pdk.Deck(layers=[city_layer, airport_layer], initial_view_state=view2))


if __name__ == "__main__":
    main()
