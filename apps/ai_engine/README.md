# AI Engine

Recommendations, semantically ranked search, review summarization and a
shopping assistant for the AI E-Commerce platform.

Everything here runs **locally and for free**. There are no paid APIs, no API
keys, and no cloud inference required. Heavy optional backends (PyTorch,
Hugging Face Transformers, Ollama) are supported but never mandatory — the
engine always has a deterministic, CPU-only fallback that works offline.

## Layout

The machine-learning code is deliberately isolated from Django in the `ml/`
package so it can be trained, evaluated and served from a plain script:

```
apps/ai_engine/
├── ml/                     # isolated, Django-free ML package
│   ├── config.py           # seeds, paths, hyper-parameters
│   ├── licenses.py         # license registry (models + datasets)
│   ├── artifacts.py        # model registry & versioning
│   ├── data/               # data processing
│   │   ├── synthetic.py    #   deterministic synthetic generator
│   │   ├── dataset.py      #   splits, matrices, save/load
│   │   ├── preprocessing.py#   tokenization, sentence splitting
│   │   └── django_source.py#   ORM -> plain structures adapters
│   ├── algorithms/         # model implementations
│   │   ├── popularity.py   #   baseline (non-personalized)
│   │   ├── hybrid_recommender.py  # learned CF + content model
│   │   ├── text_embedding.py      # semantic-search embeddings
│   │   └── summarizer.py          # extractive / transformer / ollama
│   ├── training/           # reproducible training entry points
│   ├── evaluation/         # metrics + model comparison
│   ├── inference/          # artifact loaders with safe fallbacks
│   └── cli.py              # standalone runner (no Django)
├── management/commands/    # ai_generate_dataset, ai_train_recommender, ...
├── services/
│   └── ml_service.py       # Django-facing facade used by views
└── tests/                  # automated tests for all of the above
```

## What is trained vs. pretrained

We are explicit about provenance — nothing pretrained is presented as trained
from scratch.

| Component | Status | Notes |
|-----------|--------|-------|
| Popularity baseline | **In-house, deterministic** | No learning; ranks items by interaction weight. |
| Hybrid recommender | **Trained from scratch** | Truncated-SVD matrix factorization + TF-IDF content model, fitted on the supplied interaction data. |
| TF-IDF embedding index | **Fitted locally** | scikit-learn `TfidfVectorizer` over catalog text. |
| `all-MiniLM-L6-v2` embeddings | **Pretrained (used as-is, optional)** | Apache-2.0, ~22M params, CPU-friendly. Not fine-tuned here. |
| `google/flan-t5-small` summaries | **Pretrained (used as-is, optional)** | Apache-2.0. Not fine-tuned here. |
| Ollama LLM (e.g. `qwen2.5:0.5b`) | **Pretrained (served locally, optional)** | Apache-2.0. No cloud, no API keys. |
| Extractive summarizer | **In-house, deterministic** | Frequency-based sentence ranking. |

## Hardware & dependency reality

This project is developed against **Python 3.14**, for which PyTorch wheels are
not yet published. The engine is therefore built so that the core — the
baseline, the trained hybrid recommender, TF-IDF semantic search and the
extractive summarizer — runs on **CPU with scikit-learn + NumPy only**.

Optional backends activate automatically when their dependencies are present:

