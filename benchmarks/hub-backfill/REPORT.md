# Hub backfill report

Written by `.github/workflows/hub-packs.yml` (the `backfill report` job) after every
publishing run; do not edit by hand. One row per corpus per run; the rows behind it
are in `rows.jsonl`. Spec: docs/CORPUS_HUB_V2_IMPLEMENTATION.md §12.1.

## Current state

94 corpora attempted: 39 published at their latest attempt, 55 not.

### Latest attempt did not publish (fix or delist on purpose)

| slug | pin8 | bytes | defs | result | error |
|---|---|---:|---:|---|---|
| `12-factor-agents` | `d20c7283` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `18f-content-guide` | `1b1723d3` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `a11y-project-content` | `27de2268` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `accord-legal-models` | `a23b30a1` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `ada-2010` | `d2be9eb3` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `adalflow` | `810de99d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `adyen-openapi` | `45520ee6` | 128802151 | 0 | failed at `e2e` | xerj hub pull adyen-openapi failed (exit 1) |
| `aeron` | `d3499bb1` | 54753628 | 28139 | failed at `e2e` | xerj hub pull aeron failed (exit 1) |
| `agentbench` | `d1e4a10d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `agentscope` | `812eaecd` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `agno` | `1f2aac51` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":6,"errors":true,"items":[{"index":{"_index":"xc-agno-b1792295323-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1,"status |
| `aider` | `5dc9490b` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `aioquic` | `974e9349` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `alex-inclusive-language` | `9a57595d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `ann-benchmarks` | `2e081ad3` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `annoy` | `379f7446` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `anthropic-cookbook` | `9c1e493d` | 84900043 | 901 | failed at `e2e` | xerj hub pull anthropic-cookbook failed (exit 1) |
| `anything-llm` | `3e4f9411` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `api-blueprint` | `86fc3a12` | 660828 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `api-common-protos` | `3332dec5` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `api-linter` | `836098d5` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `arazzo-spec` | `79ddb24a` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `argo-cd` | `03a10c74` | 96831097 | 25467 | failed at `e2e` | xerj hub pull argo-cd failed (exit 1) |
| `argo-workflows` | `8f57ec73` | 91719093 | 14769 | failed at `e2e` | xerj hub pull argo-workflows failed (exit 1) |
| `aria-practices` | `0f765e4d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `arrow-rs` | `73595d58` | 56234430 | 24047 | failed at `e2e` | xerj hub pull arrow-rs failed (exit 1) |
| `astro-docs` | `f29faa41` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `asyncapi-bindings` | `1f418fe7` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `asyncapi-spec` | `1dd65fd2` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `asyncapi-spec-json-schemas` | `00af2905` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `asyncapi-studio` | `f3aa74ec` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `atomic-agents` | `4d443474` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `attack-flow` | `8b6ca28b` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `attack-mappings-explorer` | `a85e55af` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `autogen` | `027ecf0a` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `autorag` | `ccb70c12` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `avro` | `28cb08c1` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `awesome-ai-system-prompts` | `74964625` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `awesome-llm-apps` | `4bf51ab7` | 56867640 | 7418 | failed at `e2e` | xerj hub pull awesome-llm-apps failed (exit 1) |
| `awesome-mcp-servers` | `cc7f1f42` | 2808990 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `awesome-sre` | `e91ef69a` | 115178 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `axe-core` | `7e287a6a` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `axolotl` | `e767fe07` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `biome` | `39d7595b` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":7,"errors":true,"items":[{"index":{"_index":"xc-biome-b1792295599-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1,"statu |
| `bookkeeper` | `773a988d` | 68217531 | 29420 | failed at `e2e` | xerj hub pull bookkeeper failed (exit 1) |
| `botan` | `9fc28d5b` | 143697339 | 18513 | failed at `e2e` | xerj hub pull botan failed (exit 1) |
| `boulder` | `f877538d` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":11,"errors":true,"items":[{"index":{"_index":"xc-boulder-b1792295713-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1,"st |
| `brex-prompt-engineering` | `50871be1` | 473150 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `calcite` | `8f27e24a` | 108815484 | 49987 | failed at `e2e` | xerj hub pull calcite failed (exit 1) |
| `caliber-ehr-phenotypes` | `f4f614fc` | 8251949 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `camel` | `e5e55256` | 265425403 | 10924 | failed at `e2e` | xerj hub pull camel failed (exit 1) |
| `cassandra` | `ec2c276b` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":10,"errors":true,"items":[{"index":{"_index":"xc-cassandra-b1792296135-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1," |
| `cdk8s` | `ed80049b` | 105196359 | 127 | failed at `e2e` | xerj hub pull cdk8s failed (exit 1) |
| `cell-ontology` | `b7cb31d4` | 196856121 | 67 | failed at `e2e` | xerj hub pull cell-ontology failed (exit 1) |
| `cfssl` | `ab47f0d9` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":5,"errors":true,"items":[{"index":{"_index":"xc-cfssl-b1792296480-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1,"statu |

