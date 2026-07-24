from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from routing_stack.input.semantic_features import (
    HashPromptEncoder,
    SemanticFeatureIndex,
    SentenceTransformerPromptEncoder,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an optional semantic feature index from eval specs.")
    parser.add_argument("--input", default="data/public/example_eval_specs.csv")
    parser.add_argument("--output", default="artifacts/semantic_feature_index.json")
    parser.add_argument("--encoder", choices=("hash", "sentence-transformers"), default="hash")
    parser.add_argument("--model", default="intfloat/multilingual-e5-small")
    args = parser.parse_args()

    specs = pd.read_csv(args.input)
    index = build_semantic_feature_index(specs, encoder_name=args.encoder, model_name=args.model)
    index.save(args.output)
    print(json.dumps(summarize_index(index), ensure_ascii=False, indent=2))


def build_semantic_feature_index(
    specs_df: pd.DataFrame,
    encoder_name: str = "hash",
    model_name: str = "intfloat/multilingual-e5-small",
) -> SemanticFeatureIndex:
    required = {"prompt", "expected_min_model"}
    missing = required - set(specs_df.columns)
    if missing:
        raise ValueError(f"eval specs missing required columns: {sorted(missing)}")

    clean = specs_df.dropna(subset=["prompt"]).copy()
    clean["expected_min_model"] = clean["expected_min_model"].fillna("mid").astype(str)
    clean = clean[clean["expected_min_model"].isin({"cheap", "mid", "premium"})]
    if clean.empty:
        raise ValueError("no cheap/mid/premium rows available to build semantic feature index")

    encoder = (
        SentenceTransformerPromptEncoder(model_name)
        if encoder_name == "sentence-transformers"
        else HashPromptEncoder()
    )
    return SemanticFeatureIndex.fit(
        prompts=clean["prompt"].astype(str).tolist(),
        labels=clean["expected_min_model"].astype(str).tolist(),
        encoder=encoder,
    )


def summarize_index(index: SemanticFeatureIndex) -> dict:
    return {
        "encoder_name": index.encoder_name,
        "dimension": index.dimension,
        "counts": index.counts,
        "labels": sorted(index.centroids),
    }


if __name__ == "__main__":
    main()
