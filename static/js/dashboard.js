
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
    currentDriverRides = rides;
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

    container.innerHTML = rides.map(ride => {
        const hasBookings = Number(ride.confirmed_bookings) > 0;
        const isScheduled = ride.status === "scheduled";
        const canManage = isScheduled && !hasBookings;

        return `
            <article class="dashboard-item driver-ride-item"
                     data-ride-id="${Number(ride.ride_id)}">

                <div class="item-main">
                    <div class="route-name">
                        ${escapeHTML(ride.source)}
                        <span class="route-arrow">→</span>
                        ${escapeHTML(ride.destination)}
                    </div>
                    <p class="item-meta">
                        ${formatDate(ride.departure_time)}
                        · Ride #${Number(ride.ride_id)}
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

                <div class="ride-status-actions">
                    <span class="status-label">
                        ${escapeHTML(ride.status)}
                    </span>

                    ${
                        canManage
                        ? `
                            <div class="ride-actions">
                                <button class="small-action edit-ride-btn"
                                        data-id="${Number(ride.ride_id)}">
                                    Edit
                                </button>
                                <button class="small-action cancel-ride-btn"
                                        data-id="${Number(ride.ride_id)}">
                                    Cancel
                                </button>
                            </div>
                        `
                        : hasBookings && isScheduled
                        ? `<span class="ride-restriction">
                               ${Number(ride.confirmed_bookings)} confirmed booking(s) — editing and cancellation unavailable
                           </span>`
                        : ""
                    }
                </div>

                <div class="ride-edit-area" id="ride-edit-${Number(ride.ride_id)}"></div>
            </article>
        `;
    }).join("");

    setupDriverRideActions();
}

function setupDriverRideActions() {
    const container = document.getElementById("driver-rides");

    if (container.dataset.actionsBound === "true") return;
    container.dataset.actionsBound = "true";

    container.addEventListener("click", async event => {
        const editButton = event.target.closest(".edit-ride-btn");
        const cancelButton = event.target.closest(".cancel-ride-btn");

        if (editButton) {
            const rideId = Number(editButton.dataset.id);
            const card = editButton.closest(".driver-ride-item");
            const ride = currentDriverRides.find(
                item => Number(item.ride_id) === rideId
            );

            if (!ride) return;

            const area = card.querySelector(".ride-edit-area");

            area.innerHTML = `
                <form class="ride-edit-form" data-id="${rideId}">
                    <label>
                        Departure time
                        <input type="datetime-local"
                               name="departure_time"
                               value="${escapeHTML(ride.departure_time.slice(0, 16))}"
                               required>
                    </label>

                    <label>
                        Available seats
                        <input type="number" name="available_seats"
                               min="1" max="8"
                               value="${Number(ride.available_seats)}" required>
                    </label>

                    <label>
                        Price per seat (₹)
                        <input type="number" name="price_per_seat"
                               min="0" step="0.01"
                               value="${Number(ride.price_per_seat)}" required>
                    </label>

                    <div class="ride-edit-actions">
                        <button type="submit" class="small-action">Save changes</button>
                        <button type="button" class="small-action close-edit-btn">Close</button>
                    </div>
                    <p class="ride-action-message" role="status"></p>
                </form>
            `;
            return;
        }

        if (event.target.closest(".close-edit-btn")) {
            event.target.closest(".ride-edit-area").innerHTML = "";
            return;
        }

        if (cancelButton) {
            const rideId = Number(cancelButton.dataset.id);

            if (!confirm(`Cancel ride #${rideId}? This action cannot be undone.`)) {
                return;
            }

            cancelButton.disabled = true;

            try {
                await apiRequest(`/api/rides/${rideId}/cancel`, "POST");
                await loadDriverDashboard();
            } catch (error) {
                alert(error.message);
                cancelButton.disabled = false;
            }
        }
    });

    container.addEventListener("submit", async event => {
        const form = event.target.closest(".ride-edit-form");
        if (!form) return;

        event.preventDefault();

        const rideId = Number(form.dataset.id);
        const message = form.querySelector(".ride-action-message");
        const submitButton = form.querySelector('[type="submit"]');

        const payload = {
            departure_time: form.elements.departure_time.value,
            available_seats: Number(form.elements.available_seats.value),
            price_per_seat: Number(form.elements.price_per_seat.value)
        };

        submitButton.disabled = true;
        message.textContent = "Saving changes...";

        try {
            await apiRequest(`/api/rides/${rideId}`, "PUT", payload);
            await loadDriverDashboard();
        } catch (error) {
            message.textContent = error.message;
            submitButton.disabled = false;
        }
    });
}

let currentDriverRides = [];

async function apiRequest(url, method, body = null) {
    const options = {
        method,
        headers: {}
    };

    if (body !== null) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Request failed.");
    }

    return data;
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
