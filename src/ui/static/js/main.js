document.addEventListener("DOMContentLoaded", () => {
    // UI Elements
    const elements = {
        dateChip: document.getElementById("date-chip"),
        themeList: document.getElementById("theme-list"),
        weeklyNote: document.getElementById("weekly-note"),
        quotesGrid: document.getElementById("quotes-grid"),
        actionList: document.getElementById("action-list"),
        feeScenario: document.getElementById("fee-scenario"),
        feeBulletsList: document.getElementById("fee-bullets-list"),


        statusBadge: document.getElementById("status-badge"),
        statusText: document.getElementById("status-text"),
        emailInput: document.getElementById("email-input"),
        addEmailBtn: document.getElementById("add-email-btn"),
        recipientChips: document.getElementById("recipient-chips"),
        btnApprove: document.getElementById("btn-approve"),
        btnReject: document.getElementById("btn-reject"),
        modal: document.getElementById("confirm-modal"),
        modalCancel: document.getElementById("modal-cancel"),
        modalConfirm: document.getElementById("modal-confirm"),
        confirmCount: document.getElementById("confirm-count")
    };

    let recipients = new Set();
    let actionAlreadyTaken = false;

    // --- Data Loading ---

    async function loadData() {
        try {
            // Fetch payload first, because this endpoint triggers the server
            // to load the data from disk and update the server-side status to 'Ready'
            const payloadRes = await fetch("/api/payload");
            const statusRes = await fetch("/api/status");

            const statusData = await statusRes.json();
            updateStatusUI(statusData);

            if (payloadRes.ok) {
                const payload = await payloadRes.json();
                renderPayload(payload);
            } else {
                showToast("Failed to load payload.", "error");
            }
        } catch (error) {
            console.error(error);
            showToast("Network error while loading data.", "error");
        }
    }

    function renderPayload(payload) {
        elements.dateChip.textContent = payload.date;

        // Themes
        elements.themeList.innerHTML = payload.weekly_pulse.themes.map(t => 
            `<li>
                <span class="theme-name">${t.name}</span>
                <span class="theme-count">${t.review_count} reviews</span>
            </li>`
        ).join("");

        // Note
        elements.weeklyNote.innerHTML = `<p>${payload.weekly_pulse.note}</p>`;

        // Quotes
        elements.quotesGrid.innerHTML = payload.weekly_pulse.quotes.map(q => 
            `<div class="quote-card">
                <p>${q.text}</p>
                <div class="quote-rating">Rating: ${q.rating}/5</div>
            </div>`
        ).join("");

        // Actions
        elements.actionList.innerHTML = payload.weekly_pulse.actions.map(a => 
            `<li>${a}</li>`
        ).join("");

        // Fee
        elements.feeScenario.textContent = payload.fee_scenario;
        elements.feeBulletsList.innerHTML = payload.explanation_bullets.map(b => 
            `<li>${b}</li>`
        ).join("");
        

    }

    function updateStatusUI(statusData) {
        elements.statusText.textContent = statusData.status;
        actionAlreadyTaken = statusData.action_taken;

        // Update badge color
        elements.statusBadge.className = "status-badge";
        if (actionAlreadyTaken) {
            if (statusData.status.includes("Reject")) {
                elements.statusBadge.classList.add("status-danger");
            } else if (statusData.status.includes("Fail")) {
                elements.statusBadge.classList.add("status-danger");
            } else {
                elements.statusBadge.classList.add("status-warning"); // or generic done
            }
            disableActionButtons();
        }
    }

    function disableActionButtons() {
        elements.btnApprove.disabled = true;
        elements.btnReject.disabled = true;
        elements.emailInput.disabled = true;
        elements.addEmailBtn.disabled = true;
        // disable remove buttons on chips
        document.querySelectorAll(".chip-remove").forEach(btn => btn.style.display = "none");
    }

    // --- Recipient Management ---

    function renderChips() {
        elements.recipientChips.innerHTML = Array.from(recipients).map(email => 
            `<div class="chip">
                <span>${email}</span>
                <button class="chip-remove" data-email="${email}">
                    <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>`
        ).join("");

        // Attach listeners
        document.querySelectorAll(".chip-remove").forEach(btn => {
            btn.addEventListener("click", (e) => {
                if (actionAlreadyTaken) return;
                const email = e.currentTarget.getAttribute("data-email");
                recipients.delete(email);
                renderChips();
            });
        });
    }

    function addRecipient() {
        const val = elements.emailInput.value.trim().toLowerCase();
        // Simple regex check
        const regex = /^\S+@\S+\.\S+$/;
        if (!val || !regex.test(val)) {
            showToast("Please enter a valid email address.", "error");
            return;
        }

        if (recipients.has(val)) {
            showToast("Recipient already added.", "error");
            return;
        }

        recipients.add(val);
        elements.emailInput.value = "";
        renderChips();
    }

    elements.addEmailBtn.addEventListener("click", addRecipient);
    elements.emailInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") addRecipient();
    });

    // --- Approvals & Modals ---

    elements.btnReject.addEventListener("click", async () => {
        if (actionAlreadyTaken) return;
        if (confirm("Are you sure you want to reject this pipeline run? No MCP actions will be taken.")) {
            try {
                const res = await fetch("/api/reject", { method: "POST" });
                const data = await res.json();
                if (res.ok) {
                    showToast(data.message, "success");
                    loadData(); // reload status
                } else {
                    showToast(data.error, "error");
                }
            } catch (e) {
                showToast("Request failed", "error");
            }
        }
    });

    elements.btnApprove.addEventListener("click", () => {
        if (actionAlreadyTaken) return;
        elements.confirmCount.textContent = recipients.size;
        elements.modal.classList.add("active");
    });

    elements.modalCancel.addEventListener("click", () => {
        elements.modal.classList.remove("active");
    });

    elements.modalConfirm.addEventListener("click", async () => {
        elements.modal.classList.remove("active");
        
        elements.statusText.textContent = "Processing...";
        elements.statusBadge.classList.add("status-warning");
        disableActionButtons();

        try {
            const res = await fetch("/api/approve", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ recipients: Array.from(recipients) })
            });
            const data = await res.json();

            if (res.ok) {
                showToast(data.message, "success");
            } else {
                showToast(data.error || "Failed to trigger actions", "error");
            }
        } catch (e) {
            showToast("Network error during approval", "error");
        } finally {
            loadData(); // Refresh final status
        }
    });

    // --- Toasts ---
    function showToast(message, type = "success") {
        const container = document.getElementById("toast-container");
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(50px)";
            toast.style.transition = "all 0.3s";
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // Init
    loadData();
});
