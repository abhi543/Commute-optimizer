from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import json
import urllib.request
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
    origin: str
    destination: str
    preferences: str = ""

class FrustrationLogRequest(BaseModel):
    log_text: str
    category: str
    severity: int
    location_name: str

# Helper: Call Gemini API using urllib (standard library, zero dependencies)
def generate_gemini_advice(origin: str, destination: str, preferences: str, routes: list, active_logs: list):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
        
    prompt = f"""
You are the AI routing advisor for the Daily Commute Optimizer (DCO) app.
The user wants to travel from {origin} to {destination}.
Their preferences/constraints are: "{preferences}"

Available routes computed by the optimizer:
{json.dumps(routes, indent=2)}

Active community reports & frustration logs:
{json.dumps(active_logs, indent=2)}

Write a concise, personalized commuter advisory (2-3 sentences max).
- Recommend the best route based on their constraints (e.g., if they have knee pain, avoid stairs/walking; if they hate traffic, suggest metro or low-stress route).
- Mention any active disruptions (like construction or waterlogging) that they will bypass.
- Give a highly specific, human-like recommendation (e.g. "Leave 12 minutes early to beat the Kankarbagh gridlock").
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
    
    # Match any active frustration locations
    impacted_locations = []
    for log in active_logs:
        loc = log["location_name"]
        for route in routes:
            if loc in route["path"]:
                impacted_locations.append((loc, log["category"], log["severity"]))
                break
                
    advices = []
    
    # Core recommendations based on preferences
    if has_knee_pain:
        advices.append(f"To protect your knee, we recommend taking a direct Cab or Auto. Avoid the Active/Eco route which involves significant walking segments.")
    elif has_rain:
        flooded = [loc for loc, cat, sev in impacted_locations if cat in ["weather", "traffic"]]
        if flooded:
            advices.append(f"Due to the wet conditions and reported waterlogging at {', '.join(flooded[:2])}, we recommend riding the Metro which is completely weatherproof.")
        else:
            advices.append("It's rainy today! We advise using covered transit modes (Metro or Cab) over two-wheelers, and leaving 10 minutes early due to slick roads.")
    elif has_crowd_aversion:
        advices.append("Since you want to avoid crowds, skip the Metro during this window. The Low-Stress Cab route using residential links is 8 minutes slower but significantly calmer.")
    elif has_speed_focus:
        advices.append("Since you are in a rush, we recommend the Fastest Route using the Metro corridor. It is immune to the traffic bottlenecks at major crossings.")
        
    # Standard fallback if no specific keywords match
    if not advices:
        # Check if we bypassed anything in the low-stress route
        congested = [loc for loc, cat, sev in impacted_locations if sev >= 4]
        if congested:
            advices.append(f"We've optimized your route to bypass active bottlenecks at {', '.join(congested[:2])}.")
        else:
            advices.append(f"Standard traffic conditions observed. The Low-Stress path is recommended for a balanced, calm ride today.")
            
    # Add departure suggestion
    now = datetime.now()
    opt_leave = now + timedelta(minutes=15)
    advices.append(f"Optimal departure window: {opt_leave.strftime('%I:%M %p')} to avoid peak congestion. Have a safe trip!")
    
    return " ".join(advices)

# API Endpoints
@app.post("/api/optimize-route")
def optimize_route(req: RouteRequest):
    if req.origin not in optimizer.LANDMARKS or req.destination not in optimizer.LANDMARKS:
        raise HTTPException(status_code=400, detail="Invalid origin or destination landmark")
        
    routes = optimizer.compute_all_routes(req.origin, req.destination)
    active_logs = database.get_frustration_logs(limit=10)
    
    # Try Gemini first, fallback to rule-based
    ai_advice = generate_gemini_advice(req.origin, req.destination, req.preferences, routes, active_logs)
    if not ai_advice:
        ai_advice = generate_fallback_advice(req.origin, req.destination, req.preferences, routes, active_logs)
        
    return {
        "origin": req.origin,
        "destination": req.destination,
        "origin_coords": optimizer.LANDMARKS[req.origin],
        "destination_coords": optimizer.LANDMARKS[req.destination],
        "routes": routes,
        "ai_advice": ai_advice
    }

@app.post("/api/frustration-logs")
def create_frustration_log(req: FrustrationLogRequest):
    if req.location_name not in optimizer.LANDMARKS:
        raise HTTPException(status_code=400, detail="Invalid landmark name")
        
    coords = optimizer.LANDMARKS[req.location_name]
    database.add_frustration_log(
        req.log_text,
        req.category,
        req.severity,
        req.location_name,
        coords["lat"],
        coords["lng"]
    )
    return {"status": "success", "message": "Frustration logged successfully"}

@app.get("/api/frustration-logs")
def get_frustration_logs():
    return database.get_frustration_logs()

@app.get("/api/departure-predictor")
def get_departure_predictor(origin: str, destination: str):
    if origin not in optimizer.LANDMARKS or destination not in optimizer.LANDMARKS:
        raise HTTPException(status_code=400, detail="Invalid landmarks")
        
    routes = optimizer.compute_all_routes(origin, destination)
    if not routes:
        raise HTTPException(status_code=404, detail="No route found")
        
    fastest_time = routes[0]["time_minutes"]
    now = datetime.now()
    
    # Predict intervals
    slots = []
    
    # 1. Early slot (30 mins before)
    time_1 = now - timedelta(minutes=15)
    slots.append({
        "time": time_1.strftime("%I:%M %p"),
        "label": "Early Bird",
        "estimated_duration": round(fastest_time * 0.85, 1),
        "status": "Green",
        "stress": "Very Calm"
    })
    
    # 2. Recommended slot (current)
    time_2 = now + timedelta(minutes=10)
    slots.append({
        "time": time_2.strftime("%I:%M %p"),
        "label": "AI Recommended",
        "estimated_duration": round(fastest_time, 1),
        "status": "Green",
        "stress": "Calm"
    })
    
    # 3. Peak congestion slot (25 mins later)
    time_3 = now + timedelta(minutes=30)
    slots.append({
        "time": time_3.strftime("%I:%M %p"),
        "label": "Peak Jam Window",
        "estimated_duration": round(fastest_time * 1.4, 1),
        "status": "Red",
        "stress": "High Frustration"
    })
    
    return {
        "origin": origin,
        "destination": destination,
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
