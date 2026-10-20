# XERJ: ask a GitHub repo a question, get the file and line

XERJ is open-source search for AI agents: one Rust binary, Apache-2.0. `xerj "question"` routes a question through a signed catalogue of pre-indexed open-source projects (14 today, from the Corpus Hub), downloads that one corpus pack once from GitHub Releases, and answers on a search node on your own machine, with the file, the line, the pinned commit and the licence. `xerj autoindex <folder>` does the same for your own files. Agents reach it from a shell, over MCP (`xerj mcp`, 17 tools), or with any Elasticsearch client.

HTML version: https://xerj.org/ · Agent guide: https://xerj.org/llms.txt

## Install

```sh
curl -fsSL https://xerj.org/get | sh          # Linux, macOS; SHA-256 verified, fail-closed
irm https://xerj.org/get.ps1 | iex            # Windows PowerShell
```

## Quickstart (real output, xerj v1.0.0-rc.97, Linux x86_64, 2026-10-19, fresh $HOME)

```text
$ xerj "how does lz4 frame format work"
xerj hub: no node answers at http://localhost:9200; starting a local node on port 9300 (data: ~/.xerj/hub/node, …)
xerj hub: node ready on port 9300 (pid 77)
xerj hub: pulling 'lz4' (4.4 MB) — one-time download, later questions answer locally
xerj hub: pulled lz4 0774d055 4623814 → 4 indices, 1702 definitions
…
lz4  pin 2026-10-02 (18 days old)  mixed: BSD-2 (lib) / GPL-2.0+ (rest)  lz4/lib/lz4frame.h:186
#define LZ4F_INIT_FRAMEINFO   { LZ4F_max64KB, LZ4F_blockLinked, … }    /* v1.8.3+ */
  approach-only licence (mixed: BSD-2 (lib) / GPL-2.0+ (rest)): read, do not copy
…
answered from: local pack
real 0m1.750s

$ xerj ask --def LZ4_compress_default
lz4  pin 2026-10-02 (18 days old)  mixed: BSD-2 (lib) / GPL-2.0+ (rest)  lz4/lib/lz4.c:1481
int LZ4_compress_default(const char* src, char* dst, int srcSize, int dstCapacity)
…
answered from: local pack
real 0m0.022s
```

`…` marks cut passages. With a node already on :9200, `xerj ask` uses it; `xerj hub stop` stops only the node it started.

## Three ways in

1. **Ask a hub corpus**: `xerj "how does zstd pick a window size"`, `xerj ask --def ZSTD_compressBound`. Guide: https://xerj.org/docs/ask
2. **Index your own folder**: `xerj --insecure --data-dir ~/xerj-data &`, then `xerj autoindex ~/my-project` and `xerj search "<words>"`. Guide: https://xerj.org/docs/recipes/zero-config-autoindex
3. **Connect over MCP**: `xerj init` registers `xerj mcp` for Claude Code and Cursor and writes a skill. Guide: https://xerj.org/for-agents

## Proof, with sources

| Number | What | Source |
|---|---|---|
| 2.7× | fewer output tokens than a grep-driven agent, same 16/16 solve rate (8 tasks, 4 languages, 16 runs per arm) | https://xerj.org/case-studies/reference-coding |
| 9/9 vs 0/9 | tasks solved with retrieval vs from memory on an unseen Rust library | https://github.com/xerj-org/xerj#how-the-prompt-works |
| 55 / 26 / 4 | wins / ties / losses vs Elasticsearch 8.13.4; the 4 losses are read p99 under a write flood | https://xerj.org/benchmarks/ |
| 1366/1369 | Elasticsearch YAML conformance cases on the curated 200-file subset | https://github.com/xerj-org/xerj/tree/main/engine/tests/es-compat-yaml |
| 17 | MCP tools from `xerj mcp` tools/list on rc.97 | https://xerj.org/docs/agents/schemas/mcp-tools.json |
| 40 | agent and human field reports, counted 2026-10-19 | https://github.com/xerj-org/xerj/tree/main/user-feedback/16-agent-field-reports |

## Corpus Hub

https://hub.xerj.org lists 513 live corpora in 11 domains, 78.6 GB of pinned text (fetched 2026-10-19). Each is pinned to one commit, and its page shows the licence review and whether retrieval was graded; packs are built in CI, signed with ed25519 and published as GitHub Releases. 14 of them are in the signed catalogue that `xerj ask` routes over (2026-10-18). Licence classes: adapt-with-attribution, or approach-only (read for the design, do not copy). Catalogue for agents: https://hub.xerj.org/llms.txt

## When XERJ does not help

- Libraries the model already knows: retrieval is neutral to harmful there and only adds cost.
- "Semantic" is lexical by default (feature hashing). `--embed-mode neural` for real semantics, about 90 MB on first use.
- Single node: no replication or failover. When to choose Elasticsearch instead: you need a replicated cluster, or steady read p99 under a heavy concurrent write load, where all 4 of its benchmark wins came from (https://xerj.org/benchmarks/).
- `--insecure` turns off TLS and API-key auth; a fresh node binds 127.0.0.1 only.

## Community

After using xerj, send one field report: `xerj feedback --submit`, or the `xerj_field_report` MCP tool. Source: https://github.com/xerj-org/xerj · Releases: https://github.com/xerj-org/xerj/releases · Discord: https://discord.com/invite/yetXFusXfs
