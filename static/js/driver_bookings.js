
let allBookings = [];
let activeFilter = "all";

const list = document.getElementById("driver-bookings-list");
const message = document.getElementById("driver-bookings-message");


function safeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}


function displayDate(value) {
    return new Date(value).toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short"
    });
}


// Filter bookings by status
function filterDriverBookings() {

    const filtered = activeFilter === "all"
        ? allBookings
        : allBookings.filter(b =>
            b.booking_status.toLowerCase() === activeFilter
        );

    renderDriverBookings(filtered);
}


// Render passenger booking cards
function renderDriverBookings(bookings) {

    if (bookings.length === 0) {
        list.innerHTML = `
            <div class="empty-bookings">
                No ${activeFilter === "all" ? "" : activeFilter + " "}
                passenger bookings found.
            </div>
        `;
        return;
    }

    list.innerHTML = bookings.map(b => {

        const status = b.booking_status.toLowerCase();

        return `
            <article class="passenger-booking-card">

                <div class="passenger-card-header">
                    <div>
                        <span class="booking-id">
                            BOOKING #${safeHTML(b.booking_id)}
                            · RIDE #${safeHTML(b.ride_id)}
                        </span>

                        <h2>
                            ${safeHTML(b.source)}
                            <span>→</span>
                            ${safeHTML(b.destination)}
                        </h2>
                    </div>

                    <span class="booking-status ${safeHTML(status)}">
                        ${safeHTML(status)}
                    </span>
                </div>

                <div class="passenger-information">

                    <div>
                        <span>Passenger</span>
                        <strong>${safeHTML(b.passenger_name)}</strong>
                    </div>

                    <div>
                        <span>Seats booked</span>
                        <strong>${safeHTML(b.seats_booked)}</strong>
                    </div>

                    <div>
                        <span>Departure</span>
                        <strong>${safeHTML(displayDate(b.departure_time))}</strong>
                    </div>

                    <div>
                        <span>Booked on</span>
                        <strong>${safeHTML(displayDate(b.booked_at))}</strong>
                    </div>

                    <div>
                        <span>Email</span>
                        <strong>${safeHTML(b.passenger_email)}</strong>
                    </div>

                    <div>
                        <span>Phone</span>
                        <strong>${safeHTML(b.passenger_phone)}</strong>
                    </div>

                </div>

                <div class="passenger-route-details">
                    <p>
                        <strong>Pickup:</strong>
                        ${safeHTML(b.pickup_location || "Not available")}
                    </p>

                    <p>
                        <strong>Drop-off:</strong>
                        ${safeHTML(b.drop_location || "Not available")}
                    </p>
                </div>

            </article>
        `;

    }).join("");
}


// Fetch driver's passenger bookings
async function loadDriverBookings() {

    message.textContent = "Loading passenger bookings...";
    list.innerHTML = "";

    try {
        const response = await fetch("/api/driver/bookings");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Could not load bookings");
        }

        allBookings = data.bookings || [];

        // Statistics always show all bookings
        document.getElementById("driver-total").textContent =
            allBookings.length;

        document.getElementById("driver-confirmed").textContent =
            allBookings.filter(b => b.booking_status === "confirmed").length;

        document.getElementById("driver-cancelled").textContent =
            allBookings.filter(b => b.booking_status === "cancelled").length;

        message.textContent = "";

        // Display bookings using selected filter
        filterDriverBookings();

    } catch (error) {
        message.textContent = error.message;
    }
}


// Filter button event listeners
document.querySelectorAll(".filter-btn").forEach(button => {

    button.addEventListener("click", () => {

        activeFilter = button.dataset.filter;

        document.querySelectorAll(".filter-btn").forEach(btn => {
            btn.classList.toggle("active", btn === button);
        });

        filterDriverBookings();
    });

});


// Initial loading
loadDriverBookings();

