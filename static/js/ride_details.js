
let currentRide = null;
let detailsMap = null;
let pickupLocation = null;
let dropLocation = null;

let pickupMarker = null;
let dropMarker = null;

function escapeDetailsHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

function formatDetailsDate(value) {
    return new Date(value).toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short"
    });
}

    function initializeDetailsMap(stops) {
    const coordinates = stops.map(stop => [
        stop.latitude,
        stop.longitude
    ]);

    detailsMap = L.map("ride-details-map");

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 19
    }).addTo(detailsMap);

    const route = L.polyline(coordinates, {
        color: "#0d9488",
        weight: 4
    }).addTo(detailsMap);

    stops.forEach((stop, index) => {
        L.marker([stop.latitude, stop.longitude])
            .addTo(detailsMap)
            .bindPopup(
                `${index + 1}. ${escapeDetailsHTML(stop.name)}`
            );
    });

    setTimeout(() => {
        detailsMap.invalidateSize();
        detailsMap.fitBounds(route.getBounds(), {
            padding: [45, 45],
            maxZoom: 9
        });
    }, 200);
}

async function loadRideDetails() {
    const rideId = document.querySelector(".ride-details-page")
        .dataset.rideId;

    const loading = document.getElementById("ride-loading");
    const error = document.getElementById("ride-error");

    try {
        const response = await fetch(
            `/api/rides/${rideId}/details`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Could not load ride details.");
        }

        currentRide = data.ride;

        document.getElementById("ride-route-title").textContent =
            `${currentRide.source} → ${currentRide.destination}`;

        document.getElementById("ride-departure").textContent =
            formatDetailsDate(currentRide.departure_time);

        document.getElementById("driver-name").textContent =
            currentRide.driver_name;

        const vehicle = currentRide.vehicle;

        document.getElementById("vehicle-name").textContent =
            `${vehicle.make} ${vehicle.model}`;

        document.getElementById("vehicle-plate").textContent =
            vehicle.plate_number;

        document.getElementById("vehicle-color").textContent =
            vehicle.color || "Not specified";

        document.getElementById("vehicle-capacity").textContent =
            `${vehicle.capacity} seats`;

        document.getElementById("ride-price").textContent =
            `₹${Number(currentRide.price_per_seat).toFixed(2)}`;

        document.getElementById("ride-seats").textContent =
            currentRide.available_seats;

        document.getElementById("booking-seats").max =
            currentRide.available_seats;

        document.getElementById("ride-stops").innerHTML =
            currentRide.stops.map((stop, index) => `
                <div class="route-stop">
                    <span class="route-stop-number">${index + 1}</span>
                    <span>${escapeDetailsHTML(stop.name)}</span>
                </div>
            `).join("");

        initializeDetailsMap(currentRide.stops);

        loading.hidden = true;
        document.getElementById("ride-content").hidden = false;

        updateBookingTotal();

        if (
            currentRide.status !== "scheduled" ||
            currentRide.available_seats < 1 ||
            new Date(currentRide.departure_time) <= new Date()
        ) {
            document.getElementById("confirm-booking").disabled = true;
            document.getElementById("booking-message").textContent =
                "This ride is no longer available for booking.";
        }

    } catch (err) {
        loading.hidden = true;
        error.textContent = err.message;
    }
}

async function searchBookingLocation(type) {
    const isPickup = type === "pickup";

    const input = document.getElementById(
        isPickup ? "booking-pickup" : "booking-drop"
    );

    const results = document.getElementById(
        isPickup ? "booking-pickup-results" : "booking-drop-results"
    );

    const query = input.value.trim();

    if (!query) {
        results.textContent = "Enter a location first.";
        return;
    }

    results.textContent = "Searching...";

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
            results.textContent = "No locations found.";
            return;
        }

        results.innerHTML = locations.map((location, index) => `
            <button type="button"
                    class="location-result"
                    data-index="${index}">
                ${escapeDetailsHTML(location.display_name)}
            </button>
        `).join("");

        results.querySelectorAll(".location-result")
            .forEach(button => {
                button.addEventListener("click", () => {
                    const item = locations[Number(button.dataset.index)];

                    const selected = {
                        name: item.display_name,
                        lat: Number(item.lat),
                        lon: Number(item.lon)
                    };

                    if (isPickup) {
                        pickupLocation = selected;

                        document.getElementById(
                            "booking-pickup-selected"
                        ).textContent = `Selected: ${selected.name}`;
                    } else {
                        dropLocation = selected;

                        document.getElementById(
                            "booking-drop-selected"
                        ).textContent = `Selected: ${selected.name}`;
                    }

                    showBookingMarker(type, selected);
                    results.innerHTML = "";
                });
            });

    } catch (err) {
        results.textContent = err.message;
    }
}

