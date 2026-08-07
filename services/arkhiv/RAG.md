
目前RAG系统的主流是 Agentic RAG: 把检索、路由、记忆、工具调用模块化，甚至让 agent 自主决定 "要不要检索、检索几轮、检索哪个库", 走向多路召回和迭代检索。

当前的主要需求是在研发流程的编码一环，实现code agent 的业务知识自主检索：通过业务知识库 RAG MCP Server，覆盖飞书文档、PDF、Word、Markdown 等多种格式，支持嵌套表格、图文混排等复杂内容的解析，打通文档解析、切片、向量化与检索的全链路，使 Agent 可自主检索业务知识，缓解模型缺乏领域上下文导致的幻觉，为代码生成提供事实依据。


其需求一致性较高，在设计阶段都是走一条标准 pipeline
1. 文档解析与分块 (Chunking)—— 最影响效果的一环。主流做法是语义分块 / 递归分块 / 按标题层级分块，配合 chunk overlap; 近两年流行 父子分块 (small-to-big): 检索用小块保证精度，喂给 LLM 用大块保证上下文完整。
2. Embedding 向量化—— 选一个强 embedding 模型 (bge、E5、OpenAI text-embedding-3、Cohere embed 等), 中文场景常用 bge-m3。
3. 混合检索 (Hybrid Search)——向量检索 + 关键词检索 (BM25) 融合, 几乎是共识：向量管语义、BM25 管精确术语 / 专名，用 RRF (Reciprocal Rank Fusion) 融合两路结果。
4. 重排 (Reranking)—— 用 cross-encoder reranker (如 bge-reranker、Cohere Rerank) 对召回的候选做精排，只把最相关的少数 chunk 送进 LLM。这一步性价比极高。
5. 上下文构造与生成—— 把精排后的 chunk 拼 prompt, 要求模型基于给定上下文作答并给出引用, 降低幻觉。
6. 评估 (Evaluation)—— 用 RAGAS 这类框架量化 faithfulness (忠实度)、answer relevancy、context precision/recall, 形成 "改一版就跑一次评测" 的闭环。这是从 demo 走向生产的分水岭。

下面简谈其设计：

---

RAG 平台项目设计方案

一、项目背景与目标
1.1 业务背景与要解决的问题

团队内部沉淀了大量代码库、技术文档和历史资料,但检索方式仍停留在关键字匹配,既不理解语义,也无法把散落在多处的信息聚合成一个可直接使用的答案。与此同时,编码 agent 正在成为日常开发的一环,它们需要一个标准化的入口去获取代码上下文和文档知识。这两类需求——人通过 web 提问、agent 通过工具调用——底层要解决的其实是同一件事:把非结构化的内部知识,变成可被语义检索、可带来源引用的可信答案。
当前缺的正是这样一个统一的 RAG 平台。

1.2 项目目标:统一 RAG 内核,对外提供两类能力
核心目标是建设一套协议无关的 RAG 内核,把数据接入、切分、向量化、检索、重排、生成这条链路做扎实、做统一,然后在同一个内核之上包出两层不同的对外能力。内核只写一遍是这个项目最重要的原则,它保证 agent 侧和 web 侧拿到的检索结果、引用来源、召回质量完全一致,不会因为两套实现而行为漂移。

1.3 两个核心交付物界定
第一个交付物是面向 coding agent 的 MCP 服务,让 Cursor、Claude Code 以及内网编码 agent 能把本平台当成一个标准工具来调用,拿到结构化的代码片段和文档证据。第二个交付物是面向 web 的 REST API 服务,打通 Next.js 前端,给终端用户提供带流式输出和引用来源的完整问答体验。两者共享内核,差异只在最外层的协议外壳。

1.4 非目标(明确本期不做的范围)
本期不自建或微调基础模型 , embedding、rerank、生成模型一律走现成的 API 渠道，
1.5 名词与术语表
术语
含义
Embedding
把文本编码成向量,用于语义相似度检索,由专门的编码模型产出
Rerank
对初步召回的候选做交叉编码打分,精排出更相关的结果
ANN
近似最近邻检索,用少量精度损失换数量级的检索速度
RRF
Reciprocal Rank Fusion,把多路召回结果融合成一个排序
MCP
Model Context Protocol,让 agent 以标准方式发现和调用外部工具与数据的开放协议
SSE
Server-Sent Events,服务端向浏览器持续推送的单向流,用于流式返回答案
语义缓存
按 query 语义等价性命中的缓存,可直接跳过检索与生成

