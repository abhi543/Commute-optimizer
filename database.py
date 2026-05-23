import sqlite3
import os
from datetime import datetime, timedelta
import random

if os.environ.get("VERCEL"):
    DB_FILE = "/tmp/dco.db"
else:
    DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dco.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create frustration logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS frustration_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        log_text TEXT NOT NULL,
        category TEXT NOT NULL,
        severity INTEGER NOT NULL,
        location_name TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL
    )
    """)
    
    # Create commute history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS commute_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        origin TEXT NOT NULL,
        destination TEXT NOT NULL,
        mode TEXT NOT NULL,
        duration INTEGER NOT NULL,
        satisfaction_score INTEGER NOT NULL
    )
    """)
    
    # Seed default data if empty
    cursor.execute("SELECT COUNT(*) FROM frustration_logs")
    if cursor.fetchone()[0] == 0:
        seed_data(cursor)
        
    conn.commit()
    conn.close()

def seed_data(cursor):
    # Fictional / Patna-inspired landmarks map coordinates (x, y on a 1000x600 canvas)
    # Latitude and longitude mapped to screen coordinates roughly
    landmarks = {
        "Danapur": {"lat": 25.6300, "lng": 85.0400, "description": "Residential hub on the west side"},
        "Bailey Road": {"lat": 25.6110, "lng": 85.0850, "description": "Major arterial highway, prone to metro construction jams"},
        "Boring Road Crossing": {"lat": 25.6180, "lng": 85.1150, "description": "Highly congested commercial crossing"},
        "Patliputra Colony": {"lat": 25.6320, "lng": 85.1050, "description": "Upscale residential area, tree-lined streets"},
        "Dak Bungalow Crossing": {"lat": 25.6080, "lng": 85.1380, "description": "Heart of the city, extremely busy crossing"},
        "Gandhi Maidan": {"lat": 25.6200, "lng": 85.1480, "description": "Central public park, traffic-heavy perimeter"},
        "Patna Junction": {"lat": 25.6020, "lng": 85.1320, "description": "Main railway station and metro transit exchange"},
        "Rajendra Nagar": {"lat": 25.5980, "lng": 85.1650, "description": "Major student coaching and residential area"},
        "Kankarbagh": {"lat": 25.5900, "lng": 85.1550, "description": "Massive residential colony, prone to waterlogging"},
        "Patna City": {"lat": 25.6050, "lng": 85.2200, "description": "Historical old town, extremely narrow congested streets"}
    }
    
    # Insert some initial frustration logs
    now = datetime.now()
    initial_logs = [
        (
            (now - timedelta(hours=2)).isoformat(),
            "Waterlogging near Bailey Road flyover ramp due to morning drizzle. Traffic crawling at 5 km/h.",
            "weather",
            4,
            "Bailey Road",
            25.6110,
            85.0850
        ),
        (
            (now - timedelta(hours=6)).isoformat(),
            "Metro construction barricading has blocked two lanes near Dak Bungalow crossing. Avoid.",
            "construction",
            5,
            "Dak Bungalow Crossing",
            25.6080,
            85.1380
        ),
        (
            (now - timedelta(days=1)).isoformat(),
            "Auto-rickshaws blocking the left lane entirely at Patna Junction exit. Chaos during rush hour.",
            "traffic",
            3,
            "Patna Junction",
            25.6020,
            85.1320
        ),
        (
            (now - timedelta(days=2)).isoformat(),
            "Severe parking shortage at Boring Road Crossing market. Spent 20 minutes circling block.",
            "parking",
            4,
            "Boring Road Crossing",
            25.6180,
            85.1150
        ),
        (
            (now - timedelta(days=2, hours=4)).isoformat(),
            "High passenger crowding inside the line-1 public transit buses at Kankarbagh terminal.",
            "crowding",
            3,
            "Kankarbagh",
            25.5900,
            85.1550
        )
    ]
    
    cursor.executemany("""
    INSERT INTO frustration_logs (timestamp, log_text, category, severity, location_name, lat, lng)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, initial_logs)
    
    # Seed some commute history
    modes = ["metro", "cab", "bike", "walking", "auto"]
    history_entries = []
    
    # Generate 15 historical commutes over the past week
    for i in range(15):
        date_offset = random.randint(1, 7)
        hour = random.choice([9, 10, 17, 18])  # commute times
        commute_time = now - timedelta(days=date_offset)
        commute_time = commute_time.replace(hour=hour, minute=random.randint(0, 59))
        
        orig = random.choice(["Danapur", "Bailey Road", "Patliputra Colony", "Kankarbagh"])
        dest = random.choice(["Dak Bungalow Crossing", "Gandhi Maidan", "Rajendra Nagar", "Patna City"])
        if orig == dest:
            continue
            
        mode = random.choice(modes)
        duration = random.randint(15, 65)
        # Satisfaction is generally lower if duration is higher
        sat = max(1, min(5, 6 - int(duration / 15) + random.choice([-1, 0, 1])))
        
        history_entries.append((
            commute_time.isoformat(),
            orig,
            dest,
            mode,
            duration,
            sat
        ))
        
    cursor.executemany("""
    INSERT INTO commute_history (timestamp, origin, destination, mode, duration, satisfaction_score)
    VALUES (?, ?, ?, ?, ?, ?)
    """, history_entries)

# Database helper functions
def add_frustration_log(log_text, category, severity, location_name, lat, lng):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO frustration_logs (timestamp, log_text, category, severity, location_name, lat, lng)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), log_text, category, severity, location_name, lat, lng))
    conn.commit()
    conn.close()

def get_frustration_logs(limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM frustration_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_commute_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate average satisfaction, total routes, total estimated time saved
    cursor.execute("SELECT COUNT(*) FROM commute_history")
    total_commutes = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(satisfaction_score) FROM commute_history")
    avg_sat = cursor.fetchone()[0] or 4.0
    
    cursor.execute("SELECT AVG(duration) FROM commute_history")
    avg_duration = cursor.fetchone()[0] or 35.0
    
    conn.close()
    
    # Fictional estimated savings based on optimizer usage
    # 22 minutes saved per commute on average for the user
    time_saved = total_commutes * 18 
    
    return {
        "total_commutes": total_commutes,
        "avg_satisfaction": round(avg_sat, 1),
        "avg_duration_minutes": round(avg_duration, 1),
        "total_time_saved_minutes": time_saved,
        "stress_reduction_percentage": round(30 + (avg_sat * 5), 1)
    }