* `sentence-transformers` + `torch` → pretrained semantic embeddings.
* `transformers` + `torch` → pretrained summarization.
* A running [Ollama](https://ollama.com) server → local open-weight LLM.

When they are unavailable the engine **falls back silently and deterministically**
and never raises. See `requirements/ai.txt` for the optional installs.

### Installing the optional backends

```bash
# CPU PyTorch (only if wheels exist for your Python version)
pip install torch --index-url https://download.pytorch.org/whl/cpu

pip install sentence-transformers transformers

# Local LLM runtime (separate application, not a Python dependency)
#   1. install Ollama from https://ollama.com
#   2. pull a small open-weight model
ollama pull qwen2.5:0.5b
#   3. enable it in settings
export AI_LLM_ENABLED=true
```

## Licenses

Every model and dataset is registered in `ml/licenses.py` with its SPDX license,
source and provenance. The test suite asserts that the components enabled by
default are all permissive and that non-permissive components (Meta Llama
Community License, MovieLens research license) are explicitly flagged and
disabled by default.

| Identifier | License | Kind |
|------------|---------|------|
| `tfidf_baseline` | BSD-3-Clause | baseline |
| `popularity_baseline` | BSD-3-Clause | baseline |
| `hybrid_recommender` | BSD-3-Clause | trained |
| `all-MiniLM-L6-v2` | Apache-2.0 | optional pretrained |
| `flan-t5-small` | Apache-2.0 | optional pretrained |
| `qwen2.5-0.5b-instruct` | Apache-2.0 | optional pretrained |
| `llama3.2-1b` | Llama-3.2-Community | optional, **disabled** |
| `synthetic` | CC0-1.0 | dataset |
| `catalog_activity` | BSD-3-Clause | dataset (first-party) |
| `movielens-100k` | GroupLens-Research | dataset, **disabled** |

## Data

Training and evaluation use one of two sources:

1. **Synthetic** (`ml/data/synthetic.py`, default) — deterministically generated
   from a seed. Users and items get latent factor vectors and interactions are
   sampled from a softmax over their inner product, so a factorization model has
   real structure to recover. This is what makes the baseline-vs-model
   comparison meaningful. It is synthetic, and no number derived from it is a
   real-world performance claim.
2. **First-party activity** (`--source db`) — the app's own `UserActivityLog`
   and order data. No third-party user data is ever bundled.

## Reproducing the models

Model files live in `ai_artifacts/` (git-ignored) and are **never committed**.

### Via Django management commands

```bash
# 1. Generate a synthetic dataset (optional; training generates in-memory too)
python manage.py ai_generate_dataset --users 200 --items 120 --seed 42

# 2. Train + evaluate the recommender (baseline vs. learned model)
python manage.py ai_train_recommender
python manage.py ai_train_recommender --source db        # use first-party data

# 3. Build the semantic-search embedding index
python manage.py ai_build_embedding_index
python manage.py ai_build_embedding_index --backend sentence-transformers  # optional

# 4. Re-evaluate the saved recommender against the baseline
python manage.py ai_evaluate_recommender

# 5. Summarize text locally (no cloud)
python manage.py ai_summarize --text "Great battery. Sharp camera. Slow shipping."
```

### Via the standalone runner (no Django)

```bash
python -m apps.ai_engine.ml.cli generate --users 300 --items 150 --out dataset.json
python -m apps.ai_engine.ml.cli train
python -m apps.ai_engine.ml.cli search-index
python -m apps.ai_engine.ml.cli recommend --user u0 --k 10
python -m apps.ai_engine.ml.cli search --query "premium electronics"
python -m apps.ai_engine.ml.cli summarize --text "..."
```

## Reproducibility & versioning

* A single seed drives dataset generation, the train/validation/test split and
  the SVD initialization (`SplitParams.seed`, default `42`).
* Every saved artifact carries a `metadata.json` manifest with the seed and
  hyper-parameters, the dataset fingerprint, the git commit, and the versions of
  Python/NumPy/SciPy/pandas/scikit-learn.
* Models are versioned by timestamp under
  `ai_artifacts/<name>/<version>/` with a `latest` pointer.
* The learned model is only promoted when it **matches or beats the popularity
  baseline on validation NDCG@10**; otherwise the baseline is saved. We never
  ship a model that is worse than the reference.
* Metrics are only ever computed from a held-out split. No metric is invented or
  hard-coded.

## Evaluation metrics

`ml/evaluation/metrics.py` implements, from first principles, precision@k,
recall@k, average precision@k (MAP), NDCG@k, hit rate@k and catalog coverage.
`ml/evaluation/evaluate_recommender.py` applies one identical protocol to the
baseline and the learned model.

## Configuration

Settings (in `config/settings/base.py`) with environment overrides:

| Setting | Default | Purpose |
|---------|---------|---------|
| `AI_ARTIFACTS_DIR` | `<repo>/ai_artifacts` | Where models/indexes are written (git-ignored). |
| `AI_EMBEDDING_BACKEND` | `tfidf` | `tfidf` or `sentence-transformers`. |
| `AI_EMBEDDING_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` | Optional pretrained embedding model. |
| `AI_LLM_ENABLED` | `false` | Enable the optional local LLM. |
| `AI_LLM_BACKEND` | `ollama` | Local LLM runtime. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint. |
| `OLLAMA_MODEL` | `qwen2.5:0.5b` | Small open-weight model. |

## Tests

```bash
pytest apps/ai_engine -q
```

Coverage includes: license/permissive-default guarantees, ranking metrics,
dataset generation and splits, the baseline, the learned hybrid recommender
(ranking, cold start, determinism, baseline-beating property), embeddings and
semantic search, the summarizer and assistant fallbacks, the artifact registry
and versioning, the training pipeline, the inference loaders, the CLI, the
management commands and the Django facade.
