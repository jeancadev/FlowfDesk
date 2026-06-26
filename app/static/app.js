/* ═══════════════════════════════════════════════════════════
   FlowDesk — Client Application
   ═══════════════════════════════════════════════════════════ */

// ─── State ──────────────────────────────────────────────────

const state = {
  comments: [],
  selectedTicket: null,
  tickets: [],
  users: [],
};

// ─── DOM References ─────────────────────────────────────────

const els = {
  healthDot: document.querySelector("#health-dot"),
  healthLabel: document.querySelector("#health-label"),
  healthDetail: document.querySelector("#health-detail"),
  ticketList: document.querySelector("#ticket-list"),
  ticketDetail: document.querySelector("#ticket-detail-panel"),
  userList: document.querySelector("#user-list"),
  ticketCount: document.querySelector("#ticket-count"),
  userCount: document.querySelector("#user-count"),
  ticketCreator: document.querySelector("#ticket-creator"),
  ticketForm: document.querySelector("#ticket-form"),
  userForm: document.querySelector("#user-form"),
  searchInput: document.querySelector("#ticket-search"),
  toast: document.querySelector("#toast"),
};

// ─── API Layer ──────────────────────────────────────────────

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

// ─── Toast Notifications ────────────────────────────────────

const TOAST_ICONS = {
  success: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg>`,
  error: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>`,
  info: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`,
};

let toastTimer = null;

function showToast(message, type = "success") {
  clearTimeout(toastTimer);
  const icon = TOAST_ICONS[type] || TOAST_ICONS.info;
  els.toast.className = `toast toast-${type}`;
  els.toast.innerHTML = `${icon}<span>${escapeHtml(message)}</span>`;
  // Force reflow so the animation replays when rapid toasts fire.
  void els.toast.offsetWidth;
  els.toast.classList.add("is-visible");
  toastTimer = setTimeout(() => els.toast.classList.remove("is-visible"), 3000);
}

// ─── Helpers ────────────────────────────────────────────────

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
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

function formatDate(value) {
  if (!value) {
    return "No date";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function userLabel(userId) {
  const user = state.users.find((item) => item.id === userId);
  return user ? user.full_name : userId || "Unassigned";
}

function userOptions(selectedId = "") {
  return state.users
    .map((user) => {
      const selected = user.id === selectedId ? " selected" : "";
      return `<option value="${escapeHtml(user.id)}"${selected}>${escapeHtml(
        user.full_name,
      )}</option>`;
    })
    .join("");
}

// ─── Skeleton Loaders ───────────────────────────────────────

function skeletonCards(count = 3) {
  return `<div class="skeleton">${Array.from({ length: count })
    .map(
      () => `
      <div class="skeleton-card">
        <div class="skeleton-line w-60"></div>
        <div class="skeleton-line w-80"></div>
        <div class="skeleton-line w-40"></div>
      </div>`,
    )
    .join("")}</div>`;
}

function showListLoading(listEl) {
  listEl.innerHTML = skeletonCards(3);
}

// ─── Metrics ────────────────────────────────────────────────

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

// ─── Render: Users ──────────────────────────────────────────

function renderUsers() {
  els.userCount.textContent = `${state.users.length} records`;
  els.ticketCreator.innerHTML = userOptions();

  if (!state.users.length) {
    els.userList.innerHTML = `<div class="empty-state">
      <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" x2="19" y1="8" y2="14"/><line x1="22" x2="16" y1="11" y2="11"/></svg>
      <p>No users yet. Create one to get started.</p>
    </div>`;
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

// ─── Render: Tickets ────────────────────────────────────────

function renderTickets(tickets = state.tickets) {
  els.ticketCount.textContent = `${tickets.length} records`;

  if (!tickets.length) {
    els.ticketList.innerHTML = `<div class="empty-state">
      <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5v2"/><path d="M15 11v2"/><path d="M15 17v2"/><path d="M5 5h14a2 2 0 0 1 2 2v3a2 2 0 0 0 0 4v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3a2 2 0 0 0 0-4V7a2 2 0 0 1 2-2z"/></svg>
      <p>No tickets found.</p>
    </div>`;
    return;
  }

  els.ticketList.innerHTML = tickets
    .map((ticket) => {
      const selected = state.selectedTicket?.id === ticket.id ? " is-selected" : "";
      return `
        <article class="record${selected}">
          <div class="record-head">
            <p class="record-title">${escapeHtml(ticket.title)}</p>
            <span class="pill ${safeClass(ticket.status)}">${escapeHtml(
              titleCase(ticket.status),
            )}</span>
          </div>
          <p>${escapeHtml(ticket.description)}</p>
          <div class="record-meta">
            <span class="pill ${safeClass(ticket.priority)}">${escapeHtml(
              titleCase(ticket.priority),
            )}</span>
            <span>${escapeHtml((ticket.tags || []).join(", ") || "No tags")}</span>
            <span>${escapeHtml(ticket.id)}</span>
          </div>
          <div class="record-actions">
            <button class="button subtle" data-view="${escapeHtml(
              ticket.id,
            )}" type="button">Details</button>
            ${
              ticket.status !== "closed"
                ? `<button class="button subtle" data-close="${escapeHtml(
                    ticket.id,
                  )}" type="button">Close</button>`
                : ""
            }
            <button class="button ghost" data-delete="${escapeHtml(
              ticket.id,
            )}" type="button">Delete</button>
          </div>
        </article>
      `;
    })
    .join("");
}

// ─── Render: Ticket Detail ──────────────────────────────────

function renderTicketDetail() {
  const ticket = state.selectedTicket;

  if (!ticket) {
    els.ticketDetail.innerHTML = `
      <div class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><line x1="10" x2="8" y1="9" y2="9"/></svg>
        <p>Select a ticket to inspect activity and add comments.</p>
      </div>
    `;
    return;
  }

  const comments = state.comments.length
    ? state.comments
        .map(
          (comment) => `
            <article class="comment">
              <span class="comment-meta">
                ${escapeHtml(userLabel(comment.author_id))} — ${escapeHtml(
                  formatDate(comment.created_at),
                )}
              </span>
              <p>${escapeHtml(comment.body)}</p>
            </article>
          `,
        )
        .join("")
    : `<div class="empty-state"><p>No comments yet.</p></div>`;

  els.ticketDetail.innerHTML = `
    <div class="detail-stack">
      <div class="detail-summary">
        <div class="record-head">
          <h2>${escapeHtml(ticket.title)}</h2>
          <span class="pill ${safeClass(ticket.status)}">${escapeHtml(
            titleCase(ticket.status),
          )}</span>
        </div>
        <p class="detail-description">${escapeHtml(ticket.description)}</p>
        <div class="record-meta">
          <span class="pill ${safeClass(ticket.priority)}">${escapeHtml(
            titleCase(ticket.priority),
          )}</span>
          <span>Creator: ${escapeHtml(userLabel(ticket.creator_id))}</span>
          <span>Created: ${escapeHtml(formatDate(ticket.created_at))}</span>
        </div>
      </div>

      <div>
        <div class="panel-header">
          <div>
            <h2>Comments</h2>
            <p>${state.comments.length} records</p>
          </div>
        </div>
        <div class="comment-list">${comments}</div>
      </div>

      <form class="comment-form" id="comment-form">
        <label>
          Author
          <select name="author_id" required>${userOptions(ticket.creator_id)}</select>
        </label>
        <label>
          Comment
          <textarea name="body" minlength="1" required></textarea>
        </label>
        <button class="button primary" type="submit">Add Comment</button>
      </form>
    </div>
  `;
}

// ─── Data Loading ───────────────────────────────────────────

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
  showListLoading(els.ticketList);
  showListLoading(els.userList);

  try {
    const [users, tickets] = await Promise.all([
      api("/api/v1/users/"),
      api("/api/v1/tickets/"),
    ]);
    state.users = users;
    state.tickets = tickets;

    if (state.selectedTicket) {
      const current = tickets.find((ticket) => ticket.id === state.selectedTicket.id);
      state.selectedTicket = current || null;
      if (!current) {
        state.comments = [];
      }
    }

    renderUsers();
    renderTickets();
    renderTicketDetail();
    updateMetrics();
  } catch (error) {
    showToast(`Failed to load data: ${error.message}`, "error");
    els.ticketList.innerHTML = `<div class="empty-state"><p>Could not load tickets.</p></div>`;
    els.userList.innerHTML = `<div class="empty-state"><p>Could not load users.</p></div>`;
  }
}

async function loadTicketDetail(ticketId) {
  els.ticketDetail.innerHTML = `<div class="spinner">Loading details…</div>`;

  try {
    const [ticket, comments] = await Promise.all([
      api(`/api/v1/tickets/${ticketId}`),
      api(`/api/v1/tickets/${ticketId}/comments`),
    ]);
    state.selectedTicket = ticket;
    state.comments = comments;
    renderTickets();
    renderTicketDetail();
  } catch (error) {
    showToast(`Failed to load ticket: ${error.message}`, "error");
  }
}

// ─── Actions ────────────────────────────────────────────────

async function createUser(event) {
  event.preventDefault();
  const formEl = event.currentTarget;
  const form = new FormData(formEl);

  try {
    await api("/api/v1/users/", {
      method: "POST",
      body: JSON.stringify(Object.fromEntries(form)),
    });
    formEl.reset();
    await refreshData();
    showToast("User created", "success");
  } catch (error) {
    showToast(`Failed to create user: ${error.message}`, "error");
  }
}

async function createTicket(event) {
  event.preventDefault();
  const formEl = event.currentTarget;
  const form = new FormData(formEl);
  const payload = Object.fromEntries(form);
  payload.tags = payload.tags
    ? payload.tags.split(",").map((tag) => tag.trim()).filter(Boolean)
    : [];

  try {
    const ticket = await api("/api/v1/tickets/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    formEl.reset();
    await refreshData();
    await loadTicketDetail(ticket.id);
    showToast("Ticket created", "success");
  } catch (error) {
    showToast(`Failed to create ticket: ${error.message}`, "error");
  }
}

async function createComment(event) {
  event.preventDefault();
  if (!state.selectedTicket) {
    return;
  }

  const formEl = event.currentTarget;
  const form = new FormData(formEl);

  try {
    await api(`/api/v1/tickets/${state.selectedTicket.id}/comments`, {
      method: "POST",
      body: JSON.stringify(Object.fromEntries(form)),
    });
    await loadTicketDetail(state.selectedTicket.id);
    showToast("Comment added", "success");
  } catch (error) {
    showToast(`Failed to add comment: ${error.message}`, "error");
  }
}

async function searchTickets() {
  const query = els.searchInput.value.trim();
  if (!query) {
    renderTickets();
    return;
  }

  showListLoading(els.ticketList);

  try {
    const results = await api(`/api/v1/tickets/search?q=${encodeURIComponent(query)}`);
    renderTickets(results);
  } catch (error) {
    showToast(`Search failed: ${error.message}`, "error");
    renderTickets();
  }
}

// ─── Delete Confirmation ────────────────────────────────────

let pendingDeleteId = null;

function showDeleteConfirm(ticketId, buttonEl) {
  // Remove any existing confirm bar first.
  dismissDeleteConfirm();

  pendingDeleteId = ticketId;
  const record = buttonEl.closest(".record");
  if (!record) return;

  const actionsEl = record.querySelector(".record-actions");
  if (!actionsEl) return;

  const confirmBar = document.createElement("div");
  confirmBar.className = "confirm-bar";
  confirmBar.innerHTML = `
    <span class="confirm-text">Delete this ticket?</span>
    <button class="button danger" data-confirm-delete="${escapeHtml(ticketId)}" type="button">Yes, delete</button>
    <button class="button subtle" data-cancel-delete type="button">Cancel</button>
  `;

  actionsEl.style.display = "none";
  record.appendChild(confirmBar);
}

function dismissDeleteConfirm() {
  pendingDeleteId = null;
  const existing = document.querySelector(".confirm-bar");
  if (existing) {
    const record = existing.closest(".record");
    const actionsEl = record?.querySelector(".record-actions");
    if (actionsEl) actionsEl.style.display = "";
    existing.remove();
  }
}

async function executeDelete(ticketId) {
  try {
    await api(`/api/v1/tickets/${ticketId}`, { method: "DELETE" });
    if (state.selectedTicket?.id === ticketId) {
      state.selectedTicket = null;
      state.comments = [];
    }
    await refreshData();
    showToast("Ticket deleted", "success");
  } catch (error) {
    showToast(`Failed to delete: ${error.message}`, "error");
  }
  pendingDeleteId = null;
}

// ─── Ticket Action Handler ──────────────────────────────────

async function handleTicketAction(event) {
  const target = event.target;
  const viewId = target.dataset.view;
  const closeId = target.dataset.close;
  const deleteId = target.dataset.delete;
  const confirmDeleteId = target.dataset.confirmDelete;
  const cancelDelete = target.dataset.cancelDelete;

  if (viewId) {
    await loadTicketDetail(viewId);
  }

  if (closeId) {
    try {
      await api(`/api/v1/tickets/${closeId}/close`, { method: "POST" });
      await refreshData();
      await loadTicketDetail(closeId);
      showToast("Ticket closed", "success");
    } catch (error) {
      showToast(`Failed to close ticket: ${error.message}`, "error");
    }
  }

  if (deleteId) {
    showDeleteConfirm(deleteId, target);
  }

  if (confirmDeleteId) {
    await executeDelete(confirmDeleteId);
  }

  if (cancelDelete !== undefined) {
    dismissDeleteConfirm();
  }
}

// ─── Tab Navigation ─────────────────────────────────────────

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

// ─── Event Bindings ─────────────────────────────────────────

function bindEvents() {
  bindTabs();
  document.querySelector("#refresh-btn").addEventListener("click", refreshData);
  document.querySelector("#search-btn").addEventListener("click", searchTickets);
  els.searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      searchTickets();
    }
  });
  els.ticketDetail.addEventListener("submit", createComment);
  els.ticketList.addEventListener("click", handleTicketAction);
  els.userForm.addEventListener("submit", createUser);
  els.ticketForm.addEventListener("submit", createTicket);
}

// ─── Init ───────────────────────────────────────────────────

async function init() {
  bindEvents();
  await loadHealth();
  try {
    await refreshData();
  } catch (error) {
    showToast(error.message, "error");
  }
}

init();
