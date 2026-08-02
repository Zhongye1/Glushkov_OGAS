/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "no-circular",
      severity: "error",
      comment: "禁止循环依赖",
      from: {},
      to: { circular: true },
    },
    {
      name: "no-orphans",
      severity: "warn",
      from: { orphan: true, pathNot: ["src/index\\.ts$", ".*\\.test\\.[jt]sx?$"] },
      to: {},
    },
    {
      name: "enforce-layering",
      severity: "error",
      comment: "单向依赖：apps → features → ui → core → platform；shared 全仓可依赖",
      from: { path: "^packages/(core|ui|features)/src" },
      to: { path: "^apps/", pathNot: "^packages/(platform|core)/" },
    },
    {
      name: "no-upward-deps",
      severity: "error",
      comment: "core 与 platform 不引用任何上层；下层包不得引用上层包",
      from: { path: "^packages/(core|platform)/src" },
      to: { path: "^packages/(ui|features)/|^apps/" },
    },
    {
      name: "no-app-cross-refs",
      severity: "error",
      comment: "apps 之间互不引用",
      from: { path: "^apps/" },
      to: { path: "^apps/", pathNot: "^apps/[^/]+/src/" },
    },
    {
      name: "services-via-facade-only",
      severity: "error",
      comment: "services 之间不互相 import，只经 Dispatcher facade 通信",
      from: { path: "^services/" },
      to: { path: "^services/", pathNot: "^services/dispatcher/src/" },
    },
    {
      name: "no-shared-reverse-deps",
      severity: "error",
      comment: "shared 是全仓契约层，禁止被反向依赖的包依赖它（allowed：任何 TS 侧可依赖 shared）",
      from: { path: "^shared/src" },
      to: { path: "^shared/src" },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    exclude: { path: "(dist|build|coverage|node_modules|\\.next|out)/" },
    tsConfig: { fileName: "tsconfig.json" },
    reporterOptions: {
      dot: { collapsePattern: "node_modules/[^/]+" },
    },
  },
};
