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
    # Seed frustration logs across major Indian cities
    now = datetime.now()
    initial_logs = [
        (
            (now - timedelta(hours=2)).isoformat(),
            "Severe traffic bottleneck at Silk Board Junction. Vehicles crawling towards HSR Layout.",
            "traffic",
            5,
            "Silk Board Junction, Bangalore",
            12.9176,
            77.6244
        ),
        (
            (now - timedelta(hours=5)).isoformat(),
            "Waterlogging under Hebbal Flyover due to sudden downpour. Left lane blocked.",
            "weather",
            4,
            "Hebbal Flyover, Bangalore",
            13.0359,
            77.5970
        ),
        (
            (now - timedelta(hours=8)).isoformat(),
            "High passenger crowding inside Indiranagar Metro station. Long queues at gates.",
            "crowding",
            4,
            "Indiranagar Metro, Bangalore",
            12.9719,
            77.6412
        ),
        (
            (now - timedelta(days=1)).isoformat(),
            "Metro construction blocks two lanes on Bailey Road near the flyover ramp.",
            "construction",
            4,
            "Bailey Road, Patna",
            25.6110,
            85.0850
        ),
        (
            (now - timedelta(days=1, hours=4)).isoformat(),
            "Outer Circle near Connaught Place is heavily congested. No parking spaces available.",
            "parking",
            4,
            "Connaught Place, Delhi",
            28.6304,
            77.2177
        )
    ]
    
    cursor.executemany("""
    INSERT INTO frustration_logs (timestamp, log_text, category, severity, location_name, lat, lng)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, initial_logs)
    
    # Seed commute history with generic city names
    history_entries = [
        ((now - timedelta(days=1)).isoformat(), "Indiranagar", "Koramangala", "bike", 25, 4),
        ((now - timedelta(days=2)).isoformat(), "Majestic", "Whitefield", "metro", 40, 5),
        ((now - timedelta(days=2)).isoformat(), "Dwarka", "Connaught Place", "metro", 45, 5),
        ((now - timedelta(days=3)).isoformat(), "Danapur", "Patna Junction", "auto", 35, 3),
        ((now - timedelta(days=3)).isoformat(), "HSR Layout", "Electronic City", "cab", 50, 2),
        ((now - timedelta(days=4)).isoformat(), "Noida Sec 62", "Rajiv Chowk", "metro", 55, 4),
        ((now - timedelta(days=4)).isoformat(), "Koramangala", "MG Road", "bike", 20, 5)
    ]
    
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
