import os

import numpy as np
import pytest

from src.feature_extractor import FeatureExtractor


@pytest.fixture
def sample_prompts():
    return [
        "안녕하세요? 오늘 날씨가 어떤가요?",
        "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
        "Solve the integral: ∫ x² dx from 0 to 1",
        "Write a step-by-step comparison of React vs Vue for a legal document management system",
        "",
    ]


@pytest.fixture
def fitted_extractor(sample_prompts):
    ext = FeatureExtractor(tfidf_max_features=100, svd_n_components=10)
    ext.fit(sample_prompts)
    return ext


class TestFeatureExtractor:
    def test_fit_transform_shape(self, fitted_extractor, sample_prompts):
        features = fitted_extractor.transform(sample_prompts)
        assert features.shape[0] == len(sample_prompts)
        assert features.shape[1] == fitted_extractor.feature_dim

    def test_consistent_dim(self, fitted_extractor):
        f1 = fitted_extractor.transform(["hello"])
        f2 = fitted_extractor.transform(["a much longer prompt with many words"])
        assert f1.shape[1] == f2.shape[1]

    def test_empty_string(self, fitted_extractor):
        features = fitted_extractor.transform([""])
        assert features.shape == (1, fitted_extractor.feature_dim)
        assert not np.any(np.isnan(features))

    def test_code_detection(self, fitted_extractor):
        code_prompt = "def hello(): print('world')"
        no_code_prompt = "오늘 저녁 뭐 먹을까?"
        f_code = fitted_extractor.transform([code_prompt])
        f_no_code = fitted_extractor.transform([no_code_prompt])
        # has_code는 handcrafted features의 pattern 그룹 첫 번째 (index 11)
        assert f_code[0, 11] == 1.0
        assert f_no_code[0, 11] == 0.0

    def test_math_detection(self, fitted_extractor):
        math_prompt = "Calculate ∫ x² dx"
        f_math = fitted_extractor.transform([math_prompt])
        # has_math_symbols는 index 12
        assert f_math[0, 12] == 1.0

    def test_transform_before_fit_raises(self):
        ext = FeatureExtractor()
        with pytest.raises(RuntimeError, match="fit"):
            ext.transform(["hello"])

    def test_save_load(self, fitted_extractor, sample_prompts, tmp_dir):
        path = os.path.join(tmp_dir, "pipeline.pkl")
        fitted_extractor.save(path)

        loaded = FeatureExtractor.load(path)
        original = fitted_extractor.transform(sample_prompts)
        reloaded = loaded.transform(sample_prompts)
        np.testing.assert_array_almost_equal(original, reloaded)

    def test_dtype_float32(self, fitted_extractor):
        features = fitted_extractor.transform(["test prompt"])
        assert features.dtype == np.float32
