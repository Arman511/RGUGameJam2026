const form = document.querySelector("#delete-account-form");
const usernameInput = document.querySelector("#username");
const passwordInput = document.querySelector("#password");
const confirmationInput = document.querySelector("#confirmation");
const messageElement = document.querySelector("#form-message");
const submitButton = document.querySelector("#delete-account-button");
const successElement = document.querySelector("#deletion-success");

function showMessage(message, isError = false) {
  messageElement.textContent = message;
  messageElement.classList.toggle("error", isError);
  messageElement.hidden = false;
}

async function responseMessage(response, fallback) {
  const result = await response.json();
  const detail = result.detail;
  return typeof detail === "string" ? detail : fallback;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  messageElement.hidden = true;
  messageElement.classList.remove("error");

  if (confirmationInput.value !== "DELETE") {
    showMessage('Type DELETE exactly to confirm account deletion.', true);
    confirmationInput.focus();
    return;
  }

  submitButton.disabled = true;
  try {
    const loginResponse = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: usernameInput.value.trim(),
        password: passwordInput.value,
      }),
    });
    if (!loginResponse.ok) {
      showMessage(await responseMessage(loginResponse, "Sign-in failed."), true);
      return;
    }

    const { token } = await loginResponse.json();
    const deletionResponse = await fetch("/api/v1/auth/account", {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!deletionResponse.ok) {
      showMessage(
        await responseMessage(deletionResponse, "Account deletion could not be completed."),
        true,
      );
      return;
    }

    form.reset();
    form.hidden = true;
    messageElement.hidden = true;
    successElement.hidden = false;
    successElement.focus();
  } catch (error) {
    console.error("Account deletion request failed.", error);
    showMessage("Account deletion could not be completed. Please try again.", true);
  } finally {
    submitButton.disabled = false;
  }
});
