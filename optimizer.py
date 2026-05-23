import heapq
from database import get_frustration_logs

# Define landmarks and their coordinates (x, y on a 1000x600 canvas)
LANDMARKS = {
    "Danapur": {"lat": 25.6300, "lng": 85.0400, "x": 100, "y": 300},
    "Bailey Road": {"lat": 25.6110, "lng": 85.0850, "x": 300, "y": 300},
    "Boring Road Crossing": {"lat": 25.6180, "lng": 85.1150, "x": 450, "y": 150},
    "Patliputra Colony": {"lat": 25.6320, "lng": 85.1050, "x": 350, "y": 100},
    "Dak Bungalow Crossing": {"lat": 25.6080, "lng": 85.1380, "x": 600, "y": 250},
    "Gandhi Maidan": {"lat": 25.6200, "lng": 85.1480, "x": 700, "y": 150},
    "Patna Junction": {"lat": 25.6020, "lng": 85.1320, "x": 600, "y": 450},
    "Rajendra Nagar": {"lat": 25.5980, "lng": 85.1650, "x": 800, "y": 400},
    "Kankarbagh": {"lat": 25.5900, "lng": 85.1550, "x": 850, "y": 500},
    "Patna City": {"lat": 25.6050, "lng": 85.2200, "x": 950, "y": 300}
}

# Define network graph connections with distances (in km) and mode availability
# Mode support flags: 'C' (Car/Auto), 'B' (Bus), 'M' (Metro), 'W' (Walk/Cycle)
GRAPH_EDGES = [
    # Danapur connections
    ("Danapur", "Bailey Road", 4.5, "CBMW"),
    ("Danapur", "Patliputra Colony", 6.5, "CW"),
    
    # Bailey Road connections
    ("Bailey Road", "Boring Road Crossing", 3.0, "CBW"),
    ("Bailey Road", "Patna Junction", 4.0, "CBMW"),
    ("Bailey Road", "Dak Bungalow Crossing", 4.8, "CBW"),
    
    # Boring Road Crossing connections
    ("Boring Road Crossing", "Patliputra Colony", 2.0, "CBW"),
    ("Boring Road Crossing", "Dak Bungalow Crossing", 2.5, "CBW"),
    ("Boring Road Crossing", "Gandhi Maidan", 3.5, "CW"),
    
    # Patliputra Colony connections
    ("Patliputra Colony", "Gandhi Maidan", 4.0, "CW"),
    
    # Dak Bungalow Crossing connections
    ("Dak Bungalow Crossing", "Gandhi Maidan", 1.5, "CBMW"),
    ("Dak Bungalow Crossing", "Patna Junction", 1.2, "CBW"),
    ("Dak Bungalow Crossing", "Rajendra Nagar", 3.0, "CBW"),
    
    # Gandhi Maidan connections
    ("Gandhi Maidan", "Rajendra Nagar", 2.5, "CBW"),
    ("Gandhi Maidan", "Patna City", 6.0, "CBW"),
    
    # Patna Junction connections
    ("Patna Junction", "Kankarbagh", 2.5, "CBMW"),
    
    # Rajendra Nagar connections
    ("Rajendra Nagar", "Kankarbagh", 2.0, "CBW"),
    ("Rajendra Nagar", "Patna City", 4.5, "CW"),
    
    # Kankarbagh connections
    ("Kankarbagh", "Patna City", 6.5, "CW")
]

# Average speed in km/h for modes
SPEEDS = {
    "car": 25,     # slow urban traffic
    "bus": 15,     # transit bus stops
    "metro": 45,   # fast and independent of traffic
    "bike": 18,    # active cycling
    "walk": 5      # slow pedestrian
}

# Carbon emission in g CO2 per km
EMISSIONS = {
    "car": 120,
    "bus": 40,
    "metro": 10,
    "bike": 0,
    "walk": 0
}

def build_adjacency_list():
    adj = {node: [] for node in LANDMARKS}
    for u, v, dist, modes in GRAPH_EDGES:
        adj[u].append({"to": v, "dist": dist, "modes": modes})
        adj[v].append({"to": u, "dist": dist, "modes": modes})
    return adj

ADJACENCY_LIST = build_adjacency_list()

