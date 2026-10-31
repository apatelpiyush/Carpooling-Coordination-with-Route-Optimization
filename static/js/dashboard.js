
document.addEventListener("DOMContentLoaded", loadDashboard);

async function apiGet(url) {
    const response = await fetch(url);

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Unable to load dashboard data.");
    }

    return data;
}

function formatDate(value) {
    if (!value) return "Date unavailable";

    const date = new Date(value);

    return date.toLocaleString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    });
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

function showError(message) {
    const element = document.getElementById("dashboard-error");
    element.textContent = message;
    element.hidden = false;
}

function renderEmpty(containerId, message) {
    document.getElementById(containerId).innerHTML =
        `<div class="empty-state">${escapeHTML(message)}</div>`;
}

async function loadDashboard() {
    try {
        const result = await apiGet("/auth/me");
        const user = result.user;

        document.getElementById("user-name").textContent = user.name;
        document.getElementById("user-role").textContent =
            user.is_driver ? "Driver account" : "Rider account";

        document.getElementById("dashboard-subtitle").textContent =
            user.is_driver
                ? "Manage your vehicles and published rides."
                : "Find rides and manage your bookings.";

        if (user.is_driver) {
            document.getElementById("driver-section").hidden = false;
            setupVehicleForm();
            setupRideForm();
            await loadDriverDashboard();
        }else {
            document.getElementById("rider-section").hidden = false;
            await loadRiderDashboard();
        }

    } catch (error) {
        showError(error.message);
    }
}

async function loadDriverDashboard() {
    const [rideData, vehicleData] = await Promise.all([
        apiGet("/api/my-rides"),
        apiGet("/api/vehicles")
    ]);

    const rides = rideData.rides || [];
    const vehicles = vehicleData.vehicles || [];

    const upcoming = rides.filter(
        ride => new Date(ride.departure_time) > new Date()
    );

    const totalSeats = rides.reduce(
        (sum, ride) => sum + Number(ride.available_seats), 0
    );

    document.getElementById("dashboard-stats").innerHTML = `
        <div class="stat-card">
            <span class="stat-label">Published rides</span>
            <strong>${rides.length}</strong>
        </div>
        <div class="stat-card">
            <span class="stat-label">Upcoming rides</span>
            <strong>${upcoming.length}</strong>
        </div>
        <div class="stat-card">
            <span class="stat-label">Available seats</span>
            <strong>${totalSeats}</strong>
        </div>
        <div class="stat-card">
            <span class="stat-label">Registered vehicles</span>
            <strong>${vehicles.length}</strong>
        </div>
    `;

    renderDriverRides(rides);
    renderVehicles(vehicles);
}

function renderDriverRides(rides) {
    const container = document.getElementById("driver-rides");

    if (!rides.length) {
        renderEmpty("driver-rides", "You haven't published any rides yet.");
        return;
    }

    container.innerHTML = rides.map(ride => `
        <article class="dashboard-item">
            <div class="item-main">
                <div class="route-name">
                    ${escapeHTML(ride.source)}
                    <span class="route-arrow">→</span>
                    ${escapeHTML(ride.destination)}
                </div>
                <p class="item-meta">${formatDate(ride.departure_time)}</p>
            </div>

            <div class="item-detail">
                <span class="item-detail-label">Available seats</span>
                <strong>${Number(ride.available_seats)}</strong>
            </div>

            <div class="item-detail">
                <span class="item-detail-label">Price per seat</span>
                <strong>₹${Number(ride.price_per_seat).toFixed(2)}</strong>
            </div>

            <span class="status-label">
                ${escapeHTML(ride.status)}
            </span>
        </article>
    `).join("");
}

function renderVehicles(vehicles) {
    const container = document.getElementById("driver-vehicles");

    if (!vehicles.length) {
        renderEmpty("driver-vehicles", "No vehicles registered yet.");
        return;
    }

    container.innerHTML = vehicles.map(vehicle => `
        <article class="dashboard-item">
            <div class="item-main">
                <div class="route-name">
                    ${escapeHTML(vehicle.make)} ${escapeHTML(vehicle.model)}
                </div>
                <p class="item-meta">
                    ${escapeHTML(vehicle.plate_number)}
                </p>
            </div>

            <div class="item-detail">
                <span class="item-detail-label">Capacity</span>
                <strong>${Number(vehicle.capacity)} seats</strong>
            </div>

            <div class="item-detail">
                <span class="item-detail-label">Color</span>
                <strong>${escapeHTML(vehicle.color || "Not specified")}</strong>
            </div>
        </article>
    `).join("");
}

