export interface Platform {
  readonly name: "web" | "desktop" | "extension";
  openUrl(url: string): Promise<void>;
  readClipboard(): Promise<string>;
  writeClipboard(text: string): Promise<void>;
}

export type { Platform as PlatformLike };
