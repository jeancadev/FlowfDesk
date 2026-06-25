const state = {
  comments: [],
  selectedTicket: null,
  tickets: [],
  users: [],
};

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
  els.ticketCreator.innerHTML = userOptions();

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

function renderTicketDetail() {
  const ticket = state.selectedTicket;

  if (!ticket) {
    els.ticketDetail.innerHTML = `
      <div class="empty-state">
        Select a ticket to inspect activity and add comments.
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
                ${escapeHtml(userLabel(comment.author_id))} - ${escapeHtml(
                  formatDate(comment.created_at),
                )}
              </span>
              <p>${escapeHtml(comment.body)}</p>
            </article>
          `,
        )
        .join("")
    : `<div class="empty-state">No comments yet.</div>`;

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
}

async function loadTicketDetail(ticketId) {
  const [ticket, comments] = await Promise.all([
    api(`/api/v1/tickets/${ticketId}`),
    api(`/api/v1/tickets/${ticketId}/comments`),
  ]);
  state.selectedTicket = ticket;
  state.comments = comments;
  renderTickets();
  renderTicketDetail();
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

  const ticket = await api("/api/v1/tickets/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  event.currentTarget.reset();
  await refreshData();
  await loadTicketDetail(ticket.id);
  showToast("Ticket created");
}

async function createComment(event) {
  event.preventDefault();
  if (!state.selectedTicket) {
    return;
  }

  const form = new FormData(event.currentTarget);
  await api(`/api/v1/tickets/${state.selectedTicket.id}/comments`, {
    method: "POST",
    body: JSON.stringify(Object.fromEntries(form)),
  });
  await loadTicketDetail(state.selectedTicket.id);
  showToast("Comment added");
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
  const viewId = event.target.dataset.view;
  const closeId = event.target.dataset.close;
  const deleteId = event.target.dataset.delete;

  if (viewId) {
    await loadTicketDetail(viewId);
  }

  if (closeId) {
    await api(`/api/v1/tickets/${closeId}/close`, { method: "POST" });
    await refreshData();
    await loadTicketDetail(closeId);
    showToast("Ticket closed");
  }

  if (deleteId) {
    await api(`/api/v1/tickets/${deleteId}`, { method: "DELETE" });
    if (state.selectedTicket?.id === deleteId) {
      state.selectedTicket = null;
      state.comments = [];
    }
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
  els.ticketDetail.addEventListener("submit", createComment);
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
