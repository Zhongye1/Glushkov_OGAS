{
  description = "Glushkov OGAS monorepo 开发环境（Linux/macOS 原生；Windows 用 WSL2 或 .devcontainer）";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            # 语言运行时（与根 package.json / go.work / pyproject.toml 对齐）
            nodejs_22
            go # go.work 要求 1.25+，如需精确固定改为 go_1_25
            python312 # arkhiv 要求 >= 3.11

            # 常用开发工具
            git
            jq
            ripgrep
            gnumake
            sqlite # liskin 上游使用 SQLite
            docker-compose # 服务依赖（postgres/milvus）走 infra/compose
          ];

          shellHook = ''
            # 用 corepack 锁定 pnpm 版本，与 package.json#packageManager 一致
            corepack enable
            corepack prepare pnpm@11.14.0 --activate

            echo ""
            echo "✦ OGAS devShell"
            echo "  node: $(node --version)  pnpm: $(pnpm --version)  go: $(go version | awk '{print $3}')  python: $(python3 --version)"
            echo "  服务依赖（postgres/milvus）: docker compose -f infra/compose/docker-compose.yml up -d"
            echo "  首次使用: pnpm install && pnpm build"
            echo ""
          '';
        };
      });
}
