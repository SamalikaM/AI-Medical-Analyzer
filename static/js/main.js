// Dark mode toggle, persisted per-session via a cookie-free approach:
// we just flip a data attribute + localStorage is unavailable to us here,
// so we set it on <html> and rely on a simple in-page memory + a plain
// server-rendered default. Kept intentionally tiny: no state library needed
// for one boolean.
(function () {
  const root = document.documentElement;
  const toggleBtns = document.querySelectorAll(".theme-toggle-btn");
  const stored = document.cookie.match(/theme=(dark|light)/);
  if (stored && stored[1] === "dark") root.setAttribute("data-theme", "dark");

  function setTheme(mode) {
    if (mode === "dark") root.setAttribute("data-theme", "dark");
    else root.removeAttribute("data-theme");
    document.cookie = `theme=${mode};path=/;max-age=31536000`;
  }

  toggleBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const isDark = root.getAttribute("data-theme") === "dark";
      setTheme(isDark ? "light" : "dark");
    });
  });
})();

// Drag-and-drop file selection. The actual upload is a plain native form
// submit (not XHR) so the browser follows Flask's redirect + one-time flash
// message itself -- an XHR-based upload previously consumed that flash
// message internally before the visible page ever reloaded, silently
// hiding rejection/error messages from the user.
(function () {
  const dropzone = document.getElementById("dropzone");
  if (!dropzone) return;
  const input = document.getElementById("file-input");
  const form = document.getElementById("upload-form");
  const submitBtn = form.querySelector("button[type=submit]");
  const fileNameEl = document.getElementById("selected-file-name");

  function showSelected(file) {
    if (file) fileNameEl.textContent = `Selected: ${file.name}`;
  }

  dropzone.addEventListener("click", () => input.click());
  dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      showSelected(e.dataTransfer.files[0]);
    }
  });
  input.addEventListener("change", () => showSelected(input.files[0]));

  form.addEventListener("submit", (e) => {
    if (!input.files.length) {
      e.preventDefault();
      alert("Please choose a file first.");
      return;
    }
    submitBtn.disabled = true;
    submitBtn.textContent = "Analyzing...";
    // no preventDefault -- let the browser submit and follow the redirect natively
  });
})();
