
let allBookings = [];
let activeFilter = "all";
const searchInput = document.getElementById("booking-search");

const bookingsList = document.getElementById("bookings-list");
const bookingsMessage = document.getElementById("bookings-message");


function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}


function formatDate(value) {
    return new Date(value).toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short"
    });
}


// Filter bookings based on selected status
function filterBookings() {
    const searchTerm = searchInput.value.trim().toLowerCase();

    const filtered = allBookings.filter(booking => {

        // Status filter
        const matchesStatus =
            activeFilter === "all" ||
            booking.booking_status.toLowerCase() === activeFilter;

        // Search filter
        const searchableText = [
            booking.booking_id,
            booking.driver_name,
            booking.source,
            booking.destination
        ].join(" ").toLowerCase();

        const matchesSearch = searchableText.includes(searchTerm);

        return matchesStatus && matchesSearch;
    });

    renderBookings(filtered);
}


// Update booking cards
function renderBookings(bookings) {

    if (bookings.length === 0) {
        bookingsList.innerHTML = `
            <div class="empty-bookings">
                No ${activeFilter === "all" ? "" : activeFilter + " "}
                bookings found.
            </div>
        `;
        return;
    }

    bookingsList.innerHTML = bookings.map(booking => {
        const status = booking.booking_status.toLowerCase();

        return `
            <article class="booking-card">

                <div class="booking-card-top">
                    <div>
                        <span class="booking-id">
                            BOOKING #${escapeHTML(booking.booking_id)}
                        </span>

                        <h2>
                            ${escapeHTML(booking.source)}
                            <span>→</span>
                            ${escapeHTML(booking.destination)}
                        </h2>
                    </div>

                    <span class="booking-status ${escapeHTML(status)}">
                        ${escapeHTML(status)}
                    </span>
                </div>

                <div class="booking-details">

                    <div>
                        <span>Driver</span>
                        <strong>${escapeHTML(booking.driver_name)}</strong>
                    </div>

                    <div>
                        <span>Departure</span>
                        <strong>${escapeHTML(formatDate(booking.departure_time))}</strong>
                    </div>

                    <div>
                        <span>Seats booked</span>
                        <strong>${escapeHTML(booking.seats_booked)}</strong>
                    </div>

                    <div>
                        <span>Booked on</span>
                        <strong>${escapeHTML(formatDate(booking.booked_at))}</strong>
                    </div>

                </div>

                <div class="booking-card-footer">
                    ${
                        status === "confirmed"
                        ? `<button class="cancel-booking-button"
                                   onclick="cancelBooking(${Number(booking.booking_id)})">
                                Cancel booking
                           </button>`
                        : '<span class="cancelled-note">This booking is no longer active.</span>'
                    }
                </div>

            </article>
        `;
    }).join("");
}


// Fetch bookings from backend
async function loadBookings() {

    bookingsMessage.textContent = "Loading bookings...";
    bookingsList.innerHTML = "";

    try {
        const response = await fetch("/api/bookings");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Could not load bookings");
        }

        allBookings = data.bookings || [];

        // Statistics always use ALL bookings
        document.getElementById("total-bookings").textContent =
            allBookings.length;

        document.getElementById("confirmed-bookings").textContent =
            allBookings.filter(b => b.booking_status === "confirmed").length;

        document.getElementById("cancelled-bookings").textContent =
            allBookings.filter(b => b.booking_status === "cancelled").length;

        bookingsMessage.textContent = "";

        // Display according to currently selected filter
        filterBookings();

    } catch (error) {
        bookingsMessage.textContent = error.message;
    }
}


// Cancel a booking
async function cancelBooking(bookingId) {

    if (!confirm("Are you sure you want to cancel this booking?")) {
        return;
    }

    try {
        const response = await fetch(
            `/api/bookings/${bookingId}/cancel`,
            { method: "POST" }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Cancellation failed");
        }

        bookingsMessage.textContent =
            data.message || "Booking cancelled successfully.";

        await loadBookings();

    } catch (error) {
        bookingsMessage.textContent = error.message;
    }
}


// Filter button event listeners
document.querySelectorAll(".filter-btn").forEach(button => {

    button.addEventListener("click", () => {

        activeFilter = button.dataset.filter;

        document.querySelectorAll(".filter-btn").forEach(btn => {
            btn.classList.toggle("active", btn === button);
        });

        filterBookings();
    });

});


searchInput.addEventListener("input", filterBookings);
// Initial loading
loadBookings();