二、总体架构设计
2.1 架构总览与分层理念:内核与协议外壳分离
整个平台从下到上分三层:最底是协议无关的 RAG 内核,只暴露 retrieve() 和 answer() 两个语义化入口;中间是协议适配层,MCP server 和 REST API 各自把外部协议翻译成对内核的调用;最上是接入层,Go 网关承接对外的高并发连接。这种分层的价值在于:任何一端都不允许自己写检索或调模型的逻辑,新增一种对外协议时只需再加一层薄适配,内核完全不动。

2.2 端到端链路
Web 链路是 Next.js SSR → Go 网关 → FastAPI(REST),用户的问答请求经网关鉴权限流后转发到 FastAPI,由内核完成检索加生成,再以 SSE 流式经网关透传回前端。Agent 链路是 Coding Agent → MCP Server → RAG 内核,agent 把平台注册为工具,调用时直接命中内核的检索能力,拿到结构化片段自行推理。两条链路在内核处汇合,共用同一批下游客户端和缓存。

2.3 组件职责划分
Go 网关只做连接层的事:鉴权、路由、限流削峰、SSE 透传,不承载任何 AI 逻辑。**RAG 核心(FastAPI + 内核库)**是全部智能所在,负责编排检索与生成。**前端(Next.js SSR)**负责问答交互与来源展示,SSR 保证首屏和 SEO。存储层由向量库、Redis 缓存、元数据存储组成,支撑检索与多级缓存。

2.4 技术选型总述与取舍依据
编排层选 FastAPI,原因是 RAG 是典型的 I/O 密集负载,请求时间几乎都花在等 embedding、等向量库、等 LLM 上,ASGI 异步模型能用少量线程扛住大量并发等待;更关键的是 Python 独占了 RAG 的工具生态,Web 层和 AI 逻辑同语言,迭代速度是压倒性优势 [2]。网关层可选 Go/Hertz,因为对外连接层是纯网关活儿——鉴权、限流、流式转发,goroutine 处理海量并发连接又快又省,且内网 Hertz 是基础设施标配 [3]。这套"Go 扛连接、Python 做编排"的分工,让高并发管理和快速演进的算法逻辑各归其位。

2.5 架构图
逻辑架构自上而下为"接入层(网关)→ 协议层(MCP/REST)→ 内核层(retrieve/answer)→ 存储层(向量库/缓存/元数据)→ 外部模型(embedding/rerank/生成)";部署架构上网关、rag-core、web 各为独立部署单元,向量库与 Redis 为共享中间件;数据流分两条,离线是"数据源 → 切分 → 向量化 → 入库",在线是"query → 缓存 →(未命中)检索 → 重排 →(可选)生成 → 返回"。(此处配三张图,正文略。)

三、RAG 核心能力设计(协议无关内核)
3.1 内核定位:与协议解耦,只暴露 retrieve() / answer()
内核是一个不依赖任何 Web 框架的纯 Python 库,对外只给两个方法:retrieve(query, top_k, filters) 返回排好序的片段列表,answer(query, ...) 在检索基础上再做生成并返回带引用的答案。MCP 侧主要调 retrieve(),REST 侧主要调 answer()。所有协议外壳都只是把入参出参在自己的协议格式和这两个方法之间做翻译。

3.2 数据接入与预处理
数据源覆盖代码库、文档和 Web 三类,通过统一的 loader 接口接入,每类源实现自己的抓取和解析。预处理最影响最终效果的是切分策略:朴素的固定行切分会把一个函数从中间截断,更好的做法是按语法结构切分——用 Tree-sitter 之类的解析器把代码拆成函数、类、方法这样的完整语义单元,切分时带上文件路径、所属类/函数名、import 等上下文一起入库,增强可检索性。文档则按标题层级和段落切,尽量保持语义完整。

