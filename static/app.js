// DCO Frontend Controller & Canvas Renderer

// Coordinate mapping matching the backend network (mapped to Canvas 900x420)
const LANDMARKS = {
    "Danapur": { x: 100, y: 220, label: "Danapur (West)" },
    "Bailey Road": { x: 260, y: 220, label: "Bailey Road" },
    "Boring Road Crossing": { x: 380, y: 120, label: "Boring Rd Crossing" },
    "Patliputra Colony": { x: 300, y: 70, label: "Patliputra Colony" },
    "Dak Bungalow Crossing": { x: 520, y: 200, label: "Dak Bungalow Crossing" },
    "Gandhi Maidan": { x: 620, y: 100, label: "Gandhi Maidan" },
    "Patna Junction": { x: 520, y: 320, label: "Patna Junction" },
    "Rajendra Nagar": { x: 720, y: 280, label: "Rajendra Nagar" },
    "Kankarbagh": { x: 760, y: 360, label: "Kankarbagh" },
    "Patna City": { x: 860, y: 200, label: "Patna City" }
};

// Edge connections for rendering base grid
const NETWORK_EDGES = [
    ["Danapur", "Bailey Road"],
    ["Danapur", "Patliputra Colony"],
    ["Bailey Road", "Boring Road Crossing"],
    ["Bailey Road", "Patna Junction"],
    ["Bailey Road", "Dak Bungalow Crossing"],
    ["Boring Road Crossing", "Patliputra Colony"],
    ["Boring Road Crossing", "Dak Bungalow Crossing"],
    ["Boring Road Crossing", "Gandhi Maidan"],
    ["Patliputra Colony", "Gandhi Maidan"],
    ["Dak Bungalow Crossing", "Gandhi Maidan"],
    ["Dak Bungalow Crossing", "Patna Junction"],
    ["Dak Bungalow Crossing", "Rajendra Nagar"],
    ["Gandhi Maidan", "Rajendra Nagar"],
    ["Gandhi Maidan", "Patna City"],
    ["Patna Junction", "Kankarbagh"],
    ["Rajendra Nagar", "Kankarbagh"],
    ["Rajendra Nagar", "Patna City"],
    ["Kankarbagh", "Patna City"]
];

// App State
let activeRoutes = [];
let selectedRouteIndex = 0;
let frustrationLogs = [];
let currentPulseRadius = 0;
let lineDashOffset = 0;
let isRecording = false;
let speechRecognizer = null;

// DOM Elements
const canvas = document.getElementById("city-map");
const ctx = canvas.getContext("2d");
const optimizeBtn = document.getElementById("optimize-btn");
const voiceBtn = document.getElementById("voice-btn");
const voiceIcon = document.getElementById("voice-icon");
const nlInput = document.getElementById("nl-input");
const originSelect = document.getElementById("origin-select");
const destinationSelect = document.getElementById("destination-select");
const routeGrid = document.getElementById("routes-grid-container");
const aiAdviceContainer = document.getElementById("ai-advice-container");
const aiAdviceText = document.getElementById("ai-advice-text");
const departureSlots = document.getElementById("departure-slots");
const reportsList = document.getElementById("community-reports-list");
const reportCount = document.getElementById("report-count");

// Modal Elements
const logModal = document.getElementById("log-modal");
const openModalBtn = document.getElementById("open-log-modal-btn");
const closeModalBtn = document.getElementById("close-modal-btn");
const cancelModalBtn = document.getElementById("cancel-modal-btn");
const frustrationForm = document.getElementById("frustration-form");
const severityRange = document.getElementById("severity-range");
const severityVal = document.getElementById("severity-val");

// Setup Page Onload
window.addEventListener("DOMContentLoaded", () => {
    // Start canvas animation loop
    requestAnimationFrame(animationLoop);
    
    // Init speech API
    initSpeechRecognition();
    
    // Fetch stats and reports initially
    fetchStats();
    fetchFrustrationLogs();
    
    // Update live clock
    updateClock();
    setInterval(updateClock, 1000);
});

