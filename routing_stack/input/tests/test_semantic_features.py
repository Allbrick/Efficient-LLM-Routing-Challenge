from __future__ import annotations

import numpy as np

from routing_stack.input.semantic_features import HashPromptEncoder, SemanticFeatureIndex


def test_hash_prompt_encoder_is_normalized_and_deterministic():
    encoder = HashPromptEncoder(dimension=16)

    first = encoder.encode(["요약해줘"])
    second = encoder.encode(["요약해줘"])

    assert first.shape == (1, 16)
    assert np.allclose(first, second)
    assert np.isclose(np.linalg.norm(first[0]), 1.0)


def test_semantic_feature_index_returns_distances_and_uncertainty():
    index = SemanticFeatureIndex.fit(
        prompts=["짧게 요약해줘", "멀티 리전 시스템을 설계해줘", "계약 조항의 법적 위험을 검토해줘"],
        labels=["cheap", "premium", "mid"],
        encoder=HashPromptEncoder(dimension=16),
    )

    vector = index.feature_vector("요약해줘", encoder=HashPromptEncoder(dimension=16))
    explanation = index.explain("요약해줘", encoder=HashPromptEncoder(dimension=16))

    assert vector.shape == (4,)
    assert 0.0 <= vector[-1] <= 1.0
    assert explanation["semantic_encoder"] == "hash-char-token-v1"
    assert "nearest_cheap_distance" in explanation


def test_semantic_feature_index_round_trips_dict():
    index = SemanticFeatureIndex.fit(
        prompts=["요약", "설계"],
        labels=["cheap", "premium"],
        encoder=HashPromptEncoder(dimension=8),
    )

    loaded = SemanticFeatureIndex.from_dict(index.to_dict())

    assert loaded.encoder_name == index.encoder_name
    assert loaded.dimension == 8
    assert loaded.counts == index.counts
