# LLMCompositionGap

Code, data, and per-example prediction logs for the EMNLP 2026 paper:

> **When Structure Is Hidden: Measuring and Diagnosing the Compositional Gap in LLMs**
> Shravani Hariprasad, Mohsin Ali Mohammed, Vinija Jain, Aman Chadha

The paper measures the conditional composition gap, `P(composed wrong | all
pieces correct)`, with a two-pass protocol across five domains (contracts,
math, SQL, code, logic) and four model families (GPT-4o, DeepSeek,
Qwen2.5-7B-Instruct, Llama-3.1-8B-Instruct), then uses a correct/wrong
structural-hint intervention and structure-aware prompting to diagnose where
the bottleneck lies.

## Reproducing the paper's tables (no model access needed)

Every gap rate, confidence interval, permutation test, sensitivity analysis,
and shared-subset number in the paper reproduces from the per-example
prediction logs included in this repository:

```bash
pip install -r requirements.txt   # only numpy/matplotlib needed for analysis
python analysis/recompute_tables.py   # prints every log-derived table, writes recompute_out.json
python analysis/make_figures.py       # regenerates the data-derived figures
```

The one table not regenerable from the logs is the manual error taxonomy
(Table 6 / Figure 7); its aggregate counts are reported in the paper and its
rubric is in `annotation/`.

## Repository layout

```
experiments_v2/
  core.py                 model configs and API/OSS call helpers
  <domain>/run.py         two-pass baseline runner (contracts, math, sql, code, logic)
  <domain>/results/       per-example prediction logs + aggregate results (8 configs each)
  mechanism/              correct/wrong structural-hint experiment + logs
  mitigation/             structure-aware prompting experiment + logs
  run_all_*.sh            sweep scripts (API models / open-source models)
data/annotated/splits/test.csv   the contract corpus (public-sector agreements,
                                 constraint-type labels; the paper evaluates the
                                 first 2,000 constraint-labeled clauses)
annotation/               the four-category error-taxonomy rubric used in the paper
analysis/                 scripts that regenerate every log-derived table and figure
```

## Contract corpus: label provenance

The `constraint_type` column of `test.csv` (the gold label for both contract
passes) comes from a combined process: an OpenAI model proposed each label
together with a written rationale, stored verbatim in the `notes` column with
the prefix `auto-openai:`, and the authors defined the label scheme and
reviewed and revised the proposed labels. The paper states this in Section 4.2
and Limitations, including the caveat that, because the proposals originated
from a model related to GPT-4o, its contracts gap may partly reflect agreement
with model-anchored labels. The rationales are kept in the release so the
labels can be audited or replaced.

## Scoring protocols (please read before comparing numbers)

The composed-task (Pass-2) criterion differs by domain, exactly as documented
in Section 3.4 of the paper:

| Domain | Pass-1 pieces | Pass-2 scored as |
|---|---|---|
| Contracts | modality + condition vs. gold | constraint-type label match vs. gold |
| Math | quantities + operations vs. gold | exact final-answer match vs. gold |
| SQL | tables/filters/aggregations vs. gold | **structural-template match** of the generated query vs. the gold query (rule-based classifier; not execution accuracy) |
| Logic | entities + logical form vs. gold | true/false/unknown label match vs. gold |
| Code | model's own answers, **not gold-scored** | **plan-consistency**: generated code's control flow vs. the model's own Pass-1 answers (not functional correctness) |

Consequences, stated in the paper and repeated here:

- The SQL gap measures structural disagreement with the gold composition. A
  semantically equivalent query built on a different template counts as a
  failure.
- The code column is not comparable to the other domains and is excluded from
  every cross-domain, mechanism, and mitigation claim in the paper. In the
  mechanism and mitigation experiments the code conditions were scored against
  gold-derived structure while the code baseline uses plan-consistency, so
  those code cells compare two different metrics and are reported for
  completeness only.
- DeepSeek baseline logs are 50-example pilot subsets in every domain
  (`deepseek-cot` is full-scale for math and code only). DeepSeek is excluded
  from averaged analyses.

## Rerunning generation (optional)

Rerunning the models requires API keys and/or a GPU:

```bash
export OPENAI_API_KEY=...      # GPT-4o
export DEEPSEEK_API_KEY=...    # DeepSeek
cd experiments_v2
bash run_all_api.sh            # API models
bash run_all_oss.sh            # Qwen/Llama (GPU; pinned HF checkpoints)
```

Datasets: math uses the GSM8K test split, SQL the Spider dev split, code
HumanEval, and logic the FOLIO validation split; the domain runners expect
these under `experiments_v2/<domain>/data/` (see each `run.py` `load_data`
for accepted filenames). The contract corpus ships in this repository. The
proprietary models were accessed via the `gpt-4o` and `deepseek-chat` API
aliases in April 2026; those aliases do not expose snapshot identifiers, so
regenerated outputs may drift as providers update them.

## Citation

```bibtex
@inproceedings{hariprasad2026structure,
  title     = {When Structure Is Hidden: Measuring and Diagnosing the Compositional Gap in LLMs},
  author    = {Hariprasad, Shravani and Mohammed, Mohsin Ali and Jain, Vinija and Chadha, Aman},
  booktitle = {Proceedings of the 2026 Conference on Empirical Methods in Natural Language Processing},
  year      = {2026}
}
```

## License

MIT (see `LICENSE`). The contract corpus is derived from publicly available
public-sector agreements; benchmark datasets (GSM8K, Spider, HumanEval,
FOLIO) retain their original licenses and are not redistributed here.