async function loadRiderDashboard() {
    const [bookingData, rideData] = await Promise.all([
        apiGet("/api/bookings"),
        apiGet("/api/rides")
    ]);

    const bookings = bookingData.bookings || [];
    const rides = rideData.rides || [];

    const activeBookings = bookings.filter(
        booking => booking.booking_status === "confirmed"
    );

    document.getElementById("dashboard-stats").innerHTML = `
        <div class="stat-card">
            <span class="stat-label">Total bookings</span>
            <strong>${bookings.length}</strong>
        </div>
        <div class="stat-card">
            <span class="stat-label">Confirmed bookings</span>
            <strong>${activeBookings.length}</strong>
        </div>
        <div class="stat-card">
            <span class="stat-label">Available rides</span>
            <strong>${rides.length}</strong>
        </div>
    `;

    renderBookings(bookings);
    renderAvailableRides(rides);
}

function renderBookings(bookings) {
    const container = document.getElementById("rider-bookings");

    if (!bookings.length) {
        renderEmpty("rider-bookings", "You haven't booked any rides yet.");
        return;
    }

    container.innerHTML = bookings.map(booking => `
        <article class="dashboard-item">
            <div class="item-main">
                <div class="route-name">
                    ${escapeHTML(booking.source)}
                    <span class="route-arrow">→</span>
                    ${escapeHTML(booking.destination)}
                </div>
                <p class="item-meta">
                    ${formatDate(booking.departure_time)}
                    · Driver: ${escapeHTML(booking.driver_name)}
                </p>
            </div>

            <div class="item-detail">
                <span class="item-detail-label">Seats booked</span>
                <strong>${Number(booking.seats_booked)}</strong>
            </div>

            <span class="status-label">
                ${escapeHTML(booking.booking_status)}
            </span>
        </article>
    `).join("");
}

function renderAvailableRides(rides) {
    const container = document.getElementById("available-rides");

    const upcoming = rides.filter(
        ride => new Date(ride.departure_time) > new Date()
    );

    if (!upcoming.length) {
        renderEmpty("available-rides", "No upcoming rides are currently available.");
        return;
    }

    container.innerHTML = upcoming.slice(0, 5).map(ride => `
        <article class="dashboard-item">
            <div class="item-main">
                <div class="route-name">
                    ${escapeHTML(ride.source)}
                    <span class="route-arrow">→</span>
                    ${escapeHTML(ride.destination)}
                </div>
                <p class="item-meta">
                    ${formatDate(ride.departure_time)}
                    · Driver: ${escapeHTML(ride.driver_name)}
                </p>
            </div>

            <div class="item-detail">
                <span class="item-detail-label">Available seats</span>
                <strong>${Number(ride.available_seats)}</strong>
            </div>

            <div class="item-detail">
                <span class="item-detail-label">Price per seat</span>
                <strong>₹${Number(ride.price_per_seat).toFixed(2)}</strong>
            </div>

            <a href="/rides" class="small-action">View ride</a>
        </article>
    `).join("");
}


function setupVehicleForm() {
    const form = document.getElementById("vehicle-form");

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const message = document.getElementById("vehicle-message");
        message.textContent = "Adding vehicle...";

        const vehicle = {
            make: document.getElementById("vehicle-make").value.trim(),
            model: document.getElementById("vehicle-model").value.trim(),
            plate_number: document.getElementById("vehicle-plate").value.trim(),
            capacity: Number(document.getElementById("vehicle-capacity").value),
            color: document.getElementById("vehicle-color").value.trim() || null
        };

        try {
            const response = await fetch("/api/vehicles", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(vehicle)
            });

            const text = await response.text();

            let data;

            try {
                data = JSON.parse(text);
            } catch {
                throw new Error(
                    "Server returned an unexpected response. Check the Flask terminal."
                );
            }

            if (!response.ok) {
                throw new Error(data.error || "Unable to add vehicle.");
            }

            message.textContent = "Vehicle added successfully.";
            form.reset();

            const vehicleData = await apiGet("/api/vehicles");
            renderVehicles(vehicleData.vehicles || []);

            // Refresh dashboard statistics too.
            const rideData = await apiGet("/api/my-rides");
            const rides = rideData.rides || [];

            const upcoming = rides.filter(
                ride => new Date(ride.departure_time) > new Date()
            );

            const totalSeats = rides.reduce(
                (sum, ride) => sum + Number(ride.available_seats), 0
            );

            document.getElementById("dashboard-stats").innerHTML = `
                <div class="stat-card">
                    <span class="stat-label">Published rides</span>
                    <strong>${rides.length}</strong>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Upcoming rides</span>
                    <strong>${upcoming.length}</strong>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Available seats</span>
                    <strong>${totalSeats}</strong>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Registered vehicles</span>
                    <strong>${vehicleData.vehicles.length}</strong>
                </div>
            `;

        } catch (error) {
            message.textContent = error.message;
        }
    });
}