3.3 向量化(Embedding)
向量化必须用专门的编码模型,而不是生成式大模型——生成模型没有 embedding 端点,架构上也不适合做向量化,这是两类模型的根本区别。选型上通用文本可用 bge-m3 这类,代码检索则优先代码专用的 code-embedding 模型。内网落地时,embedding 走现成 API 渠道:火山方舟 Ark 提供 doubao-embedding 系列(OpenAI 兼容),内网也有 Flow encoder、VikingDB embedding 等可选通道,按 QPS 需求和数据安全等级选择,避免自建部署的运维负担。

3.4 检索层
向量检索基于 ANN 近似最近邻,用 HNSW 或 IVF 索引把精确最近邻换成"足够近",以少量召回精度换数量级的速度,这是向量库能抗高 QPS 的算法基础。单纯向量召回不够,要做混合检索:向量召回负责语义相似,叠加 BM25/关键字做精确匹配(尤其代码里的符号名、API 名),最后用 RRF 把多路结果融合成一个排序。此外可选代码图扩展,在向量之外建一层调用/继承/引用关系图,检索时顺着"谁调用了这个函数""父类是谁"扩展上下文,类似 GraphRAG 的思路——这一项作为增强能力,视效果收益决定是否本期上。

3.5 重排(Rerank)与查询改写
初步召回的 Top-N 再过一遍 rerank 模型做交叉编码精排,把最相关的几条顶到前面,显著提升进入 prompt 的片段质量。rerank 走内网现成模型(如 doubao rerank)。查询侧做查询改写:对口语化或含指代的 query 先做归一和扩展(必要时拆成子查询多路召回),提升召回覆盖率。

3.6 生成(Generation)
生成模型走内网 API 渠道,火山方舟 Ark 的 doubao-pro、DeepSeek 系列等按需选择,Ark 提供 OpenAI 兼容接口便于接入。Prompt 编排把重排后的片段按相关度和 token 预算拼进上下文,并强制模型基于给定证据作答、标注引用来源。引用来源拼装是这一步的重点:每个片段回填文件路径、行号、来源链接,让最终答案可溯源、可点击跳转,这也是 RAG 相比裸 LLM 的核心价值。

3.7 内核对外接口契约
两个入口的契约大致如下,MCP 和 REST 都基于它翻译:
- retrieve(query: str, top_k: int, filters: dict) -> list[Chunk],Chunk 含 text / source_path / line_range / score / source_url。
- answer(query: str, top_k: int, stream: bool, filters: dict) -> Answer | AsyncIterator[Token],Answer 含 text / citations(list[Chunk]) / usage;stream=True 时返回 token 异步流。
四、MCP 服务设计(面向 coding agent)

4.1 MCP 协议定位与适用场景
MCP 是 Anthropic 提出、现被各家 coding agent 广泛支持的开放协议,让模型以标准方式发现和调用外部工具与数据源 [1]。agent 接上本平台的 MCP server 后,就能把 RAG 当成一个工具随时调用,而不必关心底层实现。

4.2 能力暴露方式:Tools vs Resources 的取舍
MCP 里 Resources 偏只读数据、Tools 偏可执行动作。对 coding agent,最实用的是暴露成 Tools,因为 agent 需要带参数主动发起检索,而不是被动读取固定资源。因此本平台把能力全部设计为 tool。

4.3 工具设计
规划两个核心工具:search_codebase(query, top_k) 返回相关代码片段,ask_docs(question) 返回文档证据。返回一律是结构化片段,带文件路径、行号、来源链接,而不是糊一大段文本,因为这些内容会直接进 agent 的上下文窗口,冗余就是浪费 token。策略上遵循**"给料而非给结论"**:MCP 侧默认只做检索加重排、返回 Top-K 原始片段,把要不要生成、怎么推理留给 agent 自己——这正是 agent 消费者和终端用户的本质差异。

