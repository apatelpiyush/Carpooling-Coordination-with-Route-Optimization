// Apply saved theme when the page loads
const savedTheme = localStorage.getItem("theme");

if (savedTheme === "dark") {
    document.body.classList.add("dark-mode");
}

// Theme toggle
const themeToggle = document.getElementById("theme-toggle");
const themeIcon = document.getElementById("theme-icon");

function updateThemeButton() {
    const isDark = document.body.classList.contains("dark-mode");

    if (themeIcon) {
        themeIcon.textContent = isDark ? "☀" : "☾";
    }

    if (themeToggle) {
        themeToggle.setAttribute(
            "aria-label",
            isDark ? "Enable light mode" : "Enable dark mode"
        );
    }
}

updateThemeButton();

if (themeToggle) {
    themeToggle.addEventListener("click", () => {
        document.body.classList.toggle("dark-mode");

        const isDark = document.body.classList.contains("dark-mode");

        localStorage.setItem("theme", isDark ? "dark" : "light");

        updateThemeButton();
    });
}


// Logout
async function logoutUser() {
    try {
        const response = await fetch("/auth/logout", {
            method: "POST"
        });

        if (response.ok) {
            window.location.href = "/login";
        }
    } catch (error) {
        console.error("Logout failed:", error);
        alert("Unable to log out. Please try again.");
    }
}


let rideMap;
let sourceMarker = null;
let destinationMarker = null;

let selectedSource = null;
let selectedDestination = null;

let driverVehicles = [];

function initializeRideMap() {
    if (rideMap) return;

    rideMap = L.map("ride-map").setView([22.5, 78.9], 5);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(rideMap);
}

function updateMapMarker(type, location) {
    const marker = type === "source"
        ? sourceMarker
        : destinationMarker;

    if (marker) {
        rideMap.removeLayer(marker);
    }

    const newMarker = L.marker([
        Number(location.lat),
        Number(location.lon)
    ]).addTo(rideMap);

    newMarker.bindPopup(
        escapeHTML(location.name)
    );

    if (type === "source") {
        sourceMarker = newMarker;
        selectedSource = location;
        document.getElementById("source-selected").textContent =
            `Selected: ${location.name}`;
    } else {
        destinationMarker = newMarker;
        selectedDestination = location;
        document.getElementById("destination-selected").textContent =
            `Selected: ${location.name}`;
    }

    rideMap.setView(
        [Number(location.lat), Number(location.lon)],
        12
    );
}

async function searchLocation(type) {
    const inputId = type === "source"
        ? "ride-source"
        : "ride-destination";

    const resultsId = type === "source"
        ? "source-results"
        : "destination-results";

    const query = document.getElementById(inputId).value.trim();
    const resultsContainer = document.getElementById(resultsId);

    if (!query) {
        resultsContainer.textContent = "Enter a location first.";
        return;
    }

    resultsContainer.textContent = "Searching...";

    try {
        const params = new URLSearchParams({
            q: query,
            format: "jsonv2",
            limit: "5",
            countrycodes: "in"
        });

        const response = await fetch(
            `https://nominatim.openstreetmap.org/search?${params}`
        );

        if (!response.ok) {
            throw new Error("Location search failed.");
        }

        const results = await response.json();

        if (!results.length) {
            resultsContainer.textContent = "No locations found.";
            return;
        }

        resultsContainer.innerHTML = results.map((item, index) => `
            <button type="button"
                    class="location-result"
                    data-index="${index}">
                ${escapeHTML(item.display_name)}
            </button>
        `).join("");

        resultsContainer.querySelectorAll(".location-result")
            .forEach(button => {
                button.addEventListener("click", () => {
                    const item = results[Number(button.dataset.index)];

                    const location = {
                        name: item.display_name,
                        lat: Number(item.lat),
                        lon: Number(item.lon)
                    };

                    updateMapMarker(type, location);
                    resultsContainer.innerHTML = "";
                });
            });

    } catch (error) {
        resultsContainer.textContent = error.message;
    }
}