function showBookingMarker(type, location) {
    const isPickup = type === "pickup";
    const existingMarker = isPickup ? pickupMarker : dropMarker;

    if (existingMarker) {
        detailsMap.removeLayer(existingMarker);
    }

    const marker = L.marker([
        location.lat,
        location.lon
    ]).addTo(detailsMap);

    marker.bindPopup(escapeDetailsHTML(location.name));

    if (isPickup) {
        pickupMarker = marker;
    } else {
        dropMarker = marker;
    }

    const points = currentRide.stops.map(stop => [
        stop.latitude,
        stop.longitude
    ]);

    points.push([location.lat, location.lon]);

    detailsMap.fitBounds(points, { padding: [35, 35] });
}

function updateBookingTotal() {
    if (!currentRide) return;

    const seats = Number(
        document.getElementById("booking-seats").value
    );

    const total = seats * Number(currentRide.price_per_seat);

    document.getElementById("booking-total").textContent =
        Number.isFinite(total) && total >= 0
            ? `₹${total.toFixed(2)}`
            : "₹0.00";
}

async function submitBooking(event) {
    event.preventDefault();

    const message = document.getElementById("booking-message");
    const button = document.getElementById("confirm-booking");

    const seats = Number(
        document.getElementById("booking-seats").value
    );

    if (!pickupLocation || !dropLocation) {
        message.textContent =
            "Select both pickup and drop-off locations.";
        return;
    }

    if (
        pickupLocation.lat === dropLocation.lat &&
        pickupLocation.lon === dropLocation.lon
    ) {
        message.textContent =
            "Pickup and drop-off must be different.";
        return;
    }

    if (
        !Number.isInteger(seats) ||
        seats < 1 ||
        seats > currentRide.available_seats
    ) {
        message.textContent = "Select a valid number of seats.";
        return;
    }

    const payload = {
        ride_id: currentRide.ride_id,
        seats_booked: seats,
        pickup_name: pickupLocation.name,
        pickup_lat: pickupLocation.lat,
        pickup_lon: pickupLocation.lon,
        drop_name: dropLocation.name,
        drop_lat: dropLocation.lat,
        drop_lon: dropLocation.lon,
        max_detour_km: Number(
            document.getElementById("booking-detour").value
        )
    };

    button.disabled = true;
    message.textContent = "Processing your booking...";

    try {
        const response = await fetch("/api/bookings", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Booking failed.");
        }

        message.textContent =
            `Booking confirmed! Booking ID: ${data.booking.booking_id}`;

        message.classList.add("booking-success");

        currentRide.available_seats -= seats;

        document.getElementById("ride-seats").textContent =
            currentRide.available_seats;

        document.getElementById("booking-seats").max =
            currentRide.available_seats;

        document.getElementById("booking-seats").value = 1;

        updateBookingTotal();

        if (currentRide.available_seats < 1) {
            button.disabled = true;
            message.textContent += " No seats remain.";
        } else {
            button.disabled = false;
        }

    } catch (err) {
        message.textContent = err.message;
        button.disabled = false;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("booking-pickup-search")
        .addEventListener("click", () => {
            searchBookingLocation("pickup");
        });

    document.getElementById("booking-drop-search")
        .addEventListener("click", () => {
            searchBookingLocation("drop");
        });

    document.getElementById("booking-seats")
        .addEventListener("input", updateBookingTotal);

    document.getElementById("booking-form")
        .addEventListener("submit", submitBooking);

    loadRideDetails();
});
