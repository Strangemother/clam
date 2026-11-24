"use strict";

const url = document.querySelector("#url");
const connect = document.querySelector("#connect");
const disconnect = document.querySelector("#disconnect");
const send = document.querySelector("#send");
const message = document.querySelector("#message");
const image = document.querySelector("#image");
const status = document.querySelector("#status");
const responses = document.querySelector("#responses");
const theme = document.querySelector("#theme");
const storedTheme = localStorage.getItem("websocket-proxy-theme");
let currentTheme = storedTheme || (
  window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark" : "light"
);
let socket;

function setTheme(value) {
  currentTheme = value;
  document.documentElement.dataset.theme = value;
  theme.textContent = value === "dark"
    ? "Use light mode" : "Use dark mode";
}

setTheme(currentTheme);
theme.onclick = () => {
  setTheme(currentTheme === "dark" ? "light" : "dark");
  localStorage.setItem("websocket-proxy-theme", currentTheme);
};

connect.onclick = () => {
  try {
    socket = new WebSocket(url.value);
  } catch (error) {
    status.textContent = `Connection error: ${error.message}`;
    return;
  }
  connect.disabled = true;
  status.textContent = "Connecting...";
  socket.onopen = () => {
    status.textContent = "Connected";
    disconnect.disabled = false;
    send.disabled = false;
  };
  socket.onmessage = event => {
    responses.textContent += `${event.data}\n`;
  };
  socket.onerror = () => { status.textContent = "WebSocket error"; };
  socket.onclose = event => {
    status.textContent = `Disconnected${event.reason
      ? `: ${event.reason}` : ""}`;
    connect.disabled = false;
    disconnect.disabled = true;
    send.disabled = true;
  };
};
disconnect.onclick = () => socket.close();
send.onclick = () => {
  if (message) {
    try {
      JSON.parse(message.value);
    } catch (error) {
      status.textContent = `Invalid JSON: ${error.message}`;
      return;
    }
    socket.send(message.value);
    status.textContent = "Connected";
    return;
  }

  const file = image.files[0];
  if (!file) {
    status.textContent = "Choose an image first";
    return;
  }
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
    status.textContent = "Choose a JPEG, PNG, or WebP image";
    return;
  }
  const connection = socket;
  const reader = new FileReader();
  reader.onerror = () => { status.textContent = "Could not read image"; };
  reader.onload = () => {
    const payload = JSON.stringify({image: reader.result});
    if (new Blob([payload]).size > 64 * 1024 * 1024) {
      status.textContent = "Image message exceeds the 64 MiB limit";
      return;
    }
    if (connection.readyState !== WebSocket.OPEN) {
      status.textContent = "Disconnected before image was ready";
      return;
    }
    connection.send(payload);
    status.textContent = "Image sent";
  };
  reader.readAsDataURL(file);
};
