"use strict";

const url = document.querySelector("#url");
const connect = document.querySelector("#connect");
const disconnect = document.querySelector("#disconnect");
const send = document.querySelector("#send");
const message = document.querySelector("#message");
const image = document.querySelector("#image");
const prompt = document.querySelector("#prompt");
const promptContent = document.querySelector("#prompt-content");
const state = document.querySelector("#state");
const status = document.querySelector("#status");
const responses = document.querySelector("#responses");
const theme = document.querySelector("#theme");
const storedTheme = localStorage.getItem("websocket-proxy-theme");
let currentTheme = storedTheme || (
  window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark" : "light"
);
let socket;
let promptRequest = 0;
let promptLoaded = false;

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

if (prompt) {
  prompt.onchange = async () => {
    const request = ++promptRequest;
    promptLoaded = false;
    promptContent.value = "";
    if (!prompt.value) {
      status.textContent = "Select a prompt";
      return;
    }
    status.textContent = "Loading prompt...";
    try {
      const endpoint = prompt.dataset.url.replace(
        "prompt-placeholder", encodeURIComponent(prompt.value)
      );
      const response = await fetch(endpoint);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error?.message || "Could not load prompt");
      }
      if (request !== promptRequest) return;
      promptContent.value = data.yaml;
      promptLoaded = true;
      status.textContent = "Prompt loaded";
    } catch (error) {
      if (request === promptRequest) {
        status.textContent = `Could not load prompt: ${error.message}`;
      }
    }
  };
}

connect.onclick = () => {
  if (prompt && !promptLoaded) {
    status.textContent = "Select and load a prompt first";
    return;
  }
  try {
    if (prompt) {
      const address = new URL(url.value);
      address.pathname = `/${prompt.value.slice(0, -7)}/`;
      url.value = address.toString();
    }
    socket = new WebSocket(url.value);
  } catch (error) {
    status.textContent = `Connection error: ${error.message}`;
    return;
  }
  connect.disabled = true;
  if (prompt) prompt.disabled = true;
  status.textContent = "Connecting...";
  socket.onopen = () => {
    status.textContent = "Connected";
    disconnect.disabled = false;
    send.disabled = false;
  };
  socket.onmessage = event => {
    let output = event.data;
    try {
      output = JSON.stringify(JSON.parse(event.data), null, 4);
    } catch (error) {
      // Non-JSON messages are displayed unchanged.
    }
    responses.textContent += `${output}\n`;
  };
  socket.onerror = () => { status.textContent = "WebSocket error"; };
  socket.onclose = event => {
    status.textContent = `Disconnected${event.reason
      ? `: ${event.reason}` : ""}`;
    connect.disabled = false;
    disconnect.disabled = true;
    send.disabled = true;
    if (prompt) prompt.disabled = false;
  };
};
disconnect.onclick = () => socket.close();
send.onclick = () => {
  if (state) {
    socket.send(JSON.stringify({state: state.value}));
    status.textContent = "Connected";
    return;
  }
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