def calculate_dijkstra(start, end, allowed_modes, penalties):
    """
    Computes shortest path from start to end using allowed modes.
    penalties: dict mapping node_name -> delay in minutes.
    """
    if start not in LANDMARKS or end not in LANDMARKS:
        return None
        
    # priority queue: (total_time_minutes, current_node, path_nodes, path_modes, total_dist, total_co2)
    pq = [(0, start, [start], [], 0.0, 0.0)]
    visited = {}
    
    while pq:
        time_min, curr, path, path_modes, dist, co2 = heapq.heappop(pq)
        
        if curr == end:
            return {
                "path": path,
                "modes": path_modes,
                "time_minutes": round(time_min, 1),
                "distance_km": round(dist, 1),
                "co2_grams": round(co2, 1)
            }
            
        if curr in visited and visited[curr] <= time_min:
            continue
            
        visited[curr] = time_min
        
        for edge in ADJACENCY_LIST[curr]:
            neighbor = edge["to"]
            edge_dist = edge["dist"]
            edge_modes = edge["modes"]
            
            # Find the best available mode for this edge among allowed modes
            best_mode = None
            best_mode_time = float('inf')
            
            for mode in allowed_modes:
                # Map mode character
                mode_char = ""
                if mode == "car": mode_char = "C"
                elif mode == "bus": mode_char = "B"
                elif mode == "metro": mode_char = "M"
                elif mode in ["bike", "walk"]: mode_char = "W"
                
                if mode_char in edge_modes:
                    # Special speeds handling: bike vs walk
                    speed = SPEEDS[mode]
                    travel_time = (edge_dist / speed) * 60  # in minutes
                    
                    # Apply penalty if it's car/bus transit
                    if mode in ["car", "bus"]:
                        node_penalty = penalties.get(neighbor, 0.0) + penalties.get(curr, 0.0)
                        travel_time += node_penalty
                        
                    if travel_time < best_mode_time:
                        best_mode_time = travel_time
                        best_mode = mode
            
            if best_mode is not None:
                new_time = time_min + best_mode_time
                new_dist = dist + edge_dist
                new_co2 = co2 + (edge_dist * EMISSIONS[best_mode])
                heapq.heappush(pq, (new_time, neighbor, path + [neighbor], path_modes + [best_mode], new_dist, new_co2))
                
    return None

def get_active_penalties():
    """
    Computes penalties based on recent frustration logs.
    """
    logs = get_frustration_logs(limit=15)
    penalties = {}
    
    for log in logs:
        loc = log["location_name"]
        severity = log["severity"]
        # Max penalty of 15 minutes per severity grade for heavy bottlenecking
        # Penalty decreases over time (for simplicity, we assume all DB entries are active)
        current_penalty = severity * 2.5  # in minutes
        penalties[loc] = penalties.get(loc, 0.0) + current_penalty
        
    return penalties

def compute_all_routes(start, end):
    penalties = get_active_penalties()
    
    # 1. Fastest Route: Can use any mode, ignore environmental focus, optimize purely for base speed.
    # Typically selects metro where available, car/cab where not.
    fastest = calculate_dijkstra(start, end, ["car", "metro", "bus", "bike", "walk"], {})
    if fastest:
        fastest["route_type"] = "Fastest Route"
        fastest["description"] = "Prioritizes speed via motorways & main metro transit corridors."
        fastest["vibe"] = "Fast & Direct"
        fastest["frustration_index"] = calculate_frustration_index(fastest["path"], penalties)
        
    # 2. Eco & Active Route: Walk, bike, metro only. No car/cab.
    eco = calculate_dijkstra(start, end, ["metro", "bike", "walk"], {})
    if eco:
        eco["route_type"] = "Eco & Active Mode"
        eco["description"] = "Zero carbon emission transit combining cycling, walking, and metro links."
        eco["vibe"] = "Healthy & Sustainable"
        eco["frustration_index"] = calculate_frustration_index(eco["path"], penalties) * 0.5  # inherently less traffic stress
        
    # 3. Low-Stress Route: Employs full penalties from frustration logs, avoiding congested junctions.
    low_stress = calculate_dijkstra(start, end, ["car", "metro", "bus", "bike", "walk"], penalties)
    if low_stress:
        # Check if it's different from fastest. If it bypassed a node, mark it clearly.
        low_stress["route_type"] = "Low-Stress / AI Vibe"
        low_stress["description"] = "Bypasses high-congestion spots and recent waterlogging/metro construction sites."
        low_stress["vibe"] = "Smooth & Calm"
        low_stress["frustration_index"] = calculate_frustration_index(low_stress["path"], penalties)
        
        # If low-stress is identical to fastest but fastest has high frustration, we adjust the output
        if low_stress["path"] == fastest["path"] and fastest["frustration_index"] > 5:
            low_stress["description"] = "No viable bypass path available, but speed-regulated to avoid peak bottlenecks."

    routes = []
    if fastest: routes.append(fastest)
    if eco: routes.append(eco)
    if low_stress: routes.append(low_stress)
    
    return routes

def calculate_frustration_index(path, penalties):
    """
    Computes a frustration rating (1-10) for a route based on penalties at nodes.
    """
    total_penalty = sum(penalties.get(node, 0.0) for node in path)
    if total_penalty == 0:
        return 1.2
    return round(min(10.0, 1.0 + (total_penalty / 3.0)), 1)
