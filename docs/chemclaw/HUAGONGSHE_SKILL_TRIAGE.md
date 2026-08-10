# 化工社 / K-Dense 合集 Skill 分流表（ChemClaw）

> 状态：Triage 初稿（D-112）— **待用户确认 P0/P1 名单后方可实现**  
> 来源：`D:\化工社skills合集`（158 zip + `kdense-skills.json`）  
> 机器可读：[`fixtures/huagongshe_skill_triage.json`](fixtures/huagongshe_skill_triage.json)  
> 生成脚本：`scripts/_gen_huagongshe_triage.py`（可复跑）

## 1. 结论摘要

| 档 | 数量 | 含义 |
| --- | ---: | --- |
| DONE | 1 | 已内置 |
| **P0** | 1 | 优先 vendor 为可选 bundled Skill（每批仍 1 个） |
| **P1** | 4 | 值得做，但以**改写合并/提炼**为主，不全量复制 |
| P2 | 17 | 只借鉴规则或模板，不装 Skill |
| Skip | 135 | 不做（生信/重 ML/平台 SaaS/与销售无关等） |

**本表不是批准批量安装。** 实现仍须逐包小任务 + 新 D 编号 + 测试。

硬规则（D-090 / 销售规格 §16）：

- 销售首包不引入 RDKit / Datamol / TimesFM / 生信主轴
- HTTP/API 进平台 Tool/Provider，不塞进 Skill
- 不覆盖 `score_lead` / Lead Fit 数值
- 需 OpenRouter 等密钥的示意图能力：ChemClaw 默认关闭
- 与已有 PubChem / GLEIF / 海关 / 报价 / 证据分级重复者降档

合集**不含**官方 `huagongshe-reaction-publisher`；该能力单独评估（写反应 API + Token + 审批），不在本 158 表内自动升级为 P0。

## 2. 动作图例

| action | 含义 |
| --- | --- |
| `done` | 已交付 |
| `vendor_optional` | 解压进 `bundled/`，中文边界，龙虾**可选** `load_skill`，不强制 `skills:` |
| `adapt_merge` | 提炼模板/规则并入现有 `chem-*`，不全量 vendor |
| `adapt_ref` | 写短 reference / 纪律条款并入现有 Skill，不装新用户可见包 |
| `ref_only` | 文档层借鉴，代码不引入 |
| `skip` | 明确不做 |

## 3. DONE

| 包名 | 分 | 动作 | 依赖风险 | ChemClaw 适配建议 | 建议挂载 |
| --- | ---: | --- | --- | --- | --- |
| `uncertainty-and-units` | 5 | `done` | `heavy` | 已 D-111 vendor；询盘/转化可选；不进 Lead 评分 | export-engagement 可选 |

## 4. P0（建议下一实现批，仍一次一包）

| 包名 | 分 | 动作 | 依赖风险 | ChemClaw 适配建议 | 建议挂载 |
| --- | ---: | --- | --- | --- | --- |
| `scientific-critical-thinking` | 5 | `vendor_optional` | `api_key` | 中文边界；挂企业核验可选；关闭 OpenRouter 示意图；不改 score_lead | export/domestic 文档可选；qualification 指针 |

建议实现顺序：`scientific-critical-thinking` →（你确认后开 D-113 级小任务）。

## 5. P1（改写合并优先）

| 包名 | 分 | 动作 | 依赖风险 | ChemClaw 适配建议 | 建议挂载 |
| --- | ---: | --- | --- | --- | --- |
| `market-research-reports` | 4 | `adapt_merge` | `api_key` | 提炼 Claims Ledger/来源台账；不全量 TeX/资产包 | 报告场景按需，不强制 |
| `exploratory-data-analysis` | 3 | `adapt_ref` | `network` | 借鉴表格审计增强海关/展会文件分析；不全量 vendor | export 文档可选 |
| `peer-review` | 3 | `adapt_ref` | `api_key` | 提炼检查项供 sales-quality / 报告门禁 | engagement 可选 |
| `research-lookup` | 3 | `adapt_ref` | `api_key` | 检索纪律/溯源并入 buyer-discovery；勿双轨搜索 | export/domestic 可选提示 |

## 6. P2（只借鉴）

