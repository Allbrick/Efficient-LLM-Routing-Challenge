import os

import numpy as np
import pytest

from src.candidate_expander import CandidateExpander


@pytest.fixture
def expander():
    return CandidateExpander({"cheap": 0, "mid": 1, "premium": 2})


class TestCandidateExpander:
    def test_expand_shape(self, expander):
        prompt_features = np.array([[1.0, 2.0, 3.0]])  # (1, 3)
        candidates = ["cheap", "mid", "premium"]
        features, ids = expander.expand(prompt_features, candidates)

        assert features.shape == (3, 4)  # 3 models, 3 features + 1 model_id
        assert ids == candidates

    def test_prompt_features_replicated(self, expander):
        prompt_features = np.array([[10.0, 20.0]])
        features, _ = expander.expand(prompt_features, ["cheap", "mid"])

        np.testing.assert_array_equal(features[0, :2], [10.0, 20.0])
        np.testing.assert_array_equal(features[1, :2], [10.0, 20.0])

    def test_model_id_encoding(self, expander):
        prompt_features = np.array([[1.0]])
        features, _ = expander.expand(prompt_features, ["cheap", "mid", "premium"])

        assert features[0, -1] == 0.0  # cheap
        assert features[1, -1] == 1.0  # mid
        assert features[2, -1] == 2.0  # premium

    def test_single_candidate(self, expander):
        prompt_features = np.array([[5.0, 6.0]])
        features, ids = expander.expand(prompt_features, ["mid"])

        assert features.shape == (1, 3)
        assert ids == ["mid"]
        assert features[0, -1] == 1.0

    def test_expand_batch(self, expander):
        batch = np.array([[1.0, 2.0], [3.0, 4.0]])  # (2, 2)
        candidates = ["cheap", "mid", "premium"]
        features, indices = expander.expand_batch(batch, candidates)

        assert features.shape == (6, 3)  # 2 prompts * 3 models
        assert len(indices) == 6
        np.testing.assert_array_equal(indices, [0, 0, 0, 1, 1, 1])

    def test_save_load(self, expander, tmp_dir):
        path = os.path.join(tmp_dir, "mapping.json")
        expander.save(path)
        loaded = CandidateExpander.load(path)
        assert loaded.model_id_mapping == expander.model_id_mapping
