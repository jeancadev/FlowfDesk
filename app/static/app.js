const state = {
  tickets: [],
  users: [],
};

const els = {
  healthDot: document.querySelector("#health-dot"),
  healthLabel: document.querySelector("#health-label"),
  healthDetail: document.querySelector("#health-detail"),
  ticketList: document.querySelector("#ticket-list"),
  userList: document.querySelector("#user-list"),
  ticketCount: document.querySelector("#ticket-count"),
  userCount: document.querySelector("#user-count"),
  ticketCreator: document.querySelector("#ticket-creator"),
  ticketForm: document.querySelector("#ticket-form"),
  userForm: document.querySelector("#user-form"),
  searchInput: document.querySelector("#ticket-search"),
  toast: document.querySelector("#toast"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data.message || data.error || detail;
    } catch {
      // Keep the HTTP status text when the body is empty.
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("is-visible");
  window.setTimeout(() => els.toast.classList.remove("is-visible"), 2600);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;",
    };
    return entities[char];
  });
}

function safeClass(value) {
  return String(value || "").replace(/[^a-z0-9_-]/gi, "");
}

function titleCase(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function updateMetrics() {
  document.querySelector("#metric-open").textContent = state.tickets.filter(
    (ticket) => ticket.status === "open",
  ).length;
  document.querySelector("#metric-progress").textContent = state.tickets.filter(
    (ticket) => ticket.status === "in_progress",
  ).length;
  document.querySelector("#metric-closed").textContent = state.tickets.filter(
    (ticket) => ticket.status === "closed",
  ).length;
  document.querySelector("#metric-users").textContent = state.users.length;
}

function renderUsers() {
  els.userCount.textContent = `${state.users.length} records`;
  els.ticketCreator.innerHTML = state.users
    .map((user) => `<option value="${escapeHtml(user.id)}">${escapeHtml(user.full_name)}</option>`)
    .join("");

  if (!state.users.length) {
    els.userList.innerHTML = `<div class="empty-state">No users yet.</div>`;
    return;
  }

  els.userList.innerHTML = state.users
    .map(
      (user) => `
        <article class="record">
          <div class="record-head">
            <p class="record-title">${escapeHtml(user.full_name)}</p>
            <span class="pill">${escapeHtml(titleCase(user.role))}</span>
          </div>
          <div class="record-meta">
            <span>${escapeHtml(user.email)}</span>
            <span>${escapeHtml(user.id)}</span>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderTickets(tickets = state.tickets) {
  els.ticketCount.textContent = `${tickets.length} records`;

  if (!tickets.length) {
    els.ticketList.innerHTML = `<div class="empty-state">No tickets found.</div>`;
    return;
  }

  els.ticketList.innerHTML = tickets
    .map(
      (ticket) => `
        <article class="record">
          <div class="record-head">
            <p class="record-title">${escapeHtml(ticket.title)}</p>
            <span class="pill ${safeClass(ticket.status)}">${escapeHtml(titleCase(ticket.status))}</span>
          </div>
          <p>${escapeHtml(ticket.description)}</p>
          <div class="record-meta">
            <span class="pill ${safeClass(ticket.priority)}">${escapeHtml(titleCase(ticket.priority))}</span>
            <span>${escapeHtml((ticket.tags || []).join(", ") || "No tags")}</span>
            <span>${escapeHtml(ticket.id)}</span>
          </div>
          <div class="record-actions">
            ${
              ticket.status !== "closed"
                ? `<button class="button subtle" data-close="${escapeHtml(ticket.id)}" type="button">
                    Close
                  </button>`
                : ""
            }
            <button class="button ghost" data-delete="${escapeHtml(ticket.id)}" type="button">
              Delete
            </button>
          </div>
        </article>
      `,
    )
    .join("");
}

async function loadHealth() {
  try {
    const health = await api("/health");
    els.healthDot.className = "status-dot is-ok";
    els.healthLabel.textContent = "API healthy";
    els.healthDetail.textContent = `Redis ${health.redis}`;
  } catch (error) {
    els.healthDot.className = "status-dot is-bad";
    els.healthLabel.textContent = "API offline";
    els.healthDetail.textContent = error.message;
  }
}

async function refreshData() {
  const [users, tickets] = await Promise.all([
    api("/api/v1/users/"),
    api("/api/v1/tickets/"),
  ]);
  state.users = users;
  state.tickets = tickets;
  renderUsers();
  renderTickets();
  updateMetrics();
}

async function createUser(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  await api("/api/v1/users/", {
    method: "POST",
    body: JSON.stringify(Object.fromEntries(form)),
  });
  event.currentTarget.reset();
  await refreshData();
  showToast("User created");
}

async function createTicket(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form);
  payload.tags = payload.tags
    ? payload.tags.split(",").map((tag) => tag.trim()).filter(Boolean)
    : [];

  await api("/api/v1/tickets/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  event.currentTarget.reset();
  await refreshData();
  showToast("Ticket created");
}

async function searchTickets() {
  const query = els.searchInput.value.trim();
  if (!query) {
    renderTickets();
    return;
  }

  const results = await api(`/api/v1/tickets/search?q=${encodeURIComponent(query)}`);
  renderTickets(results);
}

async function handleTicketAction(event) {
  const closeId = event.target.dataset.close;
  const deleteId = event.target.dataset.delete;

  if (closeId) {
    await api(`/api/v1/tickets/${closeId}/close`, { method: "POST" });
    await refreshData();
    showToast("Ticket closed");
  }

  if (deleteId) {
    await api(`/api/v1/tickets/${deleteId}`, { method: "DELETE" });
    await refreshData();
    showToast("Ticket deleted");
  }
}

function bindTabs() {
  document.querySelectorAll(".nav-tab").forEach((button) => {
    button.addEventListener("click", () => {
      document
        .querySelectorAll(".nav-tab")
        .forEach((tab) => tab.classList.toggle("is-active", tab === button));
      document
        .querySelectorAll(".view")
        .forEach((view) =>
          view.classList.toggle("is-active", view.id === `${button.dataset.tab}-view`),
        );
    });
  });
}

function bindEvents() {
  bindTabs();
  document.querySelector("#refresh-btn").addEventListener("click", refreshData);
  document.querySelector("#search-btn").addEventListener("click", searchTickets);
  els.searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      searchTickets();
    }
  });
  els.ticketList.addEventListener("click", handleTicketAction);
  els.userForm.addEventListener("submit", createUser);
  els.ticketForm.addEventListener("submit", createTicket);
}

async function init() {
  bindEvents();
  await loadHealth();
  try {
    await refreshData();
  } catch (error) {
    showToast(error.message);
  }
}

init();

