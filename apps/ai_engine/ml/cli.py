"""
Standalone command-line runner for the AI engine.

Lets a developer train, evaluate and query the models without booting Django::

    python -m apps.ai_engine.ml.cli generate --users 300 --items 150
    python -m apps.ai_engine.ml.cli train --users 300 --items 150
    python -m apps.ai_engine.ml.cli search-index --users 300 --items 150
    python -m apps.ai_engine.ml.cli recommend --user u0
    python -m apps.ai_engine.ml.cli search --query "premium electronics"
    python -m apps.ai_engine.ml.cli summarize --text "..."

It mirrors the ``ai_*`` management commands so the pipeline can be reproduced
outside the web application.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import RecommenderParams, SplitParams
from .data.dataset import save_dataset
from .data.synthetic import generate_dataset
from .inference.assistant import summarize
from .inference.recommender import RecommenderInference
from .inference.semantic_search import SemanticSearchService
from .training.build_embedding_index import build_embedding_index
from .training.train_recommender import train_recommender


def _generate(args: argparse.Namespace) -> None:
    """Generate a synthetic dataset and optionally write it to disk."""
    dataset = generate_dataset(
        n_users=args.users, n_items=args.items, seed=args.seed
    )
    if args.out:
        save_dataset(Path(args.out), dataset.to_dict())
        print(f"Wrote dataset to {args.out}")
    print(
        json.dumps(
            {
                "interactions": len(dataset.interactions),
                "items": len(dataset.items),
                "users": len(dataset.users),
                "seed": args.seed,
            },
            indent=2,
        )
    )


def _train(args: argparse.Namespace) -> None:
    """Train and evaluate the recommender on synthetic data."""
    dataset = generate_dataset(n_users=args.users, n_items=args.items, seed=args.seed)
    report = train_recommender(
        dataset.interactions,
        dataset.items,
        params=RecommenderParams(
            n_components=args.components, alpha=args.alpha
        ),
        split_params=SplitParams(seed=args.seed),
        artifact_name=args.name,
    )
    print(json.dumps(report, indent=2))


def _search_index(args: argparse.Namespace) -> None:
    """Build and persist the embedding index on synthetic data."""
    dataset = generate_dataset(n_users=args.users, n_items=args.items, seed=args.seed)
    item_ids = sorted(dataset.items)
    documents = [dataset.items[item_id]["text"] for item_id in item_ids]
    report = build_embedding_index(
        item_ids, documents, backend=args.backend, artifact_name=args.name
    )
    print(json.dumps(report, indent=2))


def _recommend(args: argparse.Namespace) -> None:
    """Show recommendations from the latest artifact."""
    engine = RecommenderInference()
    print(json.dumps({"algorithm": engine.algorithm, "items": engine.recommend(args.user, args.k)}, indent=2))


def _search(args: argparse.Namespace) -> None:
    """Run a semantic search against the latest index."""
    service = SemanticSearchService()
    print(json.dumps(service.search(args.query, args.k), indent=2))


def _summarize(args: argparse.Namespace) -> None:
    """Summarize free text with the deterministic backend."""
    text = args.text
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    print(summarize([text], max_sentences=args.sentences))


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser."""
    parser = argparse.ArgumentParser(description="AI engine standalone runner")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--users", type=int, default=200)
        p.add_argument("--items", type=int, default=120)
        p.add_argument("--seed", type=int, default=42)

    gen = sub.add_parser("generate", help="generate a synthetic dataset")
    add_common(gen)
    gen.add_argument("--out", type=str, default=None)
    gen.set_defaults(func=_generate)

    train = sub.add_parser("train", help="train and evaluate the recommender")
    add_common(train)
    train.add_argument("--components", type=int, default=32)
    train.add_argument("--alpha", type=float, default=0.6)
    train.add_argument("--name", type=str, default="recommender")
    train.set_defaults(func=_train)

    index = sub.add_parser("search-index", help="build the embedding index")
    add_common(index)
    index.add_argument("--backend", type=str, default="tfidf")
    index.add_argument("--name", type=str, default="embedding_index")
    index.set_defaults(func=_search_index)

    recommend = sub.add_parser("recommend", help="recommend for a user")
    recommend.add_argument("--user", type=str, default="u0")
    recommend.add_argument("--k", type=int, default=10)
    recommend.set_defaults(func=_recommend)

    search = sub.add_parser("search", help="semantic search")
    search.add_argument("--query", type=str, required=True)
    search.add_argument("--k", type=int, default=5)
    search.set_defaults(func=_search)

    summarize_cmd = sub.add_parser("summarize", help="summarize text")
    summarize_cmd.add_argument("--text", type=str, default="")
    summarize_cmd.add_argument("--file", type=str, default=None)
    summarize_cmd.add_argument("--sentences", type=int, default=3)
    summarize_cmd.set_defaults(func=_summarize)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