// Update Clock Widget
function updateClock() {
    const now = new Date();
    document.getElementById("current-time").innerText = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Canvas Animation Loop
function animationLoop(timestamp) {
    // Calculate pulse values
    currentPulseRadius = Math.sin(timestamp / 200) * 8 + 12;
    lineDashOffset = (lineDashOffset - 0.4) % 100;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw HUD Grid
    drawMapGrid();
    
    // Draw Base Infrastructure Network (Faint links)
    drawBaseNetwork();
    
    // Draw Active Selected Route
    drawActiveRoute();
    
    // Draw Frustration/Hazard warnings (Pulsing circles)
    drawHazardZones();
    
    // Draw Landmark Nodes & Labels
    drawNodes();
    
    requestAnimationFrame(animationLoop);
}

// Draw a subtle HUD grid background
function drawMapGrid() {
    ctx.strokeStyle = "rgba(0, 242, 254, 0.02)";
    ctx.lineWidth = 1;
    const gridSize = 40;
    for (let x = 0; x < canvas.width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
    }
}

// Draw static street network paths
function drawBaseNetwork() {
    ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
    ctx.lineWidth = 2;
    ctx.setLineDash([]);
    
    NETWORK_EDGES.forEach(([fromNode, toNode]) => {
        const start = LANDMARKS[fromNode];
        const end = LANDMARKS[toNode];
        if (start && end) {
            ctx.beginPath();
            ctx.moveTo(start.x, start.y);
            ctx.lineTo(end.x, end.y);
            ctx.stroke();
        }
    });
}

// Draw the dynamic glowing paths for the currently selected route
function drawActiveRoute() {
    if (!activeRoutes || activeRoutes.length === 0) return;
    
    const activeRoute = activeRoutes[selectedRouteIndex];
    if (!activeRoute) return;
    
    const path = activeRoute.path;
    const modes = activeRoute.modes;
    
    for (let i = 0; i < path.length - 1; i++) {
        const startNode = LANDMARKS[path[i]];
        const endNode = LANDMARKS[path[i+1]];
        const mode = modes[i];
        
        if (startNode && endNode) {
            ctx.beginPath();
            ctx.moveTo(startNode.x, startNode.y);
            ctx.lineTo(endNode.x, endNode.y);
            
            // Set styles based on transit mode
            if (mode === "metro") {
                // Green dashed animated lines
                ctx.strokeStyle = "hsl(145, 95%, 45%)";
                ctx.lineWidth = 6;
                ctx.setLineDash([12, 8]);
                ctx.lineDashOffset = lineDashOffset;
                ctx.shadowColor = "rgba(74, 222, 128, 0.4)";
                ctx.shadowBlur = 10;
            } else if (mode === "car" || mode === "bus") {
                // Cyan solid lines with floating particles simulated
                ctx.strokeStyle = "hsl(182, 100%, 48%)";
                ctx.lineWidth = 5;
                ctx.setLineDash([]);
                ctx.shadowColor = "rgba(0, 242, 254, 0.4)";
                ctx.shadowBlur = 8;
            } else {
                // Purple dotted lines for cycle/walk
                ctx.strokeStyle = "hsl(270, 95%, 65%)";
                ctx.lineWidth = 4;
                ctx.setLineDash([4, 6]);
                ctx.lineDashOffset = -lineDashOffset;
                ctx.shadowColor = "rgba(168, 85, 247, 0.4)";
                ctx.shadowBlur = 6;
            }
            
            ctx.stroke();
            
            // Reset shadows
            ctx.shadowBlur = 0;
            ctx.setLineDash([]);
        }
    }
}

// Draw warning alerts dynamically around nodes with active frustration records
function drawHazardZones() {
    frustrationLogs.forEach(log => {
        const node = LANDMARKS[log.location_name];
        if (node) {
            const sev = log.severity;
            // Draw pulsing orange/red gradient around the location
            ctx.beginPath();
            ctx.arc(node.x, node.y, currentPulseRadius * (sev * 0.4), 0, 2 * Math.PI);
            
            // Use severity color
            if (sev >= 4) {
                ctx.fillStyle = "rgba(239, 68, 68, 0.08)";
                ctx.strokeStyle = "rgba(239, 68, 68, 0.4)";
            } else {
                ctx.fillStyle = "rgba(253, 224, 71, 0.08)";
                ctx.strokeStyle = "rgba(253, 224, 71, 0.4)";
            }
            
            ctx.lineWidth = 1.5;
            ctx.fill();
            ctx.stroke();
            
            // Draw small hazard marker
            ctx.beginPath();
            ctx.arc(node.x, node.y - 12, 4, 0, 2 * Math.PI);
            ctx.fillStyle = sev >= 4 ? "hsl(355, 90%, 58%)" : "hsl(42, 100%, 53%)";
            ctx.fill();
        }
    });
}

// Draw nodes (landmarks) and names
function drawNodes() {
    ctx.setLineDash([]);
    ctx.shadowBlur = 0;
    
    // Check if start/end nodes exist
    const selectedOrigin = originSelect.value;
    const selectedDest = destinationSelect.value;
    
    Object.entries(LANDMARKS).forEach(([name, node]) => {
        const isOrigin = name === selectedOrigin;
        const isDest = name === selectedDest;
        
        ctx.beginPath();
        ctx.arc(node.x, node.y, (isOrigin || isDest) ? 8 : 5, 0, 2 * Math.PI);
        
        // Draw colors matching node states
        if (isOrigin) {
            ctx.fillStyle = "hsl(182, 100%, 48%)"; // cyan
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // Draw pulse around start pin
            ctx.beginPath();
            ctx.arc(node.x, node.y, currentPulseRadius * 0.7, 0, 2 * Math.PI);
            ctx.strokeStyle = "rgba(0, 242, 254, 0.4)";
            ctx.stroke();
        } else if (isDest) {
            ctx.fillStyle = "hsl(270, 95%, 65%)"; // purple destination
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // Draw pulse around destination pin
            ctx.beginPath();
            ctx.arc(node.x, node.y, currentPulseRadius * 0.7, 0, 2 * Math.PI);
            ctx.strokeStyle = "rgba(168, 85, 247, 0.4)";
            ctx.stroke();
        } else {
            ctx.fillStyle = "rgba(30, 41, 59, 0.9)";
            ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
            ctx.lineWidth = 1;
            ctx.stroke();
        }
        ctx.fill();
        
        // Render labels
        ctx.font = (isOrigin || isDest) ? "bold 11px var(--font-body)" : "10px var(--font-body)";
        ctx.fillStyle = (isOrigin || isDest) ? "#fff" : "var(--text-secondary)";
        ctx.textAlign = "center";
        ctx.fillText(node.label, node.x, node.y + 18);
    });
}

// Manual inputs selectors update triggers map redraw highlights
originSelect.addEventListener("change", () => {
    fetchDepartureSlots();
});
destinationSelect.addEventListener("change", () => {
    fetchDepartureSlots();
});

// Event listeners for NLP pills
function applyShortcut(type) {
    if (type === 'knee') {
        nlInput.value = "I need to reach office by 9:30. My knee hurts today so I prefer less walking and want to avoid stairs/crowded buses.";
        originSelect.value = "Danapur";
        destinationSelect.value = "Dak Bungalow Crossing";
    } else if (type === 'rain') {
        nlInput.value = "It is raining heavily! Avoid usual waterlogged streets near Bailey Road or Kankarbagh if possible.";
        originSelect.value = "Kankarbagh";
        destinationSelect.value = "Gandhi Maidan";
    } else if (type === 'crowds') {
        nlInput.value = "I hate crowded metros today and want a quiet, low-stress ride.";
        originSelect.value = "Patliputra Colony";
        destinationSelect.value = "Patna Junction";
    }
}

// Vibe Button Click Presets
document.querySelectorAll(".vibe-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".vibe-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
    });
});

