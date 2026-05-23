// DCO Live OpenStreetMap & Leaflet Controller

// Global map references
let map;
let routeLayerGroup;
let incidentLayerGroup;
let selectedMarker;

// Default coordinate states (Bangalore coordinates)
let originCoords = { lat: 12.9176, lng: 77.6244, name: "Silk Board, Bangalore" };
let destCoords = { lat: 12.9719, lng: 77.6412, name: "Indiranagar, Bangalore" };

// App State
let activeRoutes = [];
let selectedRouteIndex = 0;
let frustrationLogs = [];
let isRecording = false;
let speechRecognizer = null;

// DOM Elements
const optimizeBtn = document.getElementById("optimize-btn");
const voiceBtn = document.getElementById("voice-btn");
const voiceIcon = document.getElementById("voice-icon");
const nlInput = document.getElementById("nl-input");
const originInput = document.getElementById("origin-input");
const destinationInput = document.getElementById("destination-input");
const originSuggestions = document.getElementById("origin-suggestions");
const destinationSuggestions = document.getElementById("destination-suggestions");
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
    // 1. Initialize Map
    initMap();
    
    // 2. Setup Autocomplete Geocoders
    setupAutocomplete(originInput, originSuggestions, (coords) => {
        originCoords = coords;
        fetchDepartureSlots();
    });
    
    setupAutocomplete(destinationInput, destinationSuggestions, (coords) => {
        destCoords = coords;
        fetchDepartureSlots();
    });
    
    // 3. Init Speech APIs
    initSpeechRecognition();
    
    // 4. Fetch Stats and Incident Logs
    fetchStats();
    fetchFrustrationLogs();
    
    // 5. Setup Departure Predictions
    fetchDepartureSlots();
    
    // 6. Update Live Clock
    updateClock();
    setInterval(updateClock, 1000);
});

// Update Clock Widget
function updateClock() {
    const now = new Date();
    document.getElementById("current-time").innerText = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Initialize Leaflet Map
function initMap() {
    // Center initially on Bangalore
    map = L.map('city-map', {
        zoomControl: true,
        attributionControl: false
    }).setView([12.9716, 77.5946], 12);

    // CartoDB Dark Matter tile layer for premium dark dashboard feel
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19
    }).addTo(map);

    routeLayerGroup = L.layerGroup().addTo(map);
    incidentLayerGroup = L.layerGroup().addTo(map);

    // Browser Geolocation integration
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(position => {
            const { latitude, longitude } = position.coords;
            // Center map on user's current city
            map.setView([latitude, longitude], 12);
        });
    }

    // Click on map to trigger incident reportingpin drop
    map.on("click", (e) => {
        const { lat, lng } = e.latlng;
        
        if (selectedMarker) {
            map.removeLayer(selectedMarker);
        }
        
        selectedMarker = L.marker([lat, lng], {
            draggable: true
        }).addTo(map);
        
        selectedMarker.bindPopup("Report delay or bottleneck here.").openPopup();
        
        // Copy to modal
        document.getElementById("modal-location-lat").value = lat;
        document.getElementById("modal-location-lng").value = lng;
        document.getElementById("modal-location-name").value = `Coordinates: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        document.getElementById("modal-coordinates-display").innerText = `Dropped pin: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        
        // Auto open modal
        logModal.classList.add("active");
    });
}

// Setup Nominatim Autocomplete Suggestions
function setupAutocomplete(inputEl, suggestionsEl, callback) {
    let debounceTimer;
    
    inputEl.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        const query = inputEl.value.trim();
        
        if (query.length < 3) {
            suggestionsEl.innerHTML = "";
            suggestionsEl.classList.remove("active");
            return;
        }
        
        debounceTimer = setTimeout(async () => {
            try {
                const response = await fetch(`/api/geocode?q=${encodeURIComponent(query)}`);
                const results = await response.json();
                
                if (results.length === 0) {
                    suggestionsEl.innerHTML = `<div class="autocomplete-item">No locations found</div>`;
                    suggestionsEl.classList.add("active");
                    return;
                }
                
                suggestionsEl.innerHTML = results.map(item => `
                    <div class="autocomplete-item" data-lat="${item.lat}" data-lng="${item.lng}" data-name="${item.display_name}">
                        ${item.display_name}
                    </div>
                `).join("");
                
                suggestionsEl.classList.add("active");
                
                // Add item listeners
                suggestionsEl.querySelectorAll(".autocomplete-item").forEach(item => {
                    item.addEventListener("click", () => {
                        const lat = parseFloat(item.getAttribute("data-lat"));
                        const lng = parseFloat(item.getAttribute("data-lng"));
                        const name = item.getAttribute("data-name");
                        
                        inputEl.value = name;
                        suggestionsEl.classList.remove("active");
                        
                        callback({ lat, lng, name });
                    });
                });
            } catch (err) {
                console.error("Geocoding fetch failed:", err);
            }
        }, 300);
    });
    
    // Close autocompletes on external click
    document.addEventListener("click", (e) => {
        if (e.target !== inputEl && e.target !== suggestionsEl) {
            suggestionsEl.classList.remove("active");
        }
    });
}