4.4 传输方式选择:stdio vs Streamable HTTP
MCP 支持 stdio(本地进程,agent 直接拉起)和 Streamable HTTP(远程服务)两种。本平台是中心化部署、多人共用,因此选 Streamable HTTP,stdio 仅在个别本地调试场景保留。官方 Python SDK 提供了快速搭 server 的能力,把内核方法注册成 tool 即可 [4]。

4.5 鉴权与配额
远程 MCP 走 agent token 鉴权,每个接入方分配独立 token,便于溯源和吊销;配套按 token 做限流和配额,防止单个 agent 打满检索资源。

4.6 与内核的调用关系

MCP 适配层只调内核的 retrieve(),拿到 list[Chunk] 后裁剪成适合 agent 的结构化返回,不触碰生成逻辑。

五、REST API 服务设计(面向 web)

5.1 接口定位:面向终端用户的完整问答
REST 侧消费者是 web 前端和终端用户,要的是可读的完整答案加引用来源,而非原始片段,因此默认要走生成。

5.2 主要接口设计
规划三类接口:问答接口(提交 query、返回流式答案)、检索接口(只返回片段,供前端做"引用来源"展开)、会话接口(多轮上下文管理)。接口契约由 FastAPI 自动导出的 OpenAPI 描述,作为前端生成客户端的唯一来源。

5.3 流式返回(SSE)设计与网关透传
问答默认用 SSE 边生成边推送,大幅降低用户感知延迟。SSE 流从 FastAPI 出发,经 Go 网关原样透传到浏览器,网关不缓冲、不改写,保证 token 实时到达。

5.4 生成 + 引用来源的返回结构
返回体包含答案正文和 citations 数组,每条引用带路径、行号、来源链接,前端据此渲染可点击的溯源角标。

5.5 鉴权(用户会话 / 网关鉴权)
REST 侧走用户会话鉴权,由 Go 网关统一校验登录态和权限,后端 FastAPI 信任网关传递的用户身份,不重复做重登录逻辑。

5.6 与内核的调用关系
REST 适配层调内核的 answer(stream=True),把 token 流转成 SSE 事件输出。

六、API 网关设计(Go / Hertz)

6.1 网关职责
网关只做四件事:鉴权、路由、限流、SSE 透传,是一个不含 AI 逻辑的薄连接层。

6.2 为何用 Go 承接高并发连接层
RAG 请求 90% 的时间在等下游 LLM,编排层快几毫秒对端到端延迟影响很小,但连接管理在高并发下是实打实的开销。Go 的 goroutine 极其轻量,单机能扛的连接数和吞吐明显高于 Python,且编译型、无 GIL、内存占用低,做纯网关性价比最高;内网选 Hertz 还能直接对接现有 IDL 生态 [3]。

6.3 与后端 FastAPI 的通信(REST / gRPC 取舍)
网关到 FastAPI 的内部通信,本期建议先走 REST/JSON + SSE 透传,实现简单、调试直观、天然支持流式;若后续对内部调用的类型强约束和性能有更高要求,再演进到 gRPC(需处理流式与 Python 侧的 stub 生成)。这是一处待决策点,见 14.2。

6.4 限流、削峰与降级策略入口
网关是限流削峰的第一道闸:用令牌桶做入口限流,过载时按策略降级——要么排队等待,要么降级为"只返回检索结果不生成",而不是把后端 GPU 打爆导致雪崩。

七、高并发与性能设计(抗十万并发)
7.1 瓶颈分析:压力集中在生成层
一条 RAG 请求里,query 预处理、embedding、ANN 检索、rerank 都是毫秒级且易水平扩展,唯有 LLM 生成动辄数百毫秒到数秒、吃显存、单卡并发上限低。所以十万并发的账,本质是算需要多少卡跑生成,以及怎么让大部分请求根本走不到生成这一步。

7.2 多级缓存
最外层做语义缓存:对 query 做 embedding、在小向量库里查相似度,超过阈值即命中,直接返回上次答案,连检索和生成都省掉。线上问题长尾加热点并存,热点一旦被缓存,能削掉一大截生成流量,这是压住并发最关键的一招。往里一层做检索结果缓存和 embedding 缓存,同一 query 的向量和 Top-K 文档按哈希缓存到 Redis,让重复请求跳过 embedding 和 ANN。