// Fetch Stats from Backend
async function fetchStats() {
    try {
        const response = await fetch("/api/stats");
        const stats = await response.json();
        
        document.getElementById("stat-time-saved").innerText = stats.total_time_saved_minutes + "m";
        document.getElementById("stat-stress-reduction").innerText = stats.stress_reduction_percentage + "%";
        document.getElementById("stat-total-commutes").innerText = stats.total_commutes;
    } catch (e) {
        console.error("Error loading stats:", e);
    }
}

// Fetch Frustration Logs
async function fetchFrustrationLogs() {
    try {
        const response = await fetch("/api/frustration-logs");
        frustrationLogs = await response.json();
        
        // Update community reports panel
        reportCount.innerText = frustrationLogs.length + " reports";
        
        if (frustrationLogs.length === 0) {
            reportsList.innerHTML = `<div class="report-placeholder">No active road frustrations logged today.</div>`;
            return;
        }
        
        reportsList.innerHTML = frustrationLogs.map(log => {
            const date = new Date(log.timestamp);
            const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            // Build severity dots
            let dotsHtml = "";
            for (let i = 1; i <= 5; i++) {
                dotsHtml += `<span class="sev-dot ${i <= log.severity ? 'active-sev' : ''}"></span>`;
            }
            
            // Category icon selection
            let icon = "alert-triangle";
            if (log.category === 'traffic') icon = "car";
            else if (log.category === 'crowding') icon = "users";
            else if (log.category === 'weather') icon = "cloud-rain";
            else if (log.category === 'construction') icon = "hammer";
            else if (log.category === 'parking') icon = "square-parking";
            
            return `
                <div class="report-log-card">
                    <div class="report-log-header">
                        <span class="report-location">${log.location_name}</span>
                        <span class="report-time">${timeStr}</span>
                    </div>
                    <p class="report-text">${log.log_text}</p>
                    <div class="report-footer">
                        <span class="report-category"><i data-lucide="${icon}" style="width:11px;height:11px;"></i> ${log.category}</span>
                        <div class="report-severity-pills">${dotsHtml}</div>
                    </div>
                </div>
            `;
        }).join("");
        
        // Trigger lucide icons
        lucide.createIcons();
    } catch (e) {
        console.error("Error loading frustration logs:", e);
    }
}

