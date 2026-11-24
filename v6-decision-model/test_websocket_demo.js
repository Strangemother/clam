"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function setup() {
  const ids = [
    "url", "connect", "disconnect", "send", "status", "responses",
    "theme", "prompt", "prompt-content", "state",
  ];
  const elements = Object.fromEntries(ids.map(id => [
    id, {value: "", textContent: "", disabled: false, dataset: {}},
  ]));
  elements.url.value = "ws://localhost:9999/chromite/";
  elements.prompt.dataset.url = "/ui/api/prompts/prompt-placeholder";
  const sockets = [];
  class WebSocket {
    constructor(url) {
      this.url = url;
      this.sent = [];
      sockets.push(this);
    }

    send(message) {
      this.sent.push(message);
    }

    close() {
      this.onclose({reason: ""});
    }
  }
  const context = {
    document: {
      querySelector: selector => elements[selector.slice(1)] || null,
      documentElement: {dataset: {}},
    },
    window: {matchMedia: () => ({matches: false})},
    localStorage: {getItem: () => null, setItem: () => {}},
    fetch: async () => ({
      ok: true, json: async () => ({yaml: "state: example\n"}),
    }),
    WebSocket,
    URL,
  };
  const source = fs.readFileSync(
    path.join(__dirname, "static/websocket_demo.js"), "utf8"
  );
  vm.runInNewContext(source, context);
  return {elements, sockets, context};
}

test("YAML selection, connection, state and formatted responses", async () => {
  const {elements: el, sockets, context} = setup();
  el.connect.onclick();
  assert.equal(sockets.length, 0);

  let fetched;
  context.fetch = async url => {
    fetched = url;
    return {ok: true, json: async () => ({yaml: "state: selected\n"})};
  };
  el.prompt.value = "chromite-3.d.yaml";
  const loading = el.prompt.onchange();
  assert.equal(el.url.value, "ws://localhost:9999/chromite-3/");
  await loading;
  assert.equal(fetched, "/ui/api/prompts/chromite-3.d.yaml");
  assert.equal(el["prompt-content"].value, "state: selected\n");
  el.url.value = "ws://example.com:1234/other/";
  el.connect.onclick();
  const socket = sockets[0];
  assert.equal(socket.url, "ws://example.com:1234/chromite-3/");
  assert.equal(el.prompt.disabled, true);
  socket.onopen();
  el.state.value = "A bird appears";
  el.send.onclick();
  assert.deepEqual(JSON.parse(socket.sent[0]), {state: "A bird appears"});
  socket.onmessage({data: '{"answer":{"value":1}}'});
  socket.onmessage({data: "plain text"});
  assert.equal(
    el.responses.textContent,
    '{\n    "answer": {\n        "value": 1\n    }\n}\nplain text\n'
  );
  socket.close();
  assert.equal(el.prompt.disabled, false);
  el.prompt.value = "";
  await el.prompt.onchange();
  assert.equal(el.url.value, "ws://example.com:1234/");
  el.connect.onclick();
  assert.equal(sockets.length, 1);
});

test("invalid proxy URLs are reported and cannot connect", async () => {
  const {elements: el, sockets} = setup();
  el.url.value = "ws://localhost:9999/chromite/?token=example";
  el.prompt.value = "chromite-3.d.yaml";
  await el.prompt.onchange();
  assert.match(el.status.textContent, /query or fragment/);
  el.connect.onclick();
  assert.equal(sockets.length, 0);
  assert.match(el.status.textContent, /query or fragment/);
  el.url.value = "wss://example.com:1234/other/";
  el.connect.onclick();
  assert.equal(sockets[0].url, "wss://example.com:1234/chromite-3/");
});

test("failed and stale prompt loads cannot be used", async () => {
  const {elements: el, sockets, context} = setup();
  let resolveFirst;
  context.fetch = url => {
    if (url.endsWith("first.d.yaml")) {
      return new Promise(resolve => { resolveFirst = resolve; });
    }
    return Promise.resolve({
      ok: false,
      json: async () => ({error: {message: "Bad YAML"}}),
    });
  };
  el.prompt.value = "first.d.yaml";
  const first = el.prompt.onchange();
  el.prompt.value = "second.d.yaml";
  await el.prompt.onchange();
  resolveFirst({ok: true, json: async () => ({yaml: "old"})});
  await first;
  assert.equal(el["prompt-content"].value, "");
  assert.match(el.status.textContent, /Bad YAML/);
  el.connect.onclick();
  assert.equal(sockets.length, 0);
});