7.3 检索层水平扩展:分片 + 多副本 + 无状态
检索层相对好扩:向量库按 shard 切开分散数据,每个 shard 多副本让读请求水平摊开,副本数随 QPS 线性加;embedding 服务无状态,直接多实例加负载均衡横向扩容。

7.4 生成层优化
提高单卡吞吐靠推理引擎——用 vLLM、TensorRT-LLM 这类引擎的连续批处理(continuous batching),动态把新请求插进正在跑的 batch 让 GPU 满载,配合 PagedAttention 高效管理 KV Cache,单卡有效并发能翻好几倍 [5]。削峰靠请求队列把瞬时洪峰摊平成平稳速率,配合限流和降级。分级路由进一步省钱:简单高频问题走小模型或直接返回检索,复杂问题才上大模型。(内网若统一走 Ark 等托管推理,则这一节聚焦在路由与队列,推理引擎优化由平台侧负责。)

7.5 流式返回对体验与稳定性的作用

流式不减少总计算量,但把"等整段生成完"变成"边生成边吐字",大幅降低感知延迟,也让连接和资源释放更平滑,对高并发下的体验和稳定性都有正面作用。

7.6 容量评估与压测方案
按"热点命中率 × 缓存拦截比例"倒推真正落到生成层的有效 QPS,据此估算卡数;压测覆盖缓存命中/未命中两种路径,分别测检索层和生成层的极限,并验证过载时的降级行为是否符合预期。配套引入效果评测(见 11.4 的 Ragas/Langfuse),性能压测的同时监控召回质量不因缓存和降级而劣化。

八、工程结构与 Monorepo 组织
8.1 顶层划分:apps/ + packages/
顶层分 apps/(可独立部署的服务)和 packages/(共享代码),三个服务天然对应三个 app,共享层聚焦 API 契约。
RAG/
├── apps/
│   ├── gateway/            # Go 网关 (Hertz)
│   ├── rag-core/           # Python FastAPI + RAG 内核
│   └── web/                # Next.js SSR
├── packages/
│   ├── contracts/          # API 契约 (OpenAPI / Protobuf)
│   ├── ts-sdk/             # 由契约生成的 TS 客户端
│   └── ui/                 # 前端共享组件(可选)
├── docker-compose.yml
├── Taskfile.yml
└── README.md

8.2 三个应用的原生工程结构
每个 app 保留自己语言的原生工具链,不强行统一:rag-core 用 pyproject.toml + uv + src layout;gateway 是标准 Go module;web 是 Next.js 的 package.json。Monorepo 让它们并排共存、边界清晰,而不是揉成一坨。

8.3 共享层:API 契约(contract-first)
跨语言协作最容易踩接口对不齐的坑,解法是契约先行:REST 走 OpenAPI(以 FastAPI 自动导出的 schema 为源),内部 RPC 若上 gRPC 则走 Protobuf,契约放 packages/contracts,由它生成前端 TS 客户端和 Go client。契约是唯一事实来源,各语言客户端由它生成而非手写——这是 monorepo 相比多仓最大的价值,契约和三端代码在同一次提交里原子地一起改。

8.4 任务编排:Makefile/Taskfile(全局)+ Turborepo(仅 TS)
三种语言意味着三套命令,顶层用 Taskfile 封装 task dev / test / gen 作为语言无关的统一入口;前端那半边(web + packages 的 TS)再套一层 Turborepo 做增量构建和缓存 [6]。要注意 Turborepo 管不了 Go 和 Python,所以分工是 Taskfile 管跨语言顶层编排、Turborepo 只管 TS。

8.5 本地开发:docker-compose 一键起全套
docker-compose.yml 把 gateway、rag-core、web,加向量库和 Redis 都定义成 service,docker compose up 起一整套,新人 clone 即可跑。

8.6 依赖隔离与按变更范围触发的 CI
每个 app 的依赖只装在自己目录下,Python venv、Go module cache、Node modules 各自独立,monorepo 共享的是代码和契约而非运行时依赖。CI 按路径过滤触发,只有对应目录变了才跑对应流水线,契约变更则触发所有下游重新生成加校验。

