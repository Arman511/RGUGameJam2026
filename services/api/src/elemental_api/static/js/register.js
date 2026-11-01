const form = document.querySelector("#register-form");
const usernameInput = document.querySelector("#username");
const passwordInput = document.querySelector("#password");
const confirmPasswordInput = document.querySelector("#confirm-password");
const messageElement = document.querySelector("#form-message");
const submitButton = document.querySelector("#register-button");
const passwordRequirements = {
  length: document.querySelector("#requirement-length"),
  uppercase: document.querySelector("#requirement-uppercase"),
  lowercase: document.querySelector("#requirement-lowercase"),
  number: document.querySelector("#requirement-number"),
  symbol: document.querySelector("#requirement-symbol"),
};
const passwordMatchElement = document.querySelector("#password-match");

for (const toggle of document.querySelectorAll("[data-password-toggle]")) {
  const input = document.getElementById(toggle.getAttribute("aria-controls"));
  toggle.addEventListener("click", () => {
    const showPassword = input.type === "password";
    input.type = showPassword ? "text" : "password";
    toggle.textContent = showPassword ? "Hide" : "Show";
    toggle.setAttribute("aria-pressed", String(showPassword));
    toggle.setAttribute(
      "aria-label",
      `${showPassword ? "Hide" : "Show"} ${input.id === "password" ? "password" : "password confirmation"}`,
    );
  });
}

function passwordChecks(password) {
  return {
    length: password.length >= 8 && password.length <= 128,
    uppercase: /\p{Lu}/u.test(password),
    lowercase: /\p{Ll}/u.test(password),
    number: /\p{N}/u.test(password),
    symbol: /[^\p{L}\p{N}\s]/u.test(password),
  };
}

function updatePasswordFeedback() {
  const checks = passwordChecks(passwordInput.value);
  for (const [requirement, element] of Object.entries(passwordRequirements)) {
    const met = checks[requirement];
    element.classList.toggle("requirement-met", met);
    element.setAttribute("aria-label", `${element.textContent}: ${met ? "met" : "not met"}`);
  }

  if (!confirmPasswordInput.value) {
    passwordMatchElement.textContent = "";
    passwordMatchElement.classList.remove("error");
  } else if (passwordInput.value === confirmPasswordInput.value) {
    passwordMatchElement.textContent = "Passwords match.";
    passwordMatchElement.classList.remove("error");
  } else {
    passwordMatchElement.textContent = "Passwords do not match.";
    passwordMatchElement.classList.add("error");
  }
}

passwordInput.addEventListener("input", updatePasswordFeedback);
confirmPasswordInput.addEventListener("input", updatePasswordFeedback);

function showMessage(message, isError = false) {
  messageElement.textContent = message;
  messageElement.classList.toggle("error", isError);
  messageElement.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  messageElement.hidden = true;
  messageElement.classList.remove("error");

  if (Object.values(passwordChecks(passwordInput.value)).some((met) => !met)) {
    showMessage("Please meet all password requirements before continuing.", true);
    passwordInput.focus();
    return;
  }

  if (passwordInput.value !== confirmPasswordInput.value) {
    showMessage("The passwords do not match.", true);
    confirmPasswordInput.focus();
    return;
  }

  submitButton.disabled = true;
  try {
    const response = await fetch("/api/v1/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: usernameInput.value.trim(),
        password: passwordInput.value,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      const detail = result.detail;
      const message = typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((error) => error.msg).join(" ")
          : "Registration could not be completed.";
      showMessage(message, true);
      return;
    }

    form.reset();
    showMessage(
      "The stars have opened your path. Return to the game and sign in to enter your realm.",
    );
  } catch (error) {
    console.error("Registration request failed.", error);
    showMessage("Registration could not be completed. Please try again.", true);
  } finally {
    submitButton.disabled = false;
  }
});
