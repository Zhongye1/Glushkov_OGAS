// Electron 版 platform 实现（走 IPC），待注入
import type { Platform } from "@ogas/platform";

export const platformElectron: Platform = {
  name: "desktop",
  openUrl: async (url) => {
    window.open(url, "_blank");
  },
  readClipboard: async () => "",
  writeClipboard: async () => {},
};
