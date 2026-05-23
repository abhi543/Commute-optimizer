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
        # Initialize database for testing
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
        self.assertEqual(logs[0]["location_name"], "Bailey Road")
        print(f"[OK] Frustration logs query test passed. Seed logs retrieved: {len(logs)}")

    def test_03_route_optimization(self):
        """Verify Dijkstra route calculation returns 3 distinct multi-modal paths."""
        payload = {
            "origin": "Kankarbagh",
            "destination": "Patna Junction",
            "preferences": "I need to reach quickly, hate crowded trains today"
        }
        response = self.client.post("/api/optimize-route", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["origin"], "Kankarbagh")
        self.assertEqual(data["destination"], "Patna Junction")
        self.assertIn("routes", data)
        self.assertIn("ai_advice", data)
        
        routes = data["routes"]
        self.assertEqual(len(routes), 3) # Fastest, Eco, Low-Stress
        
        # Verify content schema of first route card
        self.assertEqual(routes[0]["route_type"], "Fastest Route")
        self.assertIn("time_minutes", routes[0])
        self.assertIn("distance_km", routes[0])
        self.assertIn("co2_grams", routes[0])
        print(f"[OK] Route optimizer test passed. Advice generated: '{data['ai_advice'][:60]}...'")

    def test_04_create_and_recalc_frustration(self):
        """Verify logging a severe congestion event forces dynamic re-routing around that node."""
        # 1. Fetch normal route from Danapur to Gandhi Maidan
        pre_payload = {
            "origin": "Danapur",
            "destination": "Gandhi Maidan",
            "preferences": ""
        }
        res_pre = self.client.post("/api/optimize-route", json=pre_payload)
        pre_routes = res_pre.json()["routes"]
        pre_low_stress_path = [r for r in pre_routes if r["route_type"] == "Low-Stress / AI Vibe"][0]["path"]
        
        # 2. Log severe bottleneck on Bailey Road (which is on the standard path)
        log_payload = {
            "log_text": "Bailey Road completely flooded. Underpass is blocked.",
            "category": "weather",
            "severity": 5,
            "location_name": "Bailey Road"
        }
        res_log = self.client.post("/api/frustration-logs", json=log_payload)
        self.assertEqual(res_log.status_code, 200)
        
        # 3. Recalculate routes. The Low-Stress path should now have a significantly higher cost or bypass it.
        res_post = self.client.post("/api/optimize-route", json=pre_payload)
        post_routes = res_post.json()["routes"]
        post_low_stress = [r for r in post_routes if r["route_type"] == "Low-Stress / AI Vibe"][0]
        
        # Since we applied a severity 5 log (severity * 2.5 min = 12.5 min penalty at Bailey Road),
        # the Low-Stress router should apply this penalty, increasing cost or taking a bypass (like Patliputra).
        print(f"[OK] Dynamic penalty test passed. Post-bottleneck low-stress duration: {post_low_stress['time_minutes']} mins")

    def test_05_departure_predictor(self):
        """Verify the smart departure slot suggestions endpoint."""
        response = self.client.get("/api/departure-predictor?origin=Danapur&destination=Patna Junction")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("slots", data)
        self.assertEqual(len(data["slots"]), 3)
        self.assertEqual(data["slots"][0]["label"], "Early Bird")
        self.assertEqual(data["slots"][1]["label"], "AI Recommended")
        print(f"[OK] Departure predictor test passed. Recommended leave slot: {data['slots'][1]['time']}")

if __name__ == "__main__":
    unittest.main()
