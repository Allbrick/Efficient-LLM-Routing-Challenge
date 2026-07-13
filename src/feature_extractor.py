from __future__ import annotations

import re
from typing import List, Optional

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import Pipeline


# --- Domain / Task keyword dictionaries ---

DOMAIN_KEYWORDS = {
    "finance": ["금융", "주식", "투자", "은행", "finance", "stock", "invest", "bank", "trading", "portfolio"],
    "legal": ["법률", "법원", "계약", "소송", "legal", "law", "court", "contract", "regulation", "lawsuit"],
    "medical": ["의료", "진단", "치료", "환자", "medical", "diagnosis", "treatment", "patient", "clinical", "symptom"],
    "tech": ["프로그래밍", "소프트웨어", "알고리즘", "programming", "software", "algorithm", "database", "server", "API", "deploy"],
    "science": ["실험", "가설", "연구", "science", "experiment", "hypothesis", "research", "molecule", "physics", "chemistry"],
    "education": ["학습", "교육", "시험", "education", "learning", "exam", "curriculum", "student", "teacher"],
}

TASK_KEYWORDS = {
    "summarization": ["요약", "summarize", "summary", "tldr", "핵심", "간단히", "brief", "condense"],
    "code_generation": ["코드", "함수", "구현", "code", "function", "implement", "script", "class", "def ", "program"],
    "translation": ["번역", "translate", "translation", "영어로", "한국어로", "in english", "in korean"],
    "reasoning": ["추론", "논리", "증명", "reason", "logic", "prove", "deduce", "infer", "therefore", "왜냐하면"],
    "math": ["수학", "계산", "방정식", "math", "calculate", "equation", "solve", "integral", "derivative"],
    "qa": ["질문", "답변", "무엇", "어떻게", "question", "answer", "what", "how", "explain", "describe"],
    "creative": ["창작", "작성", "이야기", "creative", "write", "story", "poem", "essay", "generate"],
}

# --- Regex patterns ---

CODE_PATTERN = re.compile(
    r"(?:def\s+\w+|class\s+\w+|import\s+\w+|from\s+\w+\s+import|"
    r"function\s+\w+|const\s+\w+|let\s+\w+|var\s+\w+|"
    r"```|#include|public\s+class|SELECT\s+|CREATE\s+TABLE)",
    re.IGNORECASE,
)

MATH_PATTERN = re.compile(
    r"[$\\∑∫∏√±×÷≤≥≠≈∞∂∇∈∉⊂⊃∪∩]|"
    r"\b(?:integral|derivative|matrix|vector|theorem|equation|polynomial|factorial)\b",
    re.IGNORECASE,
)

REASONING_PATTERN = re.compile(
    r"\b(?:step[\s-]*by[\s-]*step|first.*then|because|therefore|however|"
    r"on\s+the\s+other\s+hand|compare|contrast|pros?\s+and\s+cons?|"
    r"analyze|evaluate|consider|단계별|왜냐하면|그러므로|반면에|비교|분석)\b",
    re.IGNORECASE,
)

URL_PATTERN = re.compile(r"https?://\S+")
EMAIL_PATTERN = re.compile(r"\S+@\S+\.\S+")
LIST_PATTERN = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)
NUMBERED_LIST_PATTERN = re.compile(r"^\s*\d+[.)]\s+", re.MULTILINE)


