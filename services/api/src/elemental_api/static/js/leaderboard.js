const REFRESH_INTERVAL = 7000;
const searchInput = document.querySelector("#search");
const sortSelect = document.querySelector("#sort");
const directionButton = document.querySelector("#direction");
const rowsElement = document.querySelector("#score-rows");
const podiumElement = document.querySelector("#podium");
const refreshStatus = document.querySelector("#refresh-status");
const footerStatus = document.querySelector("#footer-status");
const pageStatus = document.querySelector("#page-status");
const previousPageButton = document.querySelector("#previous-page");
const nextPageButton = document.querySelector("#next-page");
const pageSizeSelect = document.querySelector("#page-size");
const PAGE_SIZE_KEY = "leaderboard-page-size";
let scores = [];
let descending = true;
let totalScores = 0;
let offset = 0;
let activeRequest;
let searchTimer;

function formatDuration(seconds) {
  const wholeSeconds = Math.floor(seconds);
  const minutes = Math.floor(wholeSeconds / 60);
  return `${minutes}:${String(wholeSeconds % 60).padStart(2, "0")}`;
}

function makeCell(value, className = "") {
  const cell = document.createElement("td");
  cell.className = className;
  cell.textContent = value;
  return cell;
}

function renderPodium(ranked) {
  podiumElement.replaceChildren();
  (offset === 0 ? ranked.slice(0, 3) : []).forEach((score, index) => {
    const column = document.createElement("div");
    column.className = "col-12 col-md-4";
    const card = document.createElement("article");
    card.className = "podium-card h-100";
    const rank = document.createElement("div");
    rank.className = "podium-rank";
    rank.textContent = `#${index + 1} keeper`;
    const name = document.createElement("div");
    name.className = "podium-name";
    name.textContent = score.username;
    const time = document.createElement("div");
    time.className = "podium-time";
    time.textContent = `${formatDuration(score.time_survived)} survived · wave ${score.wave_number}`;
    card.append(rank, name, time);
    column.append(card);
    podiumElement.append(column);
  });
}

function render() {
  const ranked = scores;
  rowsElement.replaceChildren();
  renderPodium(ranked);
  const firstResult = totalScores === 0 ? 0 : offset + 1;
  const lastResult = Math.min(offset + scores.length, totalScores);
  pageStatus.textContent = `${firstResult}–${lastResult} of ${totalScores}`;
  previousPageButton.disabled = offset === 0;
  nextPageButton.disabled = offset + scores.length >= totalScores;
  if (!ranked.length) {
    const row = document.createElement("tr");
    const message = searchInput.value.trim()
      ? "No scores match your search."
      : "No scores yet. Be the first keeper to enter the hall.";
    const cell = makeCell(message, "empty-state text-center py-5");
    cell.colSpan = 6;
    row.append(cell);
    rowsElement.append(row);
    return;
  }

  ranked.forEach((score, index) => {
    const row = document.createElement("tr");
    const player = makeCell(score.username, "player-cell");
    const runId = document.createElement("span");
    runId.className = "run-id";
    runId.textContent = `Run ${score.run_id}`;
    runId.title = score.run_id;
    player.append(runId);
    const date = new Date(score.submitted_at);
    row.append(
      makeCell(String(offset + index + 1).padStart(2, "0"), "rank-cell"),
      player,
      makeCell(formatDuration(score.time_survived), "text-end survival-cell numeric-cell"),
      makeCell(String(score.wave_number), "text-end numeric-cell"),
      makeCell(String(score.enemies_defeated), "text-end numeric-cell"),
      makeCell(
        Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString(),
        "text-end",
      ),
    );
    rowsElement.append(row);
  });
}

async function refresh() {
  activeRequest?.abort();
  const controller = new AbortController();
  activeRequest = controller;
  const pageSize = Number(pageSizeSelect.value);
  const parameters = new URLSearchParams({
    limit: String(pageSize),
    offset: String(offset),
    search: searchInput.value.trim(),
    sort: sortSelect.value,
    direction: descending ? "desc" : "asc",
  });
  try {
    const response = await fetch(`/api/v1/leaderboard?${parameters}`, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`Leaderboard request failed (${response.status})`);
    const payload = await response.json();
    if (!Array.isArray(payload.scores) || !Number.isInteger(payload.total)) {
      throw new Error("Leaderboard response has an invalid format");
    }
    scores = payload.scores;
    totalScores = payload.total;
    const updated = new Date();
    document.querySelector("#stat-runs").textContent = String(totalScores);
    document.querySelector("#stat-wave").textContent = scores.length
      ? String(Math.max(...scores.map((score) => score.wave_number)))
      : "—";
    document.querySelector("#stat-updated").textContent = updated.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    refreshStatus.textContent = "Live";
    footerStatus.textContent = "Live refresh · every 7 seconds";
    footerStatus.classList.remove("error");
    render();
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    refreshStatus.textContent = "Could not refresh";
    footerStatus.textContent = error instanceof Error
      ? error.message
      : "Unexpected leaderboard error";
    footerStatus.classList.add("error");
    if (!scores.length) {
      rowsElement.replaceChildren();
      const row = document.createElement("tr");
      const cell = makeCell(
        "The leaderboard could not load. It will try again shortly.",
        "empty-state text-center py-5",
      );
      cell.colSpan = 6;
      row.append(cell);
      rowsElement.append(row);
    }
  } finally {
    if (activeRequest === controller) activeRequest = undefined;
  }
}

searchInput.addEventListener("input", () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => {
    offset = 0;
    refresh();
  }, 300);
});
sortSelect.addEventListener("change", () => {
  offset = 0;
  refresh();
});
directionButton.addEventListener("click", () => {
  descending = !descending;
  directionButton.textContent = descending ? "↓" : "↑";
  directionButton.setAttribute("aria-label", `Sort ${descending ? "descending" : "ascending"}`);
  offset = 0;
  refresh();
});

previousPageButton.addEventListener("click", () => {
  offset = Math.max(0, offset - Number(pageSizeSelect.value));
  refresh();
});
nextPageButton.addEventListener("click", () => {
  offset += Number(pageSizeSelect.value);
  refresh();
});
pageSizeSelect.addEventListener("change", () => {
  try {
    window.localStorage.setItem(PAGE_SIZE_KEY, pageSizeSelect.value);
  } catch (error) {
    console.warn("Could not save the leaderboard page size.", error);
  }
  offset = 0;
  refresh();
});

try {
  const savedPageSize = window.localStorage.getItem(PAGE_SIZE_KEY);
  if (["10", "25", "50", "100"].includes(savedPageSize)) {
    pageSizeSelect.value = savedPageSize;
  }
} catch (error) {
  console.warn("Could not read the saved leaderboard page size.", error);
}

refresh();
window.setInterval(refresh, REFRESH_INTERVAL);
