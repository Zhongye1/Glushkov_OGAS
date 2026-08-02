# 目标文件结构参考

这是本套 spec 所描述架构的目标 monorepo 结构，作为 design 文档里「影响的包」引用的落点参考。分层依赖方向：apps 引用 packages/features，features 引用 ui，ui 引用 core，core 引用 platform。越往下越稳定、越与环境无关。apps 之间横向绝不互相引用。

```
frontend/                         # monorepo 根（pnpm workspace + turbo）
├── package.json
├── pnpm-workspace.yaml
├── turbo.json
├── tsconfig.base.json
├── lefthook.yml
├── .changeset/
│
├── specs/                             # 规格单一事实源(本目录)
│   ├── overview.md
│   ├── adr/                           # 架构决策记录,只增不改
│   ├── features/                      # 功能规格,requirements/design/tasks
│   └── templates/
│
├── apps/                              # 运行时入口层 —— 互不依赖
│   ├── web/                           # 唯一带 SSR 的 target(Next.js App Router)
│   │   ├── app/                       # App Router:服务端组件优先
│   │   │   ├── layout.tsx             # 根布局 = app-shell,SSR 直出外壳
│   │   │   ├── (chat)/c/[id]/page.tsx # 对话页:历史 SSR,实时区 "use client"
│   │   │   ├── share/[token]/page.tsx # 分享页,SSR + 可抓取
│   │   │   └── kb/[docId]/page.tsx    # 知识库公开页,SSR / ISR
│   │   └── src/
│   │       ├── platform-web.ts        # 注入 web 版 platform 实现
│   │       └── providers.tsx
│   ├── desktop/                       # Electron(纯 CSR)
│   │   ├── electron/                  # 主进程 + ipc
│   │   ├── preload/bridge.ts
│   │   └── renderer/                  # Vite 打包的 CSR
│   │       └── platform-electron.ts   # 注入 electron 版 platform(走 IPC)
│   └── extension/                     # 浏览器扩展(纯 CSR,MV3)
│       ├── background/ content/ sidepanel/ popup/
│       └── platform-extension.ts      # 注入扩展版 platform(chrome.*)
│
├── packages/                          # 跨运行时共享 —— 越靠下越稳定
│   ├── platform/                      # 枢纽:只有接口,无实现
│   │   └── src/{types.ts, context.tsx, index.ts}
│   ├── core/                          # 逻辑层 —— 100% 复用,零 UI
│   │   └── src/{api/, store/{atoms,entities}, stream/, message-adapter/, query.ts, types/}
│   ├── ui/                            # 通用组件 —— 环境无关
│   │   └── src/{prompt-input/, editor/, chat-layout/, app-sidebar/, primitives/}
│   └── features/                      # 业务模块 —— 环境无关,靠 platform 注入
│       └── src/{stream/, chat/, project/, task-center/, skill/, tools/, generative-ui/, otp-auth/}
│
├── shared/                            # 跨端纯契约
│   └── src/{schema/, generated/, constants/}
│
├── docs/                              # 面向读者的现状文档
└── notes/                             # 研发过程记录
```

## 让架构不腐化的两条硬约束

第一，单向依赖用 dependency-cruiser 强制。声明 apps 可引用任意 packages；features 可引用 ui、core、platform，反向不行；core 与 platform 不引用任何上层。谁写了反向依赖，CI 直接红。

第二，下层禁摸环境全局。core、ui、features 里出现 window、document、chrome、process 或 Electron 相关标识一律 lint 报错，需要环境能力时只能走 usePlatform()。这条是保证同一份组件三端都能跑且 SSR 端不炸的底线。
