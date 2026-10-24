const REFRESH_INTERVAL = 7000;
const searchInput = document.querySelector("#search");
const sortSelect = document.querySelector("#sort");
const directionButton = document.querySelector("#direction");
const rowsElement = document.querySelector("#score-rows");
const podiumElement = document.querySelector("#podium");
const refreshStatus = document.querySelector("#refresh-status");
const footerStatus = document.querySelector("#footer-status");
const themeToggle = document.querySelector("#theme-toggle");
const themeLabel = document.querySelector("#theme-label");
const themeIcon = document.querySelector("#theme-icon");
let scores = [];
let descending = true;
let refreshing = false;

function storedTheme() {
  try {
    return window.localStorage.getItem("leaderboard-theme");
  } catch (error) {
    console.warn("Could not read the saved theme preference.", error);
    return null;
  }
}

function applyTheme(theme) {
  const isDark = theme === "dark";
  document.documentElement.setAttribute("data-bs-theme", theme);
  themeToggle.setAttribute("aria-pressed", String(isDark));
  themeToggle.setAttribute("aria-label", `Switch to ${isDark ? "light" : "dark"} mode`);
  themeLabel.textContent = isDark ? "Light mode" : "Dark mode";
  themeIcon.textContent = isDark ? "☀" : "☾";
  try {
    window.localStorage.setItem("leaderboard-theme", theme);
  } catch (error) {
    console.warn("Could not save the theme preference.", error);
  }
}

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

function filteredScores() {
  const query = searchInput.value.trim().toLocaleLowerCase();
  const key = sortSelect.value;
  return scores
    .filter((score) => !query || `${score.username} ${score.run_id}`.toLocaleLowerCase().includes(query))
    .slice()
    .sort((first, second) => {
      const left = first[key];
      const right = second[key];
      const comparison = typeof left === "string" && key === "username"
        ? left.localeCompare(right)
        : key === "submitted_at"
          ? new Date(left) - new Date(right)
          : Number(left) - Number(right);
      return (descending ? -1 : 1) * comparison;
    });
}

function renderPodium(ranked) {
  podiumElement.replaceChildren();
  ranked.slice(0, 3).forEach((score, index) => {
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
  const ranked = filteredScores();
  rowsElement.replaceChildren();
  renderPodium(ranked);
  if (!ranked.length) {
    const row = document.createElement("tr");
    const message = scores.length
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
      makeCell(String(index + 1).padStart(2, "0"), "rank-cell"),
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
  if (refreshing) return;
  refreshing = true;
  try {
    const response = await fetch("/api/v1/leaderboard?limit=100", { cache: "no-store" });
    if (!response.ok) throw new Error(`Leaderboard request failed (${response.status})`);
    const payload = await response.json();
    if (!Array.isArray(payload.scores)) throw new Error("Leaderboard response has an invalid format");
    scores = payload.scores;
    const updated = new Date();
    document.querySelector("#stat-runs").textContent = String(scores.length);
    document.querySelector("#stat-wave").textContent = scores.length
      ? String(Math.max(...scores.map((score) => score.wave_number)))
      : "—";
    document.querySelector("#stat-updated").textContent = updated.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    refreshStatus.textContent = `Updated ${updated.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    })}`;
    footerStatus.textContent = "Live refresh · every 7 seconds";
    footerStatus.classList.remove("error");
    render();
  } catch (error) {
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
    refreshing = false;
  }
}

const savedTheme = storedTheme();
const initialTheme = savedTheme === "light" || savedTheme === "dark"
  ? savedTheme
  : window.matchMedia("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
applyTheme(initialTheme);

themeToggle.addEventListener("click", () => {
  const currentTheme = document.documentElement.getAttribute("data-bs-theme");
  applyTheme(currentTheme === "dark" ? "light" : "dark");
});
searchInput.addEventListener("input", render);
sortSelect.addEventListener("change", render);
directionButton.addEventListener("click", () => {
  descending = !descending;
  directionButton.textContent = descending ? "↓" : "↑";
  directionButton.setAttribute("aria-label", `Sort ${descending ? "descending" : "ascending"}`);
  render();
});

refresh();
window.setInterval(refresh, REFRESH_INTERVAL);
