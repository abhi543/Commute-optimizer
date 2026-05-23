# Daily Commute Optimizer (DCO)

Daily Commute Optimizer (DCO) is a context-aware, AI-powered mobility planning application designed to minimize travel stress and optimize route choices. DCO goes beyond standard navigation apps by processing natural language preferences (e.g., "my knee hurts today"), integrating real-time weather and traffic disruption reports, and applying a personalization loop driven by user-reported frustration logs.

## 🚀 Key Features

*   **AI Vibe Router (NLP Input)**: Express constraints or preferences in plain words (e.g., "avoid Bailey Road, it's raining, prefer less walking"). The system extracts intent and guides route calculation.
*   **Multi-Factor Dijkstra Optimizer**: Networks a custom city infrastructure map containing key landmarks, transit corridors, and modal support. Computes three paths:
    1.  **Fastest Route**: Pure speed optimization using Car/Metro/Bus links.
    2.  **Eco & Active Mode**: Combines Walking, Cycling, and Metro segments to minimize carbon footprint.
    3.  **Low-Stress / AI Recommended**: Dynamically routes around active junctions containing high-severity frustration logs.
*   **Animated HUD Map (HTML5 Canvas)**: Features a real-time rendering loop with glowing paths and visual micro-animations (e.g., green dashed flows for metro, cyan paths for cabs, pulsing warning areas for hazards).
*   **Frustration Logger & Database**: A simple logging modal lets users report congestion, weather delays, construction blocks, or parking shortages. Data is saved in a local SQLite database and alters future routing outcomes instantly.
*   **Smart departure slots**: Predicts departure windows (Early Bird, AI Recommended, Peak Congestion) to advise on optimal leave times.

## 🛠️ Architecture & Tech Stack

*   **Frontend**: Single-Page Application (SPA) built using semantic **HTML5**, **Vanilla CSS** (for translucent glassmorphism cards and glow animations), and **modern JavaScript** (handles vector canvas draw states and Web Speech API).
*   **Backend**: **Python FastAPI** serving static assets and exposing REST APIs.
*   **Database**: **SQLite** pre-populated with realistic historical logs and stats.
*   **Deployment**: Pre-configured for deployment on **Vercel** serverless environments.

## 💻 Quick Start

### Prerequisites
Make sure you have Python 3.8+ installed.

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the application
```bash
python -m uvicorn main:app --reload --port 8000
```
Visit **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

### 3. Running Automated Tests
```bash
python -m unittest test_app.py
```

## ☁️ Vercel Deployment

DCO is configured for Vercel out of the box using `vercel.json`. It automatically routes database calls to `/tmp/dco.db` to accommodate serverless write restrictions.

1.  Install the Vercel CLI: `npm install -g vercel`
2.  Run `vercel` in the project directory.
