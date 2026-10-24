const themeToggle = document.querySelector("#theme-toggle");
const themeLabel = document.querySelector("#theme-label");
const themeIcon = document.querySelector("#theme-icon");

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