九、Python 工程化规范
9.1 依赖与环境
一切以 pyproject.toml 为中心,包管理用 uv——Rust 实现,速度比 pip/Poetry 快一个量级,同时管虚拟环境、依赖解析、锁文件和 Python 版本 [7]。必须有锁文件(uv.lock)锁死间接依赖版本,保证本地、CI、生产环境一致;生产依赖和开发依赖分组声明,部署镜像不混入测试工具。

9.2 项目结构:src layout 与分层职责
采用 src layout,源码放 src/myapp/ 下,强制以已安装包方式导入,提前暴露打包问题 [8]。内部按职责分层:api 管接口和校验,mcp 管 MCP 适配,services/rag 放编排与内核逻辑,clients 封装所有外部调用(LLM、向量库)以便 mock,core 收口配置与日志。

9.3 代码质量工具链:Ruff + mypy + pytest + pre-commit
Ruff 一个工具替代 flake8 + isort + black,极快,linting 和格式化都做 [9];mypy 做静态类型校验,RAG 里数据结构多,类型标注能省大量低级 bug;pytest 加 pytest-cov、pytest-asyncio 覆盖异步接口,测试分 unit 和 integration 两层;pre-commit 把这些串进 git 钩子,提交时自动跑、不合格拦下,CI 里再跑一遍做双保险 [10]。

9.4 引入库的取舍原则
能用标准库就不引三方库;选库看四个信号——是否活跃维护、社区体量、是否带类型标注、许可证是否合规;锁死版本并用 Renovate 定期提醒升级安全补丁;警惕依赖膨胀,LangChain 这类框架会拖进大量间接依赖,若只用一小部分功能,直接调模型 SDK 加自写几十行编排反而更干净。

十、数据与存储设计
10.1 向量库选型
向量库要求支持 HNSW/IVF、分片多副本、混合检索。开源自建可选 Milvus,内网托管可用 VikingDB(提供 recall/raw_embedding 等 API,省去自运维)。本期倾向内网 VikingDB 降低运维成本,保留 Milvus 作为可迁移的抽象接口,通过 clients 层封装以便替换。

10.2 缓存存储
用 Redis 承载语义缓存和检索结果缓存,读取微秒级;语义缓存另配一个小向量索引做相似度匹配。

10.3 元数据与来源存储
片段的元数据(文件路径、行号、来源链接、所属库/文档)与向量一起存,保证每条召回都能回填可点击的溯源信息。

10.4 数据更新:增量切分与向量化
靠文件/chunk 的内容哈希做脏标记,只对改动的文件重新切分和向量化,与 IDE 索引的增量思路一致,避免全量重建。

十一、部署与运维
11.1 部署形态
MCP 与 REST 可以同进程起两个 server(共享内核和下游客户端,省资源),也可以拆成两个部署单元(独立扩缩容)。本期建议先同进程部署快速上线,待 agent 和 web 流量画像分化后再按需拆分。

11.2 扩缩容策略
检索层无状态、可随 QPS 线性扩副本;生成层(或生成调用的并发配额)按有效 QPS 单独评估扩容,两层解耦、分别伸缩。

11.3 配置与密钥管理
用 Pydantic Settings 从环境变量读配置,密钥(模型 API key、库连接串)一律走环境变量或密钥管理服务注入,不硬编码进代码、不入库。

11.4 监控与可观测性(含效果评测——本次补充选型)
这是本次补充的关键一环。运行指标层面监控延迟、缓存命中率、生成耗时、错误率、各下游调用的 P99;LLM 与 RAG 链路的可观测性引入 Langfuse,它专门做 LLM 应用的 tracing、评测和监控,能把一次问答里的检索、rerank、生成每一步的输入输出、耗时、token 消耗完整串成一条 trace,便于定位"答得慢/答得偏"到底出在哪一环 [11]。答案质量评测引入 Ragas,它是面向 RAG 的评测框架,提供 faithfulness(答案是否忠于检索证据)、answer relevancy、context precision/recall 等指标,可在离线回归和线上抽样里量化召回与生成质量,避免调优靠拍脑袋 [12]。两者配合——Langfuse 管"链路可观测",Ragas 管"效果可量化"——构成 RAG 上线后的质量兜底。