class FeatureExtractor:
    """프롬프트 텍스트에서 수치 피처 벡터를 생성한다.

    학습 시: fit(prompts) -> transform(prompts)
    추론 시: transform(prompt)
    TF-IDF/SVD는 반드시 학습 데이터에서만 fit.
    """

    def __init__(
        self,
        tfidf_max_features: int = 5000,
        tfidf_ngram_range: tuple = (1, 2),
        svd_n_components: Optional[int] = 50,
    ):
        self.tfidf_max_features = tfidf_max_features
        self.tfidf_ngram_range = tfidf_ngram_range
        self.svd_n_components = svd_n_components
        self._text_pipeline: Optional[Pipeline] = None
        self._is_fitted = False

    def fit(self, prompts: List[str]) -> FeatureExtractor:
        steps = [
            ("tfidf", TfidfVectorizer(
                max_features=self.tfidf_max_features,
                ngram_range=self.tfidf_ngram_range,
                sublinear_tf=True,
                dtype=np.float32,
            )),
        ]
        if self.svd_n_components is not None:
            n_comp = min(self.svd_n_components, self.tfidf_max_features, len(prompts))
            steps.append(("svd", TruncatedSVD(n_components=n_comp, random_state=42)))

        self._text_pipeline = Pipeline(steps)
        self._text_pipeline.fit(prompts)
        self._is_fitted = True
        return self

    def transform(self, prompts: List[str]) -> np.ndarray:
        if not self._is_fitted:
            raise RuntimeError("FeatureExtractor.fit()을 먼저 호출하세요.")

        hand_features = np.array(
            [self._extract_handcrafted(p) for p in prompts], dtype=np.float32
        )
        text_features = self._text_pipeline.transform(prompts)
        if hasattr(text_features, "toarray"):
            text_features = text_features.toarray()
        text_features = text_features.astype(np.float32)

        return np.hstack([hand_features, text_features])

    @property
    def feature_dim(self) -> int:
        if not self._is_fitted:
            raise RuntimeError("fit 전에는 feature_dim을 알 수 없습니다.")
        hand_dim = self._handcrafted_dim()
        if self.svd_n_components is not None:
            text_dim = self._text_pipeline.named_steps["svd"].n_components
        else:
            text_dim = self.tfidf_max_features
        return hand_dim + text_dim

    # ---- Handcrafted features ----

    def _handcrafted_dim(self) -> int:
        n_domain = len(DOMAIN_KEYWORDS)
        n_task = len(TASK_KEYWORDS)
        return 6 + 5 + 6 + n_domain + n_task + 4  # stats + structural + pattern + domain + task + reasoning

    def _extract_handcrafted(self, prompt: str) -> List[float]:
        features: List[float] = []

        # Text stats (6)
        tokens = prompt.split()
        features.append(len(prompt))                         # prompt_length
        features.append(len(tokens))                         # token_count (whitespace)
        words = [t for t in tokens if t.isalpha()]
        features.append(len(words))                          # word_count
        features.append(
            np.mean([len(w) for w in words]) if words else 0.0  # avg_word_length
        )
        features.append(prompt.count(".") + prompt.count("!") + prompt.count("?"))  # sentence_count (approx)
        unique_chars = len(set(prompt))
        features.append(unique_chars / max(len(prompt), 1))  # char_diversity

        # Structural (5)
        lines = prompt.split("\n")
        features.append(len(lines))                          # line_count
        features.append(max((len(l) for l in lines), default=0))  # max_line_length
        features.append(1.0 if LIST_PATTERN.search(prompt) else 0.0)          # has_list
        features.append(1.0 if NUMBERED_LIST_PATTERN.search(prompt) else 0.0)  # has_numbered_list
        paragraph_count = sum(1 for l in lines if l.strip() == "") + 1
        features.append(paragraph_count)                     # paragraph_count

        # Pattern / regex (6)
        features.append(1.0 if CODE_PATTERN.search(prompt) else 0.0)       # has_code
        features.append(1.0 if MATH_PATTERN.search(prompt) else 0.0)       # has_math_symbols
        features.append(1.0 if URL_PATTERN.search(prompt) else 0.0)        # has_url
        features.append(1.0 if EMAIL_PATTERN.search(prompt) else 0.0)      # has_email
        special = sum(1 for c in prompt if not c.isalnum() and not c.isspace())
        features.append(special / max(len(prompt), 1))                      # special_char_ratio
        features.append(prompt.count("?"))                                   # question_mark_count

        # Domain keyword scores (n_domain)
        prompt_lower = prompt.lower()
        for _domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in prompt_lower)
            features.append(float(score))

        # Task keyword scores (n_task)
        for _task, keywords in TASK_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in prompt_lower)
            features.append(float(score))

        # Reasoning indicators (4)
        features.append(1.0 if REASONING_PATTERN.search(prompt) else 0.0)     # has_reasoning
        features.append(1.0 if "비교" in prompt or "compare" in prompt_lower else 0.0)  # has_comparison
        multi_constraint = len(re.findall(r"\b(?:and|or|but|그리고|또는|하지만)\b", prompt_lower))
        features.append(float(multi_constraint))                               # multi_constraint_count
        reasoning_kw_count = len(REASONING_PATTERN.findall(prompt))
        features.append(float(reasoning_kw_count))                             # reasoning_keyword_count

        return features

    def save(self, path: str) -> None:
        joblib.dump(
            {
                "tfidf_max_features": self.tfidf_max_features,
                "tfidf_ngram_range": self.tfidf_ngram_range,
                "svd_n_components": self.svd_n_components,
                "text_pipeline": self._text_pipeline,
            },
            path,
        )

    @classmethod
    def load(cls, path: str) -> FeatureExtractor:
        data = joblib.load(path)
        obj = cls(
            tfidf_max_features=data["tfidf_max_features"],
            tfidf_ngram_range=data["tfidf_ngram_range"],
            svd_n_components=data["svd_n_components"],
        )
        obj._text_pipeline = data["text_pipeline"]
        obj._is_fitted = True
        return obj
