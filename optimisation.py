from ortools.constraint_solver import pywrapcp, routing_enums_pb2

def generate_tournees(data, max_minutes_per_tournee=720, nb_tournees_par_chauffeur=2, time_limit=30):
    total_vehicules = data['nb_chauffeurs'] * nb_tournees_par_chauffeur

    manager = pywrapcp.RoutingIndexManager(
        len(data['distance_matrix']),
        total_vehicules,
        [data['depot_index']] * total_vehicules,
        [data['depot_index']] * total_vehicules
    )
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        [data['vehicle_capacity']] * total_vehicules,
        True,
        'Capacity')

    routing.AddDimension(
        transit_callback_index,
        0,
        max_minutes_per_tournee,
        True,
        'Time')

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = time_limit

    solution = routing.SolveWithParameters(search_parameters)

    result = []
    if solution:
        chauffeurs = {}
        for vehicle_id in range(total_vehicules):
            index = routing.Start(vehicle_id)
            if routing.IsEnd(solution.Value(routing.NextVar(index))):
                continue
            route = []
            load = 0
            route_time = 0
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                load += data['demands'][node_index]
                route.append((node_index, load))
                prev_index = index
                index = solution.Value(routing.NextVar(index))
                route_time += routing.GetArcCostForVehicle(prev_index, index, vehicle_id)
            node_index = manager.IndexToNode(index)
            route.append((node_index, load))

            chauffeur_id = vehicle_id // nb_tournees_par_chauffeur
            if chauffeur_id not in chauffeurs:
                chauffeurs[chauffeur_id] = {'routes': [], 'total_time': 0}
            chauffeurs[chauffeur_id]['routes'].append({'vehicle_id': vehicle_id + 1, 'time': route_time, 'path': route})
            chauffeurs[chauffeur_id]['total_time'] += route_time

        for chauffeur_id, info in chauffeurs.items():
            result.append({
                'chauffeur': chauffeur_id + 1,
                'total_time': info['total_time'],
                'routes': info['routes']
            })
    return result
