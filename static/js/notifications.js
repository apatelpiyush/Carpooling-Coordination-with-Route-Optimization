
document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("notification-toggle");
    const panel = document.getElementById("notification-panel");
    const list = document.getElementById("notification-list");
    const countBadge = document.getElementById("notification-count");
    const refreshButton = document.getElementById("refresh-notifications");

    if (!toggle || !panel || !list || !countBadge) return;

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

    async function loadNotifications() {
        try {
            const response = await fetch("/api/notifications");
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Unable to load notifications");
            }

            const notifications = data.notifications || [];
            const unread = data.unread_count || 0;

            countBadge.textContent = unread > 99 ? "99+" : unread;
            countBadge.hidden = unread === 0;

            if (!notifications.length) {
                list.innerHTML =
                    '<p class="notification-empty">No notifications yet.</p>';
                return;
            }

            list.innerHTML = notifications.map(n => `
                <article class="notification-item ${n.is_read ? "" : "unread"}"
                         data-id="${Number(n.notification_id)}"
                         data-read="${n.is_read}">
                    <strong>${safeHTML(n.title)}</strong>
                    <p>${safeHTML(n.message)}</p>
                    <small>${safeHTML(displayDate(n.created_at))}</small>
                </article>
            `).join("");

        } catch (error) {
            list.innerHTML =
                `<p class="notification-empty">${safeHTML(error.message)}</p>`;
        }
    }

    toggle.addEventListener("click", () => {
        const opening = panel.hidden;
        panel.hidden = !opening;
        toggle.setAttribute("aria-expanded", String(opening));

        if (opening) loadNotifications();
    });

    refreshButton?.addEventListener("click", loadNotifications);

    list.addEventListener("click", async event => {
        const item = event.target.closest(".notification-item");

        if (!item || item.dataset.read === "true") return;

        const notificationId = Number(item.dataset.id);

        try {
            const response = await fetch(
                `/api/notifications/${notificationId}/read`,
                { method: "POST" }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Unable to mark as read");
            }

            await loadNotifications();

        } catch (error) {
            alert(error.message);
        }
    });

    document.addEventListener("click", event => {
        if (!event.target.closest(".notification-wrapper")) {
            panel.hidden = true;
            toggle.setAttribute("aria-expanded", "false");
        }
    });

    loadNotifications();

    // Refresh unread count every 30 seconds.
    setInterval(loadNotifications, 30000);
});
