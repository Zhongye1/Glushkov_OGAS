// 拷贝 manifest 与静态 HTML 到 dist
import { cpSync, mkdirSync } from "node:fs";

mkdirSync("dist", { recursive: true });
cpSync("manifest.json", "dist/manifest.json");
for (const dir of ["sidepanel", "popup"]) {
  mkdirSync(`dist/${dir}`, { recursive: true });
  cpSync(`${dir}/index.html`, `dist/${dir}/index.html`);
}
