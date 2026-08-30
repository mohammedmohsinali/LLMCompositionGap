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
(Table 5 / Figure 6); its aggregate counts are reported in the paper and its
rubric is in `annotation/`.

## Repository layout

```
experiments_v2/
  core.py                 model configs and API/OSS call helpers
  <domain>/run.py         two-pass baseline runner (contracts, math, sql, code, logic)
  <domain>/results/       per-example prediction logs + aggregate results (see
                          "About the -cot files" below)
  mechanism/              correct/wrong structural-hint experiment + logs
  mitigation/             structure-aware prompting experiment + logs
  run_all_*.sh            sweep scripts (API models / open-source models)
experiments/<x>_composition_gap/
  classify_*.py           the rule-based structure classifiers imported by the runners
  data/*_classified.json  benchmark examples with the rule-derived structural type
                          (from classify_*.py) used for hints and for the logic Pass-1 gold
data/annotated/splits/test.csv   the contract corpus (public-sector agreements,
                                 constraint-type labels; the paper evaluates the
                                 first 2,000 constraint-labeled clauses)
annotation/               the four-category error-taxonomy rubric used in the paper
analysis/                 scripts that regenerate every log-derived table and figure
```

## Contract corpus: label provenance

The `constraint_type` column of `test.csv` (the gold label for both contract
passes) comes from a combined process: an OpenAI model (GPT-4o) proposed each label
together with a written rationale, stored verbatim in the `notes` column with
the prefix `auto-openai:`, and the authors defined the label scheme and
reviewed and revised the proposed labels (the file records the model's
rationale, not the revisions). The paper states this in Section 4.2
and Limitations, including the caveat that, because the proposals originated
from a model related to GPT-4o, its contracts gap may partly reflect agreement
with model-anchored labels. The rationales are kept in the release so the
labels can be audited or replaced.

## About the `-cot` files (no Chain-of-Thought condition exists)

Each configuration has a `*-cot` twin (`gpt4o-cot`, `qwen7b-cot`, ...). These
were intended as Chain-of-Thought runs, but the `cot` flag in `core.py` is
defined and never read by any runner, so every `-cot` file is a **repeat run
with identical prompts**. The camera-ready paper reports them only as a
run-to-run stability check (Section 5.1) and makes no CoT claims. For
DeepSeek the repeat run is full-scale for math and code, whereas the first
run is a 50-example pilot in every domain.

## Reproducing the exact evaluated sets

The reported GPT-4o/Qwen/Llama runs used `--limit 2000`, which only affects
contracts (the other benchmarks are smaller): `bash run_all_api.sh 2000`.
The DeepSeek pilots used `--limit 50`. The runners read the benchmark files
from `experiments/<x>_composition_gap/data/` (included) and the contract
corpus from `data/annotated/splits/test.csv`.

## Scoring protocols (please read before comparing numbers)

The composed-task (Pass-2) criterion differs by domain, exactly as documented
in Section 3.4 of the paper:

| Domain | Pass-1 pieces | Pass-2 scored as |
|---|---|---|
| Contracts | modality + condition derived from the gold label (every evaluated clause is HARD/SOFT, so gold condition is always "no"; the CSV also has 207 NOT_CONSTRAINT and 497 unlabeled rows the runner skips) | HARD/SOFT label match vs. gold |
| Math | >=70% of gold numbers; >=1 gold operation keyword | exact final-answer match vs. gold |
| SQL | tables at >=50% overlap; filters/aggregations by presence vs. gold | **structural-template match** of the generated query vs. the gold query (rule-based classifier; not execution accuracy) |
| Logic | entities at >=50% overlap; rule-derived logic type match (classify_logic_structure.py) | true/false/unknown label match vs. gold |
| Code | two yes/no questions (iteration, recursion); answers **not gold-scored** | **plan-consistency**: generated code's control flow vs. the model's own Pass-1 answers (not functional correctness) |

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
bash run_all_oss.sh            # Qwen/Llama (GPU; loaded by HF repo name, no revision hash)
```

Datasets: math uses the GSM8K test split, SQL the Spider dev split, code
HumanEval, and logic the FOLIO validation split; the classified copies the
runners read are included under `experiments/<x>_composition_gap/data/`. The contract corpus ships in this repository. The
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

MIT (see `LICENSE`) for the code and the contract corpus, which is derived
from publicly available public-sector agreements. The classified copies of
GSM8K, Spider, HumanEval, and FOLIO examples under `experiments/` are
redistributed under those benchmarks' original licenses.