11.5 日志与链路追踪
结构化日志加分布式 trace id,一条请求从网关到 FastAPI 到各下游全程可追,和 Langfuse 的 trace 打通,线上问题可端到端回溯。

十二、安全与合规
12.1 鉴权与权限
用户侧走会话鉴权由网关统一校验,agent 侧走独立 token,两类身份分离管理、可分别限流和吊销。

12.2 数据安全与访问控制
按数据分级控制来源可见性,检索时依据请求者身份过滤可访问的数据范围,避免越权召回;来源链接的可见性与原始文档权限保持一致。

12.3 模型与数据出域合规
embedding 和生成一律走内网合规渠道,敏感数据不出域;若使用有数据安全风险的外部渠道(如公网 OpenAI embedding),需经审批并限定数据范围。

十三、里程碑与落地顺序

13.1 阶段一:定稳内核 services 接口
先把 retrieve() / answer() 两个入口和 Chunk/Answer 契约定死,这是两端共享的地基,内核逻辑跑通并有单测覆盖。

13.2 阶段二:打通 REST → 网关 → web 端到端
优先做 REST,因为它链路最长(网关 + 前端 + 契约生成),先跑通端到端问答与 SSE 流式,验证引用来源展示。

13.3 阶段三:在内核之上加 MCP 适配层
REST 稳定后,MCP 基本是顺手加一层——同样调 retrieve(),注册成 tool、选 HTTP 传输、裁剪成结构化片段返回,接一个真实 coding agent 验证。

13.4 阶段四:补齐缓存、削峰、扩缩容等高并发能力
上语义缓存、检索缓存、网关限流削峰、多副本扩缩容,并接入 Langfuse + Ragas 做质量与性能双监控。

13.5 各阶段验收标准与压测指标
每阶段定量验收:内核阶段看召回 Top-K 的 context recall;REST 阶段看端到端首 token 延迟和 SSE 稳定性;MCP 阶段看 agent 调用成功率和返回结构合规;高并发阶段看目标 QPS 下的 P99 延迟、缓存命中率、降级触发是否符合预期,以及 Ragas faithfulness 不因缓存/降级而下降。

十四、风险与开放问题
14.1 技术风险
生成成本随并发线性上升,需靠缓存和分级路由压住;切分质量直接决定召回上限,语法切分的工程投入不能省;召回效果对代码类查询尤其敏感,可能需要代码图增强才能达标。

14.2 待定决策
网关到 rag-core 走 REST 还是 gRPC(影响契约设计,本期倾向先 REST);是否本期上代码图/GraphRAG(视召回效果收益);embedding 与生成的具体内网模型渠道(需结合 QPS、成本、数据合规最终敲定)。

14.3 依赖外部团队/资源的事项
内网模型渠道(Ark/VikingDB 等)的配额与接入审批、GPU 或托管推理资源、网关接入内网 Hertz/鉴权体系的对接支持,均需相关团队配合。


---

这份文档把我们前面每一轮讨论的结论都落到了对应章节,新增的 Langfuse + Ragas 可观测性/评测选型补在了 7.6 和 11.4,让"上线后怎么知道系统健康、答得准不准"有了明确抓手。

有两个决策点仍需你拍板,会实质影响 6.3 和第八章的契约细节:网关到 rag-core 走 REST 还是 gRPC,以及是否在字节内网落地(决定模型渠道和要不要接 Kitex/Hertz 的 IDL)。定了这两点我可以把契约层和代码生成命令补成可执行的细稿。需要的话,我也可以直接把这份方案写成一篇飞书文档给你,方便团队评审和批注。

References
1. Model Context Protocol
2. FastAPI
3. cloudwego/hertz
4. python-sdk | Model Context Protocol
5. vLLM
6. Turborepo
7. uv
8. Packaging Python Projects | Python Packaging User Guide
9. Ruff
10. pre-commit
11. Langfuse
12. Ragas