// Update Map warning overlays based on database frustration reports
function drawHazardOverlays() {
    incidentLayerGroup.clearLayers();
    
    frustrationLogs.forEach(log => {
        const color = log.severity >= 4 ? 'hsl(355, 90%, 58%)' : 'hsl(42, 100%, 53%)';
        
        // Pulse ring overlay
        L.circle([log.lat, log.lng], {
            radius: 300,  // meters
            color: color,
            fillColor: color,
            fillOpacity: 0.15,
            weight: 1.5
        }).addTo(incidentLayerGroup);
        
        // Hazard icon pin
        const hazardMarker = L.circleMarker([log.lat, log.lng], {
            radius: 6,
            color: '#fff',
            fillColor: color,
            fillOpacity: 1.0,
            weight: 1.5
        }).addTo(incidentLayerGroup);
        
        hazardMarker.bindPopup(`
            <div style="font-family: var(--font-body); font-size:12px; color:#fff; background: hsl(222, 35%, 11%); padding:5px; border-radius:4px;">
                <b style="color: ${color};">${log.location_name}</b><br/>
                ${log.log_text}<br/>
                <span style="font-size:10px; color: var(--text-muted);">Severity: ${log.severity}/5</span>
            </div>
        `);
    });
}

// Fetch stats
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
            
            let dotsHtml = "";
            for (let i = 1; i <= 5; i++) {
                dotsHtml += `<span class="sev-dot ${i <= log.severity ? 'active-sev' : ''}"></span>`;
            }
            
            let icon = "alert-triangle";
            if (log.category === 'traffic') icon = "car";
            else if (log.category === 'crowding') icon = "users";
            else if (log.category === 'weather') icon = "cloud-rain";
            else if (log.category === 'construction') icon = "hammer";
            else if (log.category === 'parking') icon = "square-parking";
            
            return `
                <div class="report-log-card">
                    <div class="report-log-header">
                        <span class="report-location">${log.location_name.split(',')[0]}</span>
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
        
        lucide.createIcons();
        
        // Redraw overlays on map
        drawHazardOverlays();
    } catch (e) {
        console.error("Error loading frustration logs:", e);
    }
}

// Get departure predictions from API
async function fetchDepartureSlots() {
    try {
        const response = await fetch(`/api/departure-predictor?origin_lat=${originCoords.lat}&origin_lng=${originCoords.lng}&dest_lat=${destCoords.lat}&dest_lng=${destCoords.lng}`);
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
    optimizeBtn.disabled = true;
    optimizeBtn.innerText = "Querying satellite OSRM servers...";
    
    try {
        const response = await fetch("/api/optimize-route", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                origin_lat: originCoords.lat,
                origin_lng: originCoords.lng,
                dest_lat: destCoords.lat,
                dest_lng: destCoords.lng,
                origin_name: originCoords.name,
                destination_name: destCoords.name,
                preferences: nlInput.value
            })
        });
        
        const data = await response.json();
        activeRoutes = data.routes;
        selectedRouteIndex = 0;
        
        // Show AI advice
        aiAdviceContainer.style.display = "flex";
        aiAdviceText.innerText = data.ai_advice;
        
        // Render cards
        renderRouteCards();
        
        // Draw selected route
        drawSelectedRoutePath();
        
        // Update departure intervals
        fetchDepartureSlots();
    } catch (e) {
        console.error("Optimization failed:", e);
        alert("Live routing calculation failed. Please check network connectivity.");
    } finally {
        optimizeBtn.disabled = false;
        optimizeBtn.innerHTML = `<span>Optimize Commute Path</span><i data-lucide="arrow-right"></i>`;
        lucide.createIcons();
    }
}

// Render dynamic route suggestion card containers
function renderRouteCards() {
    if (!activeRoutes || activeRoutes.length === 0) {
        routeGrid.innerHTML = `<div class="card" style="grid-column: span 3; text-align:center; color: var(--text-secondary);">No routes found.</div>`;
        return;
    }
    
    routeGrid.innerHTML = activeRoutes.map((route, index) => {
        const isSelected = index === selectedRouteIndex ? 'selected' : '';
        
        let frustrationClass = "low";
        let frustrationTxt = "Smooth Flow";
        if (route.frustration_index >= 6.0) {
            frustrationClass = "high";
            frustrationTxt = "Heavy Delays";
        } else if (route.frustration_index >= 3.0) {
            frustrationClass = "med";
            frustrationTxt = "Slow Traffic";
        }
        
        // Visual indicator of delay warning count
        const alertBadge = route.incidents && route.incidents.length > 0 
            ? `<span class="badge" style="background: rgba(239, 68, 68, 0.1); color: hsl(355, 90%, 58%); border: 1px solid rgba(239, 68, 68, 0.2); margin-left: 8px;">${route.incidents.length} logs bypassed</span>` 
            : '';
            
        return `
            <div class="route-option-card ${isSelected}" onclick="selectRoute(${index})">
                <div class="route-card-header">
                    <span class="route-title">${route.route_type} ${alertBadge}</span>
                    <span class="route-vibe">${route.vibe}</span>
                </div>
                <div class="route-duration">
                    ${route.time_minutes}<span class="duration-unit"> mins</span>
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

