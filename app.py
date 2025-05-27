# app.py — Application Streamlit pour lancer l'optimisation avec distances calculées
import streamlit as st
import pandas as pd
from optimisation import generate_tournees
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def compute_distance_matrix(df, average_speed_kmph=50):
    points = [(row['Latitude'], row['Longitude']) for _, row in df.iterrows()]
    matrix = []
    for from_point in points:
        row = []
        for to_point in points:
            dist_km = haversine(*from_point, *to_point)
            duration_min = int((dist_km / average_speed_kmph) * 60)
            row.append(duration_min)
        matrix.append(row)
    return matrix

def parse_excel(file):
    df = pd.read_excel(file)
    if 'Depot' not in df['ID externe'].values:
        st.error("Le fichier Excel doit contenir au moins une ligne avec ID externe = 'Depot'")
        st.stop()

    df = df.reset_index(drop=True)
    depot_index = df.index[df['ID externe'] == 'Depot'].tolist()[0]
    distance_matrix = compute_distance_matrix(df)

    locations = {}
    demands = []
    for i, row in df.iterrows():
        locations[row['ID externe']] = i
        demands.append(row['Palettes'])

    return {
        'locations': locations,
        'distance_matrix': distance_matrix,
        'demands': demands,
        'vehicle_capacity': 33,
        'nb_chauffeurs': st.session_state.get('nb_chauffeurs', 3),
        'depot_index': depot_index
    }

def main():
    st.title("Optimisation des tournées de livraison")
    uploaded_file = st.file_uploader("Charge ton fichier Excel", type="xlsx")

    if uploaded_file:
        with st.spinner("Analyse du fichier et préparation de l’optimisation..."):
            data = parse_excel(uploaded_file)
            result = generate_tournees(data)

        for chauffeur in result:
            st.subheader(f"Chauffeur {chauffeur['chauffeur']} – Total journée : {chauffeur['total_time']} min")
            for route in chauffeur['routes']:
                st.markdown(f"**Tournée {route['vehicle_id']}** – {route['time']} min")
                noms = list(data['locations'].keys())
                codes = list(data['locations'].values())
                path = [noms[codes.index(p[0])] for p in route['path']]
                st.code(" -> ".join(path))

if __name__ == "__main__":
    main()
