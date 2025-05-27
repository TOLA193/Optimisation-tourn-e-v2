
import streamlit as st
import pandas as pd
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np

st.set_page_config(page_title="Optimisation Tournées V2", layout="wide")

st.title("📦 Optimisation de tournées de livraison")
st.markdown("Importez un fichier Excel avec vos livraisons du jour pour générer des tournées optimisées.")

uploaded_file = st.file_uploader("📁 Déposez votre fichier Excel", type=["xlsx"])

def haversine(lat1, lon1, lat2, lon2):
    from math import radians, cos, sin, asin, sqrt
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    return round(R * c * 1.09)  # km to minutes approx

def build_distance_matrix(locations):
    size = len(locations)
    matrix = []
    for i in range(size):
        row = []
        for j in range(size):
            if i == j:
                row.append(0)
            else:
                row.append(haversine(*locations[i], *locations[j]))
        matrix.append(row)
    return matrix

def run_optimization(df):
    df = df.dropna(subset=["latitude", "longitude", "Palettes"])
    df["Palettes"] = df["Palettes"].astype(int)
    depot_coord = (50.4845, 4.49575)  # Heppignies par défaut pour exemple

    locations = [depot_coord] + list(zip(df["latitude"], df["longitude"]))
    distance_matrix = build_distance_matrix(locations)
    demands = [0] + df["Palettes"].tolist()
    vehicle_capacities = [33] * 14
    num_vehicles = len(vehicle_capacities)
    depot_index = 0

    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), num_vehicles, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        return distance_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        return demands[manager.IndexToNode(from_index)]
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        vehicle_capacities,
        True,
        'Capacity')

    time_dimension_name = 'Time'
    routing.AddDimension(
        transit_callback_index,
        0,
        12 * 60,
        False,
        time_dimension_name)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    solution = routing.SolveWithParameters(search_parameters)

    if not solution:
        return None, None

    results = []
    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        route = []
        load = 0
        total_time = 0
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            if node_index != depot_index:
                magasin = df.iloc[node_index - 1]
                route.append(magasin["ID externe"])
                load += magasin["Palettes"]
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            total_time += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
        if route:
            results.append({"Camion": f"Camion {vehicle_id+1}", "Magasins livrés": route, "Palettes": load, "Durée estimée (min)": total_time})

    df_result = pd.DataFrame(results)
    return df_result, solution

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("Fichier chargé avec succès ✅")
        st.dataframe(df.head(20), use_container_width=True)

        if st.button("🚀 Lancer l'optimisation"):
            with st.spinner("Optimisation en cours..."):
                result_df, solution = run_optimization(df)
                if result_df is not None:
                    st.success("Optimisation terminée ✅")
                    st.dataframe(result_df, use_container_width=True)
                    st.download_button("📥 Télécharger le résumé", result_df.to_csv(index=False).encode("utf-8"), "résumé_tournées.csv", "text/csv")
                else:
                    st.error("❌ Aucune solution trouvée. Vérifiez les données.")
    except Exception as e:
        st.error(f"Erreur lors du chargement : {e}")