// Select active route card and redraw the path
window.selectRoute = function(index) {
    selectedRouteIndex = index;
    document.querySelectorAll(".route-option-card").forEach((card, idx) => {
        if (idx === index) card.classList.add("selected");
        else card.classList.remove("selected");
    });
    
    drawSelectedRoutePath();
};

// Render the glowing polyline of the selected route on Leaflet Map
function drawSelectedRoutePath() {
    routeLayerGroup.clearLayers();
    
    if (!activeRoutes || activeRoutes.length === 0) return;
    const route = activeRoutes[selectedRouteIndex];
    if (!route) return;
    
    const coords = route.path_coords; // list of [lat, lng]
    if (!coords || coords.length === 0) return;

    // Define coloring
    let color = "hsl(182, 100%, 48%)"; // default Fastest cyan
    if (route.route_type === "Eco & Active Mode") {
        color = "hsl(145, 95%, 45%)"; // Mint green
    } else if (route.route_type === "Low-Stress / AI Vibe") {
        color = "hsl(270, 95%, 65%)"; // Neon purple
    }

    // 1. Draw glowing background polyline (Wide line, low opacity)
    const glowLine = L.polyline(coords, {
        color: color,
        weight: 12,
        opacity: 0.18,
        lineCap: 'round',
        lineJoin: 'round'
    }).addTo(routeLayerGroup);

    // 2. Draw core highlighted polyline (Thin line, high opacity)
    const mainLine = L.polyline(coords, {
        color: color,
        weight: 5,
        opacity: 0.9,
        lineCap: 'round',
        lineJoin: 'round'
    }).addTo(routeLayerGroup);

    // 3. Add pins at start and destination
    L.circleMarker(coords[0], {
        radius: 8,
        color: '#fff',
        fillColor: "hsl(182, 100%, 48%)",
        fillOpacity: 1,
        weight: 2
    }).addTo(routeLayerGroup).bindPopup("Start Location");

    L.circleMarker(coords[coords.length - 1], {
        radius: 8,
        color: '#fff',
        fillColor: "hsl(270, 95%, 65%)",
        fillOpacity: 1,
        weight: 2
    }).addTo(routeLayerGroup).bindPopup("Destination");

    // Adjust viewport to fit
    map.fitBounds(mainLine.getBounds(), { padding: [50, 50] });
}

