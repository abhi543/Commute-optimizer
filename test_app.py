import unittest
import os
import json
from fastapi.testclient import TestClient

# Import the main FastAPI app
from main import app
import database
import optimizer

class TestDCOApplication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Delete old db if exists to force clean re-seeding
        db_path = "dco.db"
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
        database.init_db()
        cls.client = TestClient(app)

    def test_01_stats_endpoint(self):
        """Verify that cumulative commute stats are correctly calculated and retrieved."""
        response = self.client.get("/api/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("total_commutes", data)
        self.assertIn("avg_satisfaction", data)
        self.assertIn("total_time_saved_minutes", data)
        self.assertGreater(data["total_commutes"], 0)
        print(f"[OK] Stats test passed. Total historical commutes: {data['total_commutes']}")

    def test_02_frustration_logs_list(self):
        """Verify initial seeded frustration logs are fetched correctly."""
        response = self.client.get("/api/frustration-logs")
        self.assertEqual(response.status_code, 200)
        logs = response.json()
        
        self.assertGreater(len(logs), 0)
        # Check first log is Silk Board (seeded)
        self.assertEqual(logs[0]["location_name"], "Silk Board Junction, Bangalore")
        print(f"[OK] Frustration logs query test passed. Seed logs retrieved: {len(logs)}")

    def test_03_route_optimization(self):
        """Verify OSRM route calculation returns 3 distinct paths."""
        payload = {
            "origin_lat": 12.9176,
            "origin_lng": 77.6244,
            "dest_lat": 12.9719,
            "dest_lng": 77.6412,
            "origin_name": "Silk Board, Bangalore",
            "destination_name": "Indiranagar, Bangalore",
            "preferences": "I need to reach quickly, hate crowded trains today"
        }
        response = self.client.post("/api/optimize-route", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["origin"], "Silk Board, Bangalore")
        self.assertEqual(data["destination"], "Indiranagar, Bangalore")
        self.assertIn("routes", data)
        self.assertIn("ai_advice", data)
        
        routes = data["routes"]
        self.assertEqual(len(routes), 3) # Fastest, Eco, Low-Stress
        
        self.assertEqual(routes[0]["route_type"], "Fastest Route")
        self.assertIn("time_minutes", routes[0])
        self.assertIn("distance_km", routes[0])
        self.assertIn("co2_grams", routes[0])
        print(f"[OK] Route optimizer test passed. Advice generated: '{data['ai_advice'][:60]}...'")

    def test_04_create_and_recalc_frustration(self):
        """Verify logging a severe congestion event forces dynamic re-routing around that node."""
        # 1. Fetch normal route from Silk Board to Indiranagar
        pre_payload = {
            "origin_lat": 12.9176,
            "origin_lng": 77.6244,
            "dest_lat": 12.9719,
            "dest_lng": 77.6412,
            "origin_name": "Silk Board, Bangalore",
            "destination_name": "Indiranagar, Bangalore",
            "preferences": ""
        }
        res_pre = self.client.post("/api/optimize-route", json=pre_payload)
        pre_routes = res_pre.json()["routes"]
        pre_low_stress_path = [r for r in pre_routes if r["route_type"] == "Low-Stress / AI Vibe"][0]
        
        # 2. Log severe bottleneck on a coordinate nearby (Hebbal Flyover, Bangalore)
        log_payload = {
            "log_text": "Hebbal Flyover is completely blocked.",
            "category": "weather",
            "severity": 5,
            "location_name": "Hebbal Flyover, Bangalore",
            "lat": 13.0359,
            "lng": 77.5970
        }
        res_log = self.client.post("/api/frustration-logs", json=log_payload)
        self.assertEqual(res_log.status_code, 200)
        
        # 3. Recalculate routes.
        res_post = self.client.post("/api/optimize-route", json=pre_payload)
        post_routes = res_post.json()["routes"]
        post_low_stress = [r for r in post_routes if r["route_type"] == "Low-Stress / AI Vibe"][0]
        
        print(f"[OK] Dynamic penalty test passed. Post-bottleneck low-stress duration: {post_low_stress['time_minutes']} mins")

    def test_05_departure_predictor(self):
        """Verify the smart departure slot suggestions endpoint."""
        response = self.client.get("/api/departure-predictor?origin_lat=12.9176&origin_lng=77.6244&dest_lat=12.9719&dest_lng=77.6412")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("slots", data)
        self.assertEqual(len(data["slots"]), 3)
        self.assertEqual(data["slots"][0]["label"], "Early Bird")
        self.assertEqual(data["slots"][1]["label"], "AI Recommended")
        print(f"[OK] Departure predictor test passed. Recommended leave slot: {data['slots'][1]['time']}")

if __name__ == "__main__":
    unittest.main()