async function loadVehicleOptions() {
    const data = await apiGet("/api/vehicles");
    driverVehicles = data.vehicles || [];

    const select = document.getElementById("ride-vehicle");

    if (!driverVehicles.length) {
        select.innerHTML = '<option value="">Register a vehicle first</option>';
        return;
    }

    select.innerHTML = `
        <option value="">Choose a vehicle</option>
        ${driverVehicles.map(vehicle => `
            <option value="${vehicle.vehicle_id}">
                ${escapeHTML(vehicle.make)} ${escapeHTML(vehicle.model)}
                (${escapeHTML(vehicle.plate_number)})
            </option>
        `).join("")}
    `;

    updateVehicleCapacity();
}

function updateVehicleCapacity() {
    const vehicleId = Number(
        document.getElementById("ride-vehicle").value
    );

    const vehicle = driverVehicles.find(
        item => item.vehicle_id === vehicleId
    );

    const seatsInput = document.getElementById("ride-seats");
    const hint = document.getElementById("seat-capacity-hint");

    if (!vehicle) {
        seatsInput.removeAttribute("max");
        hint.textContent = "";
        return;
    }

    seatsInput.max = vehicle.capacity;
    hint.textContent = `Maximum capacity: ${vehicle.capacity} seats`;

    if (Number(seatsInput.value) > vehicle.capacity) {
        seatsInput.value = vehicle.capacity;
    }
}

function setupRideForm() {
    initializeRideMap();

    document.getElementById("search-source")
        .addEventListener("click", () => searchLocation("source"));

    document.getElementById("search-destination")
        .addEventListener("click", () => searchLocation("destination"));

    document.getElementById("ride-vehicle")
        .addEventListener("change", updateVehicleCapacity);

    document.getElementById("ride-form")
        .addEventListener("submit", publishRide);

    loadVehicleOptions().catch(error => showError(error.message));
}

async function publishRide(event) {
    event.preventDefault();

    const message = document.getElementById("ride-message");
    const button = event.submitter;

    if (!selectedSource || !selectedDestination) {
        message.textContent = "Select both locations from the search results.";
        return;
    }

    if (
        selectedSource.lat === selectedDestination.lat &&
        selectedSource.lon === selectedDestination.lon
    ) {
        message.textContent = "Starting location and destination must differ.";
        return;
    }

    const departure = document.getElementById("ride-departure").value;

    if (!departure || new Date(departure) <= new Date()) {
        message.textContent = "Choose a future departure date and time.";
        return;
    }

    const payload = {
        vehicle_id: Number(document.getElementById("ride-vehicle").value),
        source: document.getElementById("ride-source").value.trim(),
        destination: document.getElementById("ride-destination").value.trim(),
        departure_time: departure,
        available_seats: Number(document.getElementById("ride-seats").value),
        price_per_seat: Number(document.getElementById("ride-price").value),
        source_lat: selectedSource.lat,
        source_lon: selectedSource.lon,
        destination_lat: selectedDestination.lat,
        destination_lon: selectedDestination.lon
    };

    if (!payload.vehicle_id) {
        message.textContent = "Select a vehicle.";
        return;
    }

    if (
        !payload.source ||
        !payload.destination ||
        !Number.isInteger(payload.available_seats) ||
        payload.available_seats < 1 ||
        !Number.isFinite(payload.price_per_seat) ||
        payload.price_per_seat < 0
    ) {
        message.textContent = "Check the ride details and try again.";
        return;
    }

    button.disabled = true;
    message.textContent = "Publishing ride...";

    try {
        const response = await fetch("/api/rides", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const text = await response.text();
        let data;

        try {
            data = JSON.parse(text);
        } catch {
            throw new Error("Unexpected server response. Check Flask logs.");
        }

        if (!response.ok) {
            throw new Error(data.error || "Unable to publish ride.");
        }

        message.textContent =
            `Ride #${data.ride.ride_id} published successfully.`;

        document.getElementById("ride-form").reset();

        selectedSource = null;
        selectedDestination = null;

        if (sourceMarker) rideMap.removeLayer(sourceMarker);
        if (destinationMarker) rideMap.removeLayer(destinationMarker);

        sourceMarker = null;
        destinationMarker = null;

        document.getElementById("source-selected").textContent =
            "No starting location selected.";

        document.getElementById("destination-selected").textContent =
            "No destination selected.";

        document.getElementById("source-results").innerHTML = "";
        document.getElementById("destination-results").innerHTML = "";

        updateVehicleCapacity();

        await loadDriverDashboard();

    } catch (error) {
        message.textContent = error.message;
    } finally {
        button.disabled = false;
    }
}

