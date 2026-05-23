from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta

import database
import optimizer

app = FastAPI(title="Daily Commute Optimizer API")

# Ensure DB is initialized on startup
@app.on_event("startup")
def on_startup():
    database.init_db()

# Model schemas
class RouteRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    origin_name: str
    destination_name: str
    preferences: str = ""

class FrustrationLogRequest(BaseModel):
    log_text: str
    category: str
    severity: int
    location_name: str
    lat: float
    lng: float

# Helper: Call Gemini API using urllib
def generate_gemini_advice(origin: str, destination: str, preferences: str, routes: list, active_logs: list):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
        
    prompt = f"""
You are the AI routing advisor for the Daily Commute Optimizer (DCO) app.
The user wants to travel from {origin} to {destination}.
Their preferences/constraints are: "{preferences}"

Available real-world routes computed by the OSRM optimizer:
{json.dumps(routes, indent=2)}

Active community reports & frustration logs:
{json.dumps(active_logs, indent=2)}

Write a concise, personalized commuter advisory (2-3 sentences max).
- Recommend the best route based on their constraints.
- Mention if any active frustration logs (e.g. Silk Board Junction or Connaught Place congestion) overlap with their paths.
- Give a highly specific, human-like recommendation (e.g. "Leave 12 minutes early via Route B to bypass the construction delay").
- Keep it highly professional, premium, and friendly.
"""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            text = res_data['candidates'][0]['content']['parts'][0]['text']
            return text.strip()
    except Exception as e:
        print(f"Gemini API call failed: {e}. Falling back to rule-based generation.")
        return None

# Rule-based generator when no API key is available
def generate_fallback_advice(origin: str, destination: str, preferences: str, routes: list, active_logs: list):
    pref_lower = preferences.lower()
    
    # Identify key preferences
    has_knee_pain = any(w in pref_lower for w in ["knee", "pain", "hurt", "walk", "leg", "injury"])
    has_rain = any(w in pref_lower for w in ["rain", "wet", "water", "flood", "monsoon"])
    has_crowd_aversion = any(w in pref_lower for w in ["crowd", "rush", "train", "metro", "packed", "people"])
    has_speed_focus = any(w in pref_lower for w in ["fast", "quick", "hurry", "late", "speed"])
    
    # Identify impacting incidents
    impacted_locations = []
    for r in routes:
        if r.get("incidents"):
            for inc in r["incidents"]:
                impacted_locations.append(inc["location_name"])
                
    advices = []
    
    # Core recommendations based on preferences
    if has_knee_pain:
        advices.append(f"Due to your leg/knee discomfort, avoid active biking or walking. We suggest the driving route which drops you closest to {destination}.")
    elif has_rain:
        if impacted_locations:
            advices.append(f"Heavy rain conditions observed. Bypassing active delays near {', '.join(impacted_locations[:2])} by selecting the Eco/Metro corridor.")
        else:
            advices.append("Slick roads reported from the rain. We suggest a covered vehicle (Cab/Auto) and leaving 10 minutes early.")
    elif has_crowd_aversion:
        advices.append("To avoid crowd bottlenecks, skip public buses. The alternative driving link is 5 minutes slower but has low congestion.")
    elif has_speed_focus:
        advices.append("Since speed is key, take the Fastest Route. Watch out for peak hour bottlenecks at major flyover ramps.")
        
    # Standard fallback if no specific keywords match
    if not advices:
        if impacted_locations:
            advices.append(f"We've optimized your transit path to steer clear of active reports near {', '.join(impacted_locations[:2])}.")
        else:
            advices.append("Commute networks are flowing normally. The Low-Stress option provides the most relaxing route today.")
            
    # Add departure suggestion
    now = datetime.now()
    opt_leave = now + timedelta(minutes=15)
    advices.append(f"Optimal departure window: {opt_leave.strftime('%I:%M %p')}. Safe travels!")
    
    return " ".join(advices)

# API Endpoints
@app.get("/api/geocode")
def geocode_address(q: str):
    """
    Geocodes text address using Nominatim OpenStreetMap API.
    Restricts results to India ('in') for faster matches.
    """
    encoded_q = urllib.parse.quote(q)
    url = f"https://nominatim.openstreetmap.org/search?q={encoded_q}&format=json&limit=5&countrycodes=in"
    
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'DailyCommuteOptimizer/1.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            results = []
            for item in data:
                results.append({
                    "display_name": item["display_name"],
                    "lat": float(item["lat"]),
                    "lng": float(item["lon"])
                })
            return results
    except Exception as e:
        print(f"Geocoding failed for '{q}': {e}")
        raise HTTPException(status_code=500, detail="Geocoding service currently unavailable")

@app.post("/api/optimize-route")
def optimize_route(req: RouteRequest):
    routes = optimizer.optimize_real_routes(req.origin_lat, req.origin_lng, req.dest_lat, req.dest_lng)
    if not routes:
        raise HTTPException(status_code=404, detail="No routes could be computed")
        
    active_logs = database.get_frustration_logs(limit=10)
    
    # Try Gemini first, fallback to rule-based
    ai_advice = generate_gemini_advice(req.origin_name, req.destination_name, req.preferences, routes, active_logs)
    if not ai_advice:
        ai_advice = generate_fallback_advice(req.origin_name, req.destination_name, req.preferences, routes, active_logs)
        
    return {
        "origin": req.origin_name,
        "destination": req.destination_name,
        "origin_coords": {"lat": req.origin_lat, "lng": req.origin_lng},
        "destination_coords": {"lat": req.dest_lat, "lng": req.dest_lng},
        "routes": routes,
        "ai_advice": ai_advice
    }

@app.post("/api/frustration-logs")
def create_frustration_log(req: FrustrationLogRequest):
    database.add_frustration_log(
        req.log_text,
        req.category,
        req.severity,
        req.location_name,
        req.lat,
        req.lng
    )
    return {"status": "success", "message": "Frustration logged successfully"}

@app.get("/api/frustration-logs")
def get_frustration_logs():
    return database.get_frustration_logs()

@app.get("/api/departure-predictor")
def get_departure_predictor(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float):
    routes = optimizer.optimize_real_routes(origin_lat, origin_lng, dest_lat, dest_lng)
    if not routes:
        raise HTTPException(status_code=404, detail="No route found")
        
    fastest_time = routes[0]["time_minutes"]
    now = datetime.now()
    
    # Predict intervals
    slots = []
    
    # 1. Early slot
    time_1 = now - timedelta(minutes=15)
    slots.append({
        "time": time_1.strftime("%I:%M %p"),
        "label": "Early Bird",
        "estimated_duration": round(fastest_time * 0.85, 1),
        "status": "Green",
        "stress": "Very Calm"
    })
    
    # 2. Recommended slot
    time_2 = now + timedelta(minutes=10)
    slots.append({
        "time": time_2.strftime("%I:%M %p"),
        "label": "AI Recommended",
        "estimated_duration": round(fastest_time, 1),
        "status": "Green",
        "stress": "Calm"
    })
    
    # 3. Peak congestion slot
    time_3 = now + timedelta(minutes=30)
    slots.append({
        "time": time_3.strftime("%I:%M %p"),
        "label": "Peak Jam Window",
        "estimated_duration": round(fastest_time * 1.4, 1),
        "status": "Red",
        "stress": "High Frustration"
    })
    
    return {
        "slots": slots
    }

@app.get("/api/stats")
def get_stats():
    return database.get_commute_stats()

# Mount Static Files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(static_dir, "index.html"))