// Get Departure Window Slot Recommendations
async function fetchDepartureSlots() {
    const origin = originSelect.value;
    const dest = destinationSelect.value;
    
    try {
        const response = await fetch(`/api/departure-predictor?origin=${origin}&destination=${dest}`);
        const data = await response.json();
        
        departureSlots.innerHTML = data.slots.map(slot => {
            const badgeClass = slot.status === 'Green' ? 'green' : 'red';
            return `
                <div class="slot-row">
                    <div class="slot-time">
                        <span class="slot-val">${slot.time}</span>
                        <span class="slot-lbl">${slot.label}</span>
                    </div>
                    <div class="slot-meta">
                        <span class="slot-dur">${slot.estimated_duration} min</span>
                        <span class="status-badge ${badgeClass}">${slot.stress}</span>
                    </div>
                </div>
            `;
        }).join("");
    } catch (e) {
        departureSlots.innerHTML = `<div class="slot-placeholder">Failed to calculate departure windows.</div>`;
    }
}

// Trigger Route Optimization
optimizeBtn.addEventListener("click", performRouting);

async function performRouting() {
    const origin = originSelect.value;
    const dest = destinationSelect.value;
    const preferences = nlInput.value;
    
    // Add temporary loading indicator
    optimizeBtn.disabled = true;
    optimizeBtn.innerText = "Analyzing live commute options...";
    
    try {
        const response = await fetch("/api/optimize-route", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ origin, destination, preferences })
        });
        
        const data = await response.json();
        activeRoutes = data.routes;
        selectedRouteIndex = 0; // default to first recommendation
        
        // Show AI Advice
        aiAdviceContainer.style.display = "flex";
        aiAdviceText.innerText = data.ai_advice;
        
        // Render Route Cards
        renderRouteCards();
        
        // Update departure window
        fetchDepartureSlots();
    } catch (e) {
        console.error("Optimization failed:", e);
        alert("Route optimization failed. Verify endpoint connectivity.");
    } finally {
        optimizeBtn.disabled = false;
        optimizeBtn.innerHTML = `<span>Optimize Commute Path</span><i data-lucide="arrow-right"></i>`;
        lucide.createIcons();
    }
}

// Render dynamic route suggestion card containers
function renderRouteCards() {
    if (!activeRoutes || activeRoutes.length === 0) {
        routeGrid.innerHTML = `<div class="card" style="grid-column: span 3; text-align:center; color: var(--text-secondary);">No routes found for the selected hubs.</div>`;
        return;
    }
    
    routeGrid.innerHTML = activeRoutes.map((route, index) => {
        const isSelected = index === selectedRouteIndex ? 'selected' : '';
        
        // Format transit badges list
        const segmentsHtml = route.modes.map((mode, i) => {
            let icon = "walk";
            if (mode === "car") icon = "car";
            else if (mode === "bus") icon = "bus";
            else if (mode === "metro") icon = "subway";
            else if (mode === "bike") icon = "bike";
            
            const fromLoc = route.path[i];
            return `
                <span class="segment-item" title="Transit to ${route.path[i+1]} via ${mode}">
                    <i data-lucide="${icon}" style="width:10px;height:10px;display:inline-block;"></i>
                    ${fromLoc}
                </span>
                ${i < route.modes.length - 1 ? '<span class="segment-arrow">&rarr;</span>' : ''}
            `;
        }).join("");
        
        // Frustration badge check
        let frustrationClass = "low";
        let frustrationTxt = "Smooth";
        if (route.frustration_index >= 6.0) {
            frustrationClass = "high";
            frustrationTxt = "Heavy Jams";
        } else if (route.frustration_index >= 3.0) {
            frustrationClass = "med";
            frustrationTxt = "Moderate Delay";
        }
        
        return `
            <div class="route-option-card ${isSelected}" onclick="selectRoute(${index})">
                <div class="route-card-header">
                    <span class="route-title">${route.route_type}</span>
                    <span class="route-vibe">${route.vibe}</span>
                </div>
                <div class="route-duration">
                    ${route.time_minutes}<span class="duration-unit"> mins</span>
                </div>
                <div class="route-segments">
                    ${segmentsHtml}
                </div>
                <div class="route-details-row">
                    <div class="route-meta-item"><i data-lucide="map"></i> ${route.distance_km} km</div>
                    <div class="route-meta-item"><i data-lucide="leaf"></i> ${route.co2_grams}g CO2</div>
                    <div class="route-frustration-meter">
                        <span class="frustration-badge ${frustrationClass}">${frustrationTxt}</span>
                    </div>
                </div>
            </div>
        `;
    }).join("");
    
    lucide.createIcons();
}

