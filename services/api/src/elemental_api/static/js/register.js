const form = document.querySelector("#register-form");
const usernameInput = document.querySelector("#username");
const passwordInput = document.querySelector("#password");
const confirmPasswordInput = document.querySelector("#confirm-password");
const messageElement = document.querySelector("#form-message");
const submitButton = document.querySelector("#register-button");

function showMessage(message, isError = false) {
  messageElement.textContent = message;
  messageElement.classList.toggle("error", isError);
  messageElement.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  messageElement.hidden = true;
  messageElement.classList.remove("error");

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
