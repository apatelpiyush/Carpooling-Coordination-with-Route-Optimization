
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("ride-search-form");

    form.addEventListener("submit", event => {
        event.preventDefault();
        searchRides();
    });

    searchRides();
    initializeNearbySearch();
});

async function searchRides() {
    const source = document.getElementById("search-source").value.trim();
    const destination = document.getElementById("search-destination").value.trim();

    const results = document.getElementById("rides-results");
    const count = document.getElementById("results-count");
    const message = document.getElementById("rides-message");

    results.innerHTML = "";
    message.textContent = "Searching rides...";
    count.textContent = "";

    const params = new URLSearchParams();

    if (source) params.append("source", source);
    if (destination) params.append("destination", destination);

    try {
        const response = await fetch(`/api/rides?${params.toString()}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Could not search rides.");
        }

        const rides = data.rides || [];

        message.textContent = "";
        count.textContent = `${rides.length} ride(s) found`;

        if (!rides.length) {
            results.innerHTML = `
                <div class="rides-empty">
                    No rides found for this search.
                    Try a different location.
                </div>
            `;
            return;
        }

        results.innerHTML = rides.map(ride => `
            <article class="ride-result">
                <div class="ride-route">
                    <div>
                        <span class="ride-location-label">FROM</span>
                        <strong>${escapeRideHTML(ride.source)}</strong>
                    </div>

                    <span class="ride-arrow">→</span>

                    <div>
                        <span class="ride-location-label">TO</span>
                        <strong>${escapeRideHTML(ride.destination)}</strong>
                    </div>
                </div>

                <div class="ride-information">
                    <div>
                        <span>Driver</span>
                        <strong>${escapeRideHTML(ride.driver_name)}</strong>
                    </div>

                    <div>
                        <span>Departure</span>
                        <strong>${formatRideDate(ride.departure_time)}</strong>
                    </div>

                    <div>
                        <span>Available seats</span>
                        <strong>${Number(ride.available_seats)}</strong>
                    </div>

                    <div>
                        <span>Price per seat</span>
                        <strong>₹${Number(ride.price_per_seat).toFixed(2)}</strong>
                    </div>
                </div>

                <a href="/rides/${Number(ride.ride_id)}"
                   class="ride-view-link">
                    View details
                </a>
            </article>
        `).join("");

    } catch (error) {
        message.textContent = error.message;
    }
}

function formatRideDate(value) {
    return new Date(value).toLocaleString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    });
}

function escapeRideHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}


let nearbyMap;
let pickupMarker = null;
let dropMarker = null;
let proposedRouteLayer = null;

let selectedPickup = null;
let selectedDrop = null;

function initializeNearbyMap() {
    if (nearbyMap) return;

    nearbyMap = L.map("nearby-map").setView([22.5, 78.9], 5);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(nearbyMap);
}

async function searchNearbyLocation(type) {
    const inputId = type === "pickup"
        ? "nearby-pickup"
        : "nearby-drop";

    const resultsId = type === "pickup"
        ? "pickup-results"
        : "drop-results";

    const query = document.getElementById(inputId).value.trim();
    const container = document.getElementById(resultsId);

    if (!query) {
        container.textContent = "Enter a location first.";
        return;
    }

    container.textContent = "Searching...";

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

        const locations = await response.json();

        if (!locations.length) {
            container.textContent = "No locations found.";
            return;
        }

        container.innerHTML = locations.map((location, index) => `
            <button type="button"
                    class="location-result"
                    data-index="${index}">
                ${escapeRideHTML(location.display_name)}
            </button>
        `).join("");

        container.querySelectorAll(".location-result")
            .forEach(button => {
                button.addEventListener("click", () => {
                    const item = locations[Number(button.dataset.index)];

                    const location = {
                        name: item.display_name,
                        lat: Number(item.lat),
                        lon: Number(item.lon)
                    };

                    selectNearbyLocation(type, location);
                    container.innerHTML = "";
                });
            });

    } catch (error) {
        container.textContent = error.message;
    }
}

function selectNearbyLocation(type, location) {
    const marker = type === "pickup" ? pickupMarker : dropMarker;

    if (marker) {
        nearbyMap.removeLayer(marker);
    }

    const newMarker = L.marker([
        location.lat,
        location.lon
    ]).addTo(nearbyMap);

    newMarker.bindPopup(escapeRideHTML(location.name));

    if (type === "pickup") {
        pickupMarker = newMarker;
        selectedPickup = location;

        document.getElementById("pickup-selected").textContent =
            `Selected: ${location.name}`;
    } else {
        dropMarker = newMarker;
        selectedDrop = location;

        document.getElementById("drop-selected").textContent =
            `Selected: ${location.name}`;
    }

    const points = [];

    if (selectedPickup) {
        points.push([selectedPickup.lat, selectedPickup.lon]);
    }

    if (selectedDrop) {
        points.push([selectedDrop.lat, selectedDrop.lon]);
    }

    if (points.length === 2) {
        nearbyMap.fitBounds(points, { padding: [40, 40] });
    } else {
        nearbyMap.setView(points[0], 13);
    }
}

function initializeNearbySearch() {
    initializeNearbyMap();

    document.getElementById("search-pickup")
        .addEventListener("click", () => searchNearbyLocation("pickup"));

    document.getElementById("search-drop")
        .addEventListener("click", () => searchNearbyLocation("drop"));

    document.getElementById("nearby-search-form")
        .addEventListener("submit", searchNearbyRides);
}

async function searchNearbyRides(event) {
    event.preventDefault();

    const message = document.getElementById("nearby-message");
    const results = document.getElementById("nearby-results");
    const count = document.getElementById("nearby-count");

    if (!selectedPickup || !selectedDrop) {
        message.textContent = "Select both pickup and drop-off locations.";
        return;
    }

    if (
        selectedPickup.lat === selectedDrop.lat &&
        selectedPickup.lon === selectedDrop.lon
    ) {
        message.textContent = "Pickup and drop-off must be different.";
        return;
    }

    message.textContent = "Finding suitable routes...";
    results.innerHTML = "";
    count.textContent = "";

    if (proposedRouteLayer) {
        nearbyMap.removeLayer(proposedRouteLayer);
        proposedRouteLayer = null;
    }

    const params = new URLSearchParams({
        pickup_lat: selectedPickup.lat,
        pickup_lon: selectedPickup.lon,
        drop_lat: selectedDrop.lat,
        drop_lon: selectedDrop.lon,
        radius_km: document.getElementById("nearby-radius").value,
        max_detour_km: document.getElementById("nearby-detour").value
    });

    try {
        const response = await fetch(
            `/api/rides/match-nearby?${params.toString()}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Nearby search failed.");
        }

        const matches = data.matches || [];

        message.textContent = "";
        count.textContent = `${data.count} nearby match(es) found`;

        if (!matches.length) {
            results.innerHTML = `
                <div class="rides-empty">
                    No suitable routes found. Try increasing the
                    detour limit or changing your locations.
                </div>
            `;
            return;
        }

        results.innerHTML = matches.map((ride, index) => `
            <article class="nearby-result">
                <div class="nearby-result-heading">
                    <div>
                        <span class="ride-location-label">DRIVER ROUTE</span>
                        <h3>
                            ${escapeRideHTML(ride.source)}
                            <span class="route-arrow">→</span>
                            ${escapeRideHTML(ride.destination)}
                        </h3>
                        <p class="item-meta">
                            ${formatRideDate(ride.departure_time)}
                        </p>
                    </div>

                    <span class="detour-badge">
                        +${Number(ride.detour_km).toFixed(2)} km detour
                    </span>
                </div>

                <div class="nearby-metrics">
                    <div>
                        <span>Driver</span>
                        <strong>${escapeRideHTML(ride.driver_name)}</strong>
                    </div>

                    <div>
                        <span>Available seats</span>
                        <strong>${Number(ride.available_seats)}</strong>
                    </div>

                    <div>
                        <span>Price per seat</span>
                        <strong>₹${Number(ride.price_per_seat).toFixed(2)}</strong>
                    </div>

                    <div>
                        <span>Original route</span>
                        <strong>${Number(ride.original_route_km).toFixed(2)} km</strong>
                    </div>

                    <div>
                        <span>Modified route</span>
                        <strong>${Number(ride.modified_route_km).toFixed(2)} km</strong>
                    </div>
                </div>

                <div class="nearby-stop-info">
                    <p>
                        <strong>Pickup:</strong>
                        ${escapeRideHTML(ride.matched_pickup_stop)}
                        (${Number(ride.pickup_distance_km).toFixed(2)} km away)
                    </p>

                    <p>
                        <strong>Drop-off:</strong>
                        ${escapeRideHTML(ride.matched_drop_stop)}
                        (${Number(ride.drop_distance_km).toFixed(2)} km away)
                    </p>
                </div>

                <div class="nearby-result-footer">
                    <span class="insertion-info">
                        ${ride.pickup_stop_inserted ? "New pickup stop" : "Existing pickup stop"}
                        ·
                        ${ride.drop_stop_inserted ? "New drop-off stop" : "Existing drop-off stop"}
                    </span>

                    <button type="button"
                            class="small-action show-route-button"
                            data-index="${index}">
                        Show proposed route
                    </button>

                    <a href="/rides/${Number(ride.ride_id)}"
                       class="ride-view-link">
                        View ride
                    </a>
                </div>
            </article>
        `).join("");

        results.querySelectorAll(".show-route-button")
            .forEach(button => {
                button.addEventListener("click", () => {
                    displayProposedRoute(matches[Number(button.dataset.index)]);
                });
            });

    } catch (error) {
        message.textContent = error.message;
    }
}

function displayProposedRoute(ride) {
    if (proposedRouteLayer) {
        nearbyMap.removeLayer(proposedRouteLayer);
    }

    const coordinates = ride.proposed_route.map(point => [
        Number(point.latitude),
        Number(point.longitude)
    ]);

    if (!coordinates.length) return;

    proposedRouteLayer = L.polyline(coordinates, {
        color: "#0d9488",
        weight: 4
    }).addTo(nearbyMap);

    nearbyMap.fitBounds(proposedRouteLayer.getBounds(), {
        padding: [35, 35]
    });

    proposedRouteLayer.bindPopup(
        `Ride #${ride.ride_id} proposed route`
    );

    document.getElementById("nearby-map")
        .scrollIntoView({ behavior: "smooth", block: "center" });
}