// Route selection mapping highlights click index
window.selectRoute = function(index) {
    selectedRouteIndex = index;
    // Highlight correct card UI
    document.querySelectorAll(".route-option-card").forEach((card, idx) => {
        if (idx === index) card.classList.add("selected");
        else card.classList.remove("selected");
    });
};

// Web Speech Recognition Config
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.log("Web Speech API not supported on this browser.");
        voiceBtn.style.display = "none";
        return;
    }
    
    speechRecognizer = new SpeechRecognition();
    speechRecognizer.continuous = false;
    speechRecognizer.interimResults = false;
    speechRecognizer.lang = 'en-US';
    
    speechRecognizer.onstart = () => {
        isRecording = true;
        voiceBtn.classList.add("recording");
        voiceIcon.setAttribute("data-lucide", "mic-off");
        nlInput.placeholder = "Listening to your commute request...";
        lucide.createIcons();
    };
    
    speechRecognizer.onend = () => {
        isRecording = false;
        voiceBtn.classList.remove("recording");
        voiceIcon.setAttribute("data-lucide", "mic");
        nlInput.placeholder = "e.g. I need to reach Patna Junction by 9:30 AM. My knee hurts today...";
        lucide.createIcons();
    };
    
    speechRecognizer.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        nlInput.value = transcript;
        performRouting(); // auto trigger search
    };
    
    speechRecognizer.onerror = (e) => {
        console.error("Speech error:", e);
        isRecording = false;
        voiceBtn.classList.remove("recording");
        voiceIcon.setAttribute("data-lucide", "mic");
        lucide.createIcons();
    };
}

voiceBtn.addEventListener("click", () => {
    if (!speechRecognizer) return;
    if (isRecording) {
        speechRecognizer.stop();
    } else {
        speechRecognizer.start();
    }
});

// Modal Logic
openModalBtn.addEventListener("click", () => {
    logModal.classList.add("active");
});
closeModalBtn.addEventListener("click", () => {
    logModal.classList.remove("active");
});
cancelModalBtn.addEventListener("click", () => {
    logModal.classList.remove("active");
});
// Close modal on background click
window.addEventListener("click", (e) => {
    if (e.target === logModal) {
        logModal.classList.remove("active");
    }
});

// Update Severity label during sliders sliding
severityRange.addEventListener("input", (e) => {
    severityVal.innerText = e.target.value;
});

// Handle Frustration Form Submit
frustrationForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const location_name = document.getElementById("modal-location-select").value;
    const category = document.querySelector('input[name="category"]:checked').value;
    const severity = parseInt(severityRange.value);
    const log_text = document.getElementById("log-text").value;
    
    try {
        const response = await fetch("/api/frustration-logs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ location_name, category, severity, log_text })
        });
        
        const res = await response.json();
        if (res.status === 'success') {
            // Reset and close modal
            document.getElementById("log-text").value = "";
            logModal.classList.remove("active");
            
            // Reload logs and stats
            fetchFrustrationLogs();
            fetchStats();
            
            // If active routes exist, recalculate to reroute around new hazard
            if (activeRoutes && activeRoutes.length > 0) {
                performRouting();
            }
        }
    } catch (err) {
        alert("Failed to save report.");
    }
});
