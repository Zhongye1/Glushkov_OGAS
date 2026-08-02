// preload：向 renderer 暴露受限能力（占位）
const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("ogasBridge", {
  version: "0.0.0",
});