## Runs (newest first)

### Run [39091961868](https://github.com/xerj-org/xerj/actions/runs/39091961868), 2026-10-18: 17 of 40 published

| slug | pin8 | bytes | defs | result | error |
|---|---|---:|---:|---|---|
| `adyen-openapi` | `45520ee6` | 128802151 | 0 | failed at `e2e` | xerj hub pull adyen-openapi failed (exit 1) |
| `aeron` | `d3499bb1` | 54753628 | 28139 | failed at `e2e` | xerj hub pull aeron failed (exit 1) |
| `agno` | `1f2aac51` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":6,"errors":true,"items":[{"index":{"_index":"xc-agno-b1792295323-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1,"status |
| `anthropic-cookbook` | `9c1e493d` | 84900043 | 901 | failed at `e2e` | xerj hub pull anthropic-cookbook failed (exit 1) |
| `api-blueprint` | `86fc3a12` | 660828 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `argo-cd` | `03a10c74` | 96831097 | 25467 | failed at `e2e` | xerj hub pull argo-cd failed (exit 1) |
| `argo-workflows` | `8f57ec73` | 91719093 | 14769 | failed at `e2e` | xerj hub pull argo-workflows failed (exit 1) |
| `arrow-rs` | `73595d58` | 56234430 | 24047 | failed at `e2e` | xerj hub pull arrow-rs failed (exit 1) |
| `awesome-llm-apps` | `4bf51ab7` | 56867640 | 7418 | failed at `e2e` | xerj hub pull awesome-llm-apps failed (exit 1) |
| `awesome-mcp-servers` | `cc7f1f42` | 2808990 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `awesome-sre` | `e91ef69a` | 115178 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `biome` | `39d7595b` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":7,"errors":true,"items":[{"index":{"_index":"xc-biome-b1792295599-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1,"statu |
| `bookkeeper` | `773a988d` | 68217531 | 29420 | failed at `e2e` | xerj hub pull bookkeeper failed (exit 1) |
| `botan` | `9fc28d5b` | 143697339 | 18513 | failed at `e2e` | xerj hub pull botan failed (exit 1) |
| `boulder` | `f877538d` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":11,"errors":true,"items":[{"index":{"_index":"xc-boulder-b1792295713-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1,"st |
| `brex-prompt-engineering` | `50871be1` | 473150 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `calcite` | `8f27e24a` | 108815484 | 49987 | failed at `e2e` | xerj hub pull calcite failed (exit 1) |
| `caliber-ehr-phenotypes` | `f4f614fc` | 8251949 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `camel` | `e5e55256` | 265425403 | 10924 | failed at `e2e` | xerj hub pull camel failed (exit 1) |
| `cassandra` | `ec2c276b` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":10,"errors":true,"items":[{"index":{"_index":"xc-cassandra-b1792296135-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1," |
| `cdk8s` | `ed80049b` | 105196359 | 127 | failed at `e2e` | xerj hub pull cdk8s failed (exit 1) |
| `cell-ontology` | `b7cb31d4` | 196856121 | 67 | failed at `e2e` | xerj hub pull cell-ontology failed (exit 1) |
| `cfssl` | `ab47f0d9` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":5,"errors":true,"items":[{"index":{"_index":"xc-cfssl-b1792296480-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1,"statu |
| `candle` | `c68b2499` | 31473651 | 12753 | published `pack-candle-c68b2499` |  |
| `caniuse` | `e951c6cd` | 6980429 | 3 | published `pack-caniuse-e951c6cd` |  |
| `cap-examples` | `9ef3b4d0` | 1003421 | 54 | published `pack-cap-examples-9ef3b4d0` |  |
| `capa-rules` | `805f9eac` | 2229324 | 12 | published `pack-capa-rules-805f9eac` |  |
| `capnproto` | `e866bdba` | 38671480 | 4892 | published `pack-capnproto-e866bdba` |  |
| `carbon` | `c9b1f791` | 46085538 | 11349 | published `pack-carbon-c9b1f791` |  |
| `catala-law-lang` | `5a41577e` | 14937095 | 6199 | published `pack-catala-law-lang-5a41577e` |  |
| `cdc-clinical` | `3bd1ba62` | 5920750 | 12 | published `pack-cdc-clinical-3bd1ba62` |  |
| `cel-spec` | `40a3c900` | 4524562 | 1663 | published `pack-cel-spec-40a3c900` |  |
| `cereal` | `22a1b369` | 5998963 | 3132 | published `pack-cereal-22a1b369` |  |
| `cert-manager` | `ef9ac738` | 35355153 | 8129 | published `pack-cert-manager-ef9ac738` |  |
| `certmagic` | `cfd20205` | 2154445 | 631 | published `pack-certmagic-cfd20205` |  |
| `certstrap` | `f392bdae` | 906673 | 293 | published `pack-certstrap-f392bdae` |  |
| `cfn-nag` | `8b5f03da` | 4550174 | 1323 | published `pack-cfn-nag-8b5f03da` |  |
| `chamber` | `5f93f5f3` | 1126572 | 471 | published `pack-chamber-5f93f5f3` |  |
| `chaos-mesh` | `780cb80c` | 23381806 | 7320 | published `pack-chaos-mesh-780cb80c` |  |
| `chaostoolkit-docs` | `d113ae82` | 1497001 | 10 | published `pack-chaostoolkit-docs-d113ae82` |  |