// NLP Short-cuts triggers
function applyShortcut(type) {
    if (type === 'knee') {
        nlInput.value = "My knee is sore today, need to reach Indiranagar. Avoid bicycling or walking too much.";
        originInput.value = "Silk Board, Bangalore";
        destinationInput.value = "Indiranagar, Bangalore";
        originCoords = { lat: 12.9176, lng: 77.6244, name: "Silk Board, Bangalore" };
        destCoords = { lat: 12.9719, lng: 77.6412, name: "Indiranagar, Bangalore" };
    } else if (type === 'rain') {
        nlInput.value = "It is raining heavily! Bypass active flooding bottlenecks near Hebbal Flyover.";
        originInput.value = "Hebbal, Bangalore";
        destinationInput.value = "Majestic, Bangalore";
        originCoords = { lat: 13.0359, lng: 77.5970, name: "Hebbal, Bangalore" };
        destCoords = { lat: 12.9756, lng: 77.5728, name: "Majestic, Bangalore" };
    } else if (type === 'crowds') {
        nlInput.value = "I want a quiet, low-stress ride to connaught place and skip crowded buses.";
        originInput.value = "Noida Sector 62";
        destinationInput.value = "Connaught Place, Delhi";
        originCoords = { lat: 28.6273, lng: 77.3725, name: "Noida Sector 62" };
        destCoords = { lat: 28.6304, lng: 77.2177, name: "Connaught Place, Delhi" };
    }
}

// Vibe Preset Toggles
document.querySelectorAll(".vibe-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".vibe-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
    });
});

// Voice Input configuration
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
        nlInput.placeholder = "Describe how you want to travel today in plain words...";
        lucide.createIcons();
    };
    
    speechRecognizer.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        nlInput.value = transcript;
        performRouting();
    };
    
    speechRecognizer.onerror = (e) => {
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

// Modal Actions
openModalBtn.addEventListener("click", () => {
    // If no pin is dropped, default modal coords to current map center
    const center = map.getCenter();
    document.getElementById("modal-location-lat").value = center.lat;
    document.getElementById("modal-location-lng").value = center.lng;
    document.getElementById("modal-location-name").value = "Custom Coordinates";
    document.getElementById("modal-coordinates-display").innerText = `Click map to move pin: ${center.lat.toFixed(4)}, ${center.lng.toFixed(4)}`;
    
    logModal.classList.add("active");
});

closeModalBtn.addEventListener("click", () => {
    logModal.classList.remove("active");
    if (selectedMarker) {
        map.removeLayer(selectedMarker);
        selectedMarker = null;
    }
});

cancelModalBtn.addEventListener("click", () => {
    logModal.classList.remove("active");
    if (selectedMarker) {
        map.removeLayer(selectedMarker);
        selectedMarker = null;
    }
});

window.addEventListener("click", (e) => {
    if (e.target === logModal) {
        logModal.classList.remove("active");
        if (selectedMarker) {
            map.removeLayer(selectedMarker);
            selectedMarker = null;
        }
    }
});

// Severity slider tracker
severityRange.addEventListener("input", (e) => {
    severityVal.innerText = e.target.value;
});

// Form Submission logic
frustrationForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const location_name = document.getElementById("modal-location-name").value;
    const category = document.querySelector('input[name="category"]:checked').value;
    const severity = parseInt(severityRange.value);
    const log_text = document.getElementById("log-text").value;
    const lat = parseFloat(document.getElementById("modal-location-lat").value);
    const lng = parseFloat(document.getElementById("modal-location-lng").value);
    
    try {
        const response = await fetch("/api/frustration-logs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ location_name, category, severity, log_text, lat, lng })
        });
        
        const res = await response.json();
        if (res.status === 'success') {
            document.getElementById("log-text").value = "";
            logModal.classList.remove("active");
            
            if (selectedMarker) {
                map.removeLayer(selectedMarker);
                selectedMarker = null;
            }
            
            // Reload logs, overlays, and stats
            fetchFrustrationLogs();
            fetchStats();
            
            // If active routes exist, automatically re-route to avoid new warning
            if (activeRoutes && activeRoutes.length > 0) {
                performRouting();
            }
        }
    } catch (err) {
        alert("Failed to submit frustration log.");
    }
});