| 包名 | 分 | 动作 | 依赖风险 | ChemClaw 适配建议 | 建议挂载 |
| --- | ---: | --- | --- | --- | --- |
| `citation-management` | 2 | `ref_only` | `api_key` | 文档工具与现有产物/MD 重叠，仅借鉴 | — |
| `database-lookup` | 2 | `ref_only` | `api_key` | 查库模式参考；具体 API 走平台 Provider | — |
| `docx` | 2 | `ref_only` | `network` | 文档工具与现有产物/MD 重叠，仅借鉴 | — |
| `experimental-design` | 2 | `ref_only` | `heavy` | 非销售主轴 | — |
| `latex-posters` | 2 | `ref_only` | `api_key` | 文档工具与现有产物/MD 重叠，仅借鉴 | — |
| `markdown-mermaid-writing` | 2 | `ref_only` | `network` | 文档工具与现有产物/MD 重叠，仅借鉴 | — |
| `medchem` | 2 | `ref_only` | `network` | 研发向；特殊 SKU 化学证据时参考 | — |
| `ontology-term-resolution` | 2 | `ref_only` | `api_key` | 术语归一可参考 product-intelligence | — |
| `parallel-web` | 2 | `ref_only` | `api_key` | 平台已有 web search | — |
| `pdf` | 2 | `ref_only` | `network` | 文档工具与现有产物/MD 重叠，仅借鉴 | — |
| `scientific-brainstorming` | 2 | `ref_only` | `network` | 已有 brainstorming/grilling | — |
| `scientific-writing` | 2 | `ref_only` | `api_key` | 与现有 MD/报告重叠 | — |
| `statistical-analysis` | 2 | `ref_only` | `network` | 报价敏感时偶用；勿整装 | — |
| `matplotlib` | 1 | `ref_only` | `network` | 可视化与现有 Mermaid/报告重叠 | — |
| `scientific-schematics` | 1 | `ref_only` | `api_key` | 可视化与现有 Mermaid/报告重叠 | — |
| `scientific-visualization` | 1 | `ref_only` | `network` | 可视化与现有 Mermaid/报告重叠 | — |
| `seaborn` | 1 | `ref_only` | `network` | 可视化与现有 Mermaid/报告重叠 | — |

## 7. Skip 附录（按合集目录）

共 135 个。默认理由：非销售主轴、重依赖、实验室 SaaS 集成、或与已有 ChemClaw 能力重复且无增量。若你要「捞回」某一包，回复包名即可改档。

### 生物信息学（39）

`anndata`, `arboreto`, `bids`, `biopython`, `bioservices`, `bulk-rnaseq`, `cellxgene-census`, `cobrapy`, `deeptools`, `dhdna-profiler`, `etetoolkit`, `flowio`, `geniml`, `genomic-coordinates`, `genomic-intelligence`, `gget`, `gtars`, `histolab`, `imaging-data-commons`, `lamindb`, `matchms`, `neuropixels-analysis`, `nextflow`, `omero-integration`, `onekgpd`, `opentrons-integration`, `pathml`, `pathogen-variant-surveillance`, `phylogenetics`, `polars-bio`, `pydeseq2`, `pydicom`, `pyhealth`, `pysam`, `scanpy`, `scikit-bio`, `scvelo`, `scvi-tools`, `tiledbvcf`
### 机器学习与AI（26）

`aeon`, `arbor`, `autoskill`, `cirq`, `consciousness-council`, `dask`, `depmap`, `hugging-science`, `hypogenic`, `modal`, `optimize-for-gpu`, `pennylane`, `pufferlib`, `pytdc`, `pytorch-lightning`, `pyzotero`, `qiskit`, `qutip`, `scikit-learn`, `scikit-survival`, `shap`, `stable-baselines3`, `timesfm-forecasting`, `torch-geometric`, `transformers`, `umap-learn`
### 化学信息学（14）

`adaptyv`, `datamol`, `deepchem`, `diffdock`, `esm`, `glycoengineering`, `molecular-dynamics`, `molfeat`, `pymatgen`, `pyopenms`, `rdkit`, `rowan`, `tamarind`, `torchdrug`
### 科研写作与文献（11）

`bgpt-paper-search`, `clinical-reports`, `hypothesis-generation`, `literature-review`, `paper-lookup`, `paperclip`, `paperzilla`, `research-grants`, `scholar-evaluation`, `venue-templates`, `what-if-oracle`
### 数据处理（10）

`geopandas`, `get-available-resources`, `liteparse`, `markitdown`, `networkx`, `open-notebook`, `polars`, `simpy`, `vaex`, `zarr-python`
### 平台集成（8）

`benchling-integration`, `dnanexus-integration`, `ginkgo-cloud-lab`, `labarchive-integration`, `latchbio-integration`, `pacsomatic`, `protocolsio-integration`, `pylabrobot`
### 科学可视化（6）

`fluidsim`, `generate-image`, `infographics`, `openpiv`, `pptx-posters`, `scientific-slides`
### 统计分析（6）

`analytical-method-validation`, `pymc`, `pymoo`, `statistical-power`, `statsmodels`, `sympy`
### 临床与医学（5）

`clinical-decision-support`, `neurokit2`, `pkpd-modeling`, `primekg`, `treatment-plans`
### 通用工具（5）

`exa-search`, `pi-agent`, `pptx`, `usfiscaldata`, `xlsx`
### 地球与物理科学（3）

`astropy`, `geomaster`, `matlab`
### 研究方法论（2）

`iso-standards-readiness`, `pathway-enrichment`


## 8. 与官方化工社 API 的边界

| 能力 | 处理 |
| --- | --- |
| 合集 158（K-Dense） | 本表分流 |
| `huagongshe-reaction-publisher` + 搜索/反应 API | **另案**：平台 Tool + 审批写；不进 Lead 评分 |

## 9. 请你确认

请回复是否认可：

1. P0 名单（当前仅 `scientific-critical-thinking`）
2. P1 名单与「改写不整装」策略
3. 是否有 Skip 中要捞回的包名

确认后下一刀再实现第一个 P0（或你点名的包）。