### Run [39091860082](https://github.com/xerj-org/xerj/actions/runs/39091860082), 2026-10-18: 22 of 40 published

| slug | pin8 | bytes | defs | result | error |
|---|---|---:|---:|---|---|
| `adyen-openapi` | `45520ee6` | 127033718 | 0 | failed at `e2e` | xerj hub pull adyen-openapi failed (exit 1) |
| `aeron` | `d3499bb1` | 52531523 | 28139 | failed at `e2e` | xerj hub pull aeron failed (exit 1) |
| `agno` | `1f2aac51` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":4,"errors":true,"items":[{"index":{"_index":"xc-agno-b1792292503-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1,"status |
| `anthropic-cookbook` | `9c1e493d` | 84939283 | 901 | failed at `e2e` | xerj hub pull anthropic-cookbook failed (exit 1) |
| `api-blueprint` | `86fc3a12` | 660629 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `argo-cd` | `03a10c74` | 116015334 | 25467 | failed at `e2e` | xerj hub pull argo-cd failed (exit 1) |
| `argo-workflows` | `8f57ec73` | 91730049 | 14769 | failed at `e2e` | xerj hub pull argo-workflows failed (exit 1) |
| `arrow-rs` | `73595d58` | 56254615 | 24047 | failed at `e2e` | xerj hub pull arrow-rs failed (exit 1) |
| `awesome-llm-apps` | `4bf51ab7` | 56861150 | 7418 | failed at `e2e` | xerj hub pull awesome-llm-apps failed (exit 1) |
| `awesome-mcp-servers` | `cc7f1f42` | 2809865 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `awesome-sre` | `e91ef69a` | 115543 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `biome` | `39d7595b` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":10,"errors":true,"items":[{"index":{"_index":"xc-biome-b1792292746-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1,"stat |
| `bookkeeper` | `773a988d` | 68757576 | 29420 | failed at `e2e` | xerj hub pull bookkeeper failed (exit 1) |
| `botan` | `9fc28d5b` | 164011813 | 18513 | failed at `e2e` | xerj hub pull botan failed (exit 1) |
| `boulder` | `f877538d` |  |  | failed at `build` | xerj hub build-pack: defs bulk index reported errors: {"took":11,"errors":true,"items":[{"index":{"_index":"xc-boulder-b1792292898-defs","_id":"","_version":1,"_shards":{"total":1,"successful":1,"failed":0},"_seq_no":0,"_primary_term":1,"st |
| `brex-prompt-engineering` | `50871be1` | 474953 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `calcite` | `8f27e24a` | 108806227 | 49987 | failed at `e2e` | xerj hub pull calcite failed (exit 1) |
| `caliber-ehr-phenotypes` | `f4f614fc` | 8256247 | 0 | failed at `e2e` | defs.jsonl has no identifier to look up |
| `badger` | `5688f140` | 4850849 | 1800 | published `pack-badger-5688f140` |  |
| `bandit-plugins` | `68ebe11e` | 2271033 | 1067 | published `pack-bandit-plugins-68ebe11e` |  |
| `bebop` | `03a2a761` | 3694767 | 3075 | published `pack-bebop-03a2a761` |  |
| `blake2` | `ed1974ea` | 2859278 | 675 | published `pack-blake2-ed1974ea` |  |
| `blake3` | `f55849f8` | 4448805 | 1122 | published `pack-blake3-f55849f8` |  |
| `bleve` | `6abe3730` | 42683669 | 5910 | published `pack-bleve-6abe3730` |  |
| `blst` | `19b285a4` | 4992652 | 2824 | published `pack-blst-19b285a4` |  |
| `bluge` | `57414197` | 6564295 | 2485 | published `pack-bluge-57414197` |  |
| `boringtun` | `6dcc889a` | 1185429 | 518 | published `pack-boringtun-6dcc889a` |  |
| `borsh-rs` | `c9a2ed48` | 2849421 | 1260 | published `pack-borsh-rs-c9a2ed48` |  |
| `box-openapi` | `38fa64be` | 3398743 | 18 | published `pack-box-openapi-38fa64be` |  |
| `brotli` | `42a2ed43` | 40961895 | 3157 | published `pack-brotli-42a2ed43` |  |
| `brpc` | `7a2c1d5e` | 46898776 | 17281 | published `pack-brpc-7a2c1d5e` |  |
| `bson-rust` | `81dcdcae` | 3892655 | 2270 | published `pack-bson-rust-81dcdcae` |  |
| `btrblocks` | `c950c3c0` | 4440890 | 655 | published `pack-btrblocks-c950c3c0` |  |
| `buf` | `91f127d3` | 37057776 | 19130 | published `pack-buf-91f127d3` |  |
| `buildpacks-pack` | `99894bcb` | 9899243 | 4292 | published `pack-buildpacks-pack-99894bcb` |  |
| `bulletproofs` | `be67b6d5` | 2161647 | 339 | published `pack-bulletproofs-be67b6d5` |  |
| `c-ares` | `f4156c12` | 10811210 | 4077 | published `pack-c-ares-f4156c12` |  |
| `caddy` | `ac834b5d` | 14497818 | 4633 | published `pack-caddy-ac834b5d` |  |
| `caldera` | `cb8d6a81` | 11038475 | 2989 | published `pack-caldera-cb8d6a81` |  |
| `caldera-stockpile` | `996ec41c` | 2479556 | 743 | published `pack-caldera-stockpile-996ec41c` |  |

### Run [39088277520](https://github.com/xerj-org/xerj/actions/runs/39088277520), 2026-10-18: 0 of 40 published

| slug | pin8 | bytes | defs | result | error |
|---|---|---:|---:|---|---|
| `12-factor-agents` | `d20c7283` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `18f-content-guide` | `1b1723d3` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `a11y-project-content` | `27de2268` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `accord-legal-models` | `a23b30a1` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `ada-2010` | `d2be9eb3` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `adalflow` | `810de99d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `adyen-openapi` | `45520ee6` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `aeron` | `d3499bb1` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `agentbench` | `d1e4a10d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `agentscope` | `812eaecd` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `agno` | `1f2aac51` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `aider` | `5dc9490b` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `aioquic` | `974e9349` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `alex-inclusive-language` | `9a57595d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `ann-benchmarks` | `2e081ad3` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `annoy` | `379f7446` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `anthropic-cookbook` | `9c1e493d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `anything-llm` | `3e4f9411` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `api-blueprint` | `86fc3a12` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `api-common-protos` | `3332dec5` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `api-linter` | `836098d5` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `arazzo-spec` | `79ddb24a` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `argo-cd` | `03a10c74` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `argo-workflows` | `8f57ec73` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `aria-practices` | `0f765e4d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `arrow-rs` | `73595d58` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `astro-docs` | `f29faa41` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `asyncapi-bindings` | `1f418fe7` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `asyncapi-spec` | `1dd65fd2` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `asyncapi-spec-json-schemas` | `00af2905` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `asyncapi-studio` | `f3aa74ec` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `atomic-agents` | `4d443474` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `attack-flow` | `8b6ca28b` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `autogen` | `027ecf0a` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `awesome-ai-system-prompts` | `74964625` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `awesome-llm-apps` | `4bf51ab7` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `awesome-mcp-servers` | `cc7f1f42` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `awesome-sre` | `e91ef69a` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `axe-core` | `7e287a6a` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `axolotl` | `e767fe07` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |

### Run [39085957551](https://github.com/xerj-org/xerj/actions/runs/39085957551), 2026-10-18: 0 of 40 published

| slug | pin8 | bytes | defs | result | error |
|---|---|---:|---:|---|---|
| `12-factor-agents` | `d20c7283` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `18f-content-guide` | `1b1723d3` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `a11y-project-content` | `27de2268` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `accord-legal-models` | `a23b30a1` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `ada-2010` | `d2be9eb3` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `adalflow` | `810de99d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `adyen-openapi` | `45520ee6` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `aeron` | `d3499bb1` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `agentbench` | `d1e4a10d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `agentscope` | `812eaecd` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `agno` | `1f2aac51` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `aider` | `5dc9490b` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `aioquic` | `974e9349` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `alex-inclusive-language` | `9a57595d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `ann-benchmarks` | `2e081ad3` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `annoy` | `379f7446` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `anthropic-cookbook` | `9c1e493d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `anything-llm` | `3e4f9411` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `api-blueprint` | `86fc3a12` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `api-common-protos` | `3332dec5` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `api-linter` | `836098d5` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `arazzo-spec` | `79ddb24a` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `argo-cd` | `03a10c74` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `argo-workflows` | `8f57ec73` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `aria-practices` | `0f765e4d` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `arrow-rs` | `73595d58` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `astro-docs` | `f29faa41` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `asyncapi-bindings` | `1f418fe7` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `asyncapi-spec` | `1dd65fd2` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `asyncapi-spec-json-schemas` | `00af2905` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `asyncapi-studio` | `f3aa74ec` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `atomic-agents` | `4d443474` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `attack-flow` | `8b6ca28b` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `attack-mappings-explorer` | `a85e55af` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `autogen` | `027ecf0a` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `autorag` | `ccb70c12` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `avro` | `28cb08c1` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `awesome-ai-system-prompts` | `74964625` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `awesome-llm-apps` | `4bf51ab7` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
| `awesome-mcp-servers` | `cc7f1f42` |  |  | no result | the pack job recorded no result (pack jobs: failure, build xerj: success) |
