"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loginForm");
  const status = document.getElementById("loginStatus");
  const username = document.getElementById("username");
  const password = document.getElementById("password");

  form.addEventListener("submit", event => {
    event.preventDefault();
    const user = username.value.trim();
    const pass = password.value.trim();

    if (!user || !pass) {
      setStatus("Please enter both username and password.", "err");
      return;
    }

    setStatus("Signing in…", "ok");
    localStorage.setItem("stegavault_user", user);
    setTimeout(() => {
      window.location.href = "/";
    }, 700);
  });

  function setStatus(message, type = "ok") {
    status.textContent = message;
    status.className = "status-msg" + (type === "err" ? " err" : "");
  }
});
