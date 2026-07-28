from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from router_impls.geometric.features import MODEL_ORDER, MODEL_RANK


@dataclass(frozen=True)
class EvaluationResult:
    success: bool
    score: float
    reason: str


@dataclass(frozen=True)
class OutputSufficiency:
    sufficient: bool
    score: float
    failure_reasons: list[str]
    suggested_action: str


class RubricJudge(Protocol):
    def judge(
        self,
        *,
        prompt: str,
        candidate_output: str,
        rubric: dict[str, Any],
        budget_tier: str = "",
    ) -> OutputSufficiency:
        ...


class HeuristicRubricJudge:
    """Optional no-network judge fallback for rubric-like outputs."""

    def judge(
        self,
        *,
        prompt: str,
        candidate_output: str,
        rubric: dict[str, Any],
        budget_tier: str = "",
    ) -> OutputSufficiency:
        required = _as_list_static(rubric.get("required_concepts")) + _as_list_static(rubric.get("required_terms"))
        forbidden = _as_list_static(rubric.get("forbidden_claims")) + _as_list_static(rubric.get("critical_failures"))
        text = str(candidate_output or "").lower()
        if forbidden and any(str(item).lower() in text for item in forbidden):
            return OutputSufficiency(False, 0.0, ["judge_forbidden_claim"], "escalate")
        if not required:
            enough_length = len(str(candidate_output or "").split()) >= int(rubric.get("min_words", 12))
            return OutputSufficiency(
                sufficient=enough_length,
                score=0.65 if enough_length else 0.25,
                failure_reasons=[] if enough_length else ["judge_output_too_short"],
                suggested_action="select_output" if enough_length else "escalate",
            )
        matched = sum(1 for item in required if str(item).lower() in text)
        score = matched / max(len(required), 1)
        threshold = float(rubric.get("pass_threshold", 0.7))
        return OutputSufficiency(
            sufficient=score >= threshold,
            score=score,
            failure_reasons=[] if score >= threshold else ["judge_missing_required_concepts"],
            suggested_action="select_output" if score >= threshold else "escalate",
        )


class OutputEvaluator:
    """Deterministic evaluator driven by structured JSON specs.

    The evaluator does not map prompt text to model choices. It evaluates a
    candidate output against the schema stored in `test_spec`. If a spec needs
    language variants or synonyms, those variants must live in data, not in this
    evaluator.
    """

    def __init__(self, fallback_threshold: float = 0.85, rubric_judge: RubricJudge | None = None):
        self.fallback_threshold = fallback_threshold
        self.rubric_judge = rubric_judge

    def assess_sufficiency(
        self,
        output: str,
        spec: dict | None,
        quality_score: float | None = None,
        prompt: str = "",
        budget_tier: str = "",
    ) -> OutputSufficiency:
        result = self.evaluate(output, spec, quality_score)
        if result.success:
            return OutputSufficiency(
                sufficient=True,
                score=float(result.score),
                failure_reasons=[],
                suggested_action="select_output",
            )

        evaluation_type = str((spec or {}).get("evaluation_type", "")).strip()
        raw_test_spec = "" if not spec or pd.isna(spec.get("test_spec", "")) else str(spec.get("test_spec", ""))
        rubric = self._parse_test_spec(raw_test_spec)
        if evaluation_type == "rubric_check" and self.rubric_judge is not None:
            judged = self.rubric_judge.judge(
                prompt=prompt,
                candidate_output=str(output),
                rubric=rubric,
                budget_tier=budget_tier,
            )
            if judged.sufficient or judged.score > result.score:
                return judged
        if evaluation_type in {"required_clarification", "refusal_check"}:
            suggested_action = "abstain"
        else:
            suggested_action = "escalate"
        return OutputSufficiency(
            sufficient=False,
            score=float(result.score),
            failure_reasons=[result.reason],
            suggested_action=suggested_action,
        )

    def evaluate(self, output: str, spec: dict | None, quality_score: float | None = None) -> EvaluationResult:
        if not spec:
            return self._quality_fallback(quality_score, "quality_fallback_no_spec")

        evaluation_type = str(spec.get("evaluation_type", "")).strip()
        reference = "" if pd.isna(spec.get("reference_answer", "")) else str(spec.get("reference_answer", ""))
        raw_test_spec = "" if pd.isna(spec.get("test_spec", "")) else str(spec.get("test_spec", ""))
        test_spec = self._parse_test_spec(raw_test_spec)

        if evaluation_type in {"exact_match", "numeric_count"}:
            success = str(output).strip() == reference
            return EvaluationResult(success, 1.0 if success else 0.0, evaluation_type)

        if evaluation_type == "numeric_check":
            return self._numeric_check(output, reference, test_spec)

        if evaluation_type == "exact_json":
            return self._exact_json(output, reference, quality_score)

        if evaluation_type == "required_clarification":
            return self._required_clarification(output, test_spec)

        if evaluation_type == "refusal_check":
            return self._refusal_check(output, test_spec)

        if evaluation_type == "unit_test":
            return self._unit_test(output, test_spec, quality_score)

        if evaluation_type == "constraint_check":
            return self._constraint_check(output, test_spec, quality_score)

        if evaluation_type == "rubric_check":
            return self._rubric_check(output, test_spec, quality_score)

        return self._quality_fallback(quality_score, "unknown_eval_quality_fallback")

    def expected_success_from_min_model(self, model_id: str, expected_min_model: str) -> bool:
        if expected_min_model not in MODEL_RANK:
            return False
        return MODEL_RANK[model_id] >= MODEL_RANK[expected_min_model]

    def _quality_fallback(self, quality_score: float | None, reason: str) -> EvaluationResult:
        if quality_score is None:
            return EvaluationResult(False, 0.0, reason)
        score = float(quality_score)
        return EvaluationResult(score >= self.fallback_threshold, score, reason)

    def _parse_test_spec(self, raw_test_spec: str) -> dict[str, Any]:
        text = str(raw_test_spec or "").strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"legacy_text": text}
        return parsed if isinstance(parsed, dict) else {}

    def _numeric_check(self, output: str, reference: str, test_spec: dict[str, Any]) -> EvaluationResult:
        tolerance = float(test_spec.get("tolerance", 1e-9))
        output_number = self._parse_number(str(output).strip())
        reference_number = self._parse_number(str(reference).strip())
        success = (
            output_number is not None
            and reference_number is not None
            and math.isclose(output_number, reference_number, rel_tol=tolerance, abs_tol=tolerance)
        )
        return EvaluationResult(success, 1.0 if success else 0.0, "numeric_check")

    def _exact_json(self, output: str, reference: str, quality_score: float | None) -> EvaluationResult:
        if not reference:
            parsed = self._parse_json(output)
            if parsed is not None:
                return self._quality_fallback(quality_score, "exact_json_valid_no_reference")
            return EvaluationResult(False, 0.0, "exact_json_invalid_no_reference")

        output_json = self._parse_json(output)
        reference_json = self._parse_json(reference)
        success = output_json is not None and reference_json is not None and output_json == reference_json
        return EvaluationResult(success, 1.0 if success else 0.0, "exact_json")

    def _unit_test(self, output: str, test_spec: dict[str, Any], quality_score: float | None) -> EvaluationResult:
        if test_spec.get("language") == "python":
            return self._python_unit_test(output, test_spec)

        score, reason = self._structured_score(output, test_spec)
        if reason != "no_structured_requirements":
            return EvaluationResult(score >= float(test_spec.get("pass_threshold", 0.7)), score, f"unit_test_{reason}")
        return self._quality_fallback(quality_score, "unit_test_quality_fallback")

    def _constraint_check(
        self, output: str, test_spec: dict[str, Any], quality_score: float | None
    ) -> EvaluationResult:
        score, reason = self._structured_score(output, test_spec)
        if reason == "no_structured_requirements":
            return self._quality_fallback(quality_score, "constraint_check_quality_fallback")
        return EvaluationResult(
            score >= float(test_spec.get("pass_threshold", 0.8)),
            score,
            f"constraint_check_{reason}",
        )

    def _rubric_check(self, output: str, test_spec: dict[str, Any], quality_score: float | None) -> EvaluationResult:
        score, reason = self._structured_score(output, test_spec)
        if reason == "no_structured_requirements":
            return self._quality_fallback(quality_score, "rubric_check_quality_fallback")
        return EvaluationResult(
            score >= float(test_spec.get("pass_threshold", 0.7)),
            score,
            f"rubric_check_{reason}",
        )

    def _required_clarification(self, output: str, test_spec: dict[str, Any]) -> EvaluationResult:
        text = str(output).strip()
        required_requests = self._as_list(test_spec.get("required_requests"))
        clarification_markers = self._as_list(test_spec.get("clarification_markers"))
        forbidden_claims = self._as_list(test_spec.get("forbidden_claims"))

        required_score = self._coverage(text, required_requests)
        marker_score = self._coverage(text, clarification_markers) if clarification_markers else 1.0
        forbidden_hits = self._matched_count(text, forbidden_claims)

        if not required_requests and not clarification_markers:
            return EvaluationResult(False, 0.0, "required_clarification_no_schema")

        score = 0.7 * required_score + 0.3 * marker_score
        if forbidden_hits:
            score = min(score, 0.4)

        threshold = float(test_spec.get("pass_threshold", 0.7))
        return EvaluationResult(score >= threshold, score, "required_clarification")

    def _refusal_check(self, output: str, test_spec: dict[str, Any]) -> EvaluationResult:
        text = str(output).strip()
        required_claims = self._as_list(test_spec.get("required_claims"))
        required_actions = self._as_list(test_spec.get("required_actions"))
        forbidden_claims = self._as_list(test_spec.get("forbidden_claims"))
        critical_failures = self._as_list(test_spec.get("critical_failures"))

        if not required_claims and not required_actions:
            return EvaluationResult(False, 0.0, "refusal_check_no_schema")

        components = []
        if required_claims:
            components.append(self._coverage(text, required_claims))
        if required_actions:
            components.append(self._coverage(text, required_actions))

        score = sum(components) / len(components)
        if self._matched_count(text, critical_failures):
            score = 0.0
        elif self._matched_count(text, forbidden_claims):
            score = min(score, 0.4)

        threshold = float(test_spec.get("pass_threshold", 0.8))
        return EvaluationResult(score >= threshold, score, "refusal_check")

    def _python_unit_test(self, output: str, test_spec: dict[str, Any]) -> EvaluationResult:
        code = self._normalize_code(self._strip_markdown_fence(output))
        assertions = [str(item) for item in self._as_list(test_spec.get("assertions"))]
        raises_checks = [item for item in self._as_list(test_spec.get("raises")) if isinstance(item, dict)]
        forbidden = self._as_list(test_spec.get("forbidden"))

        if "recursive_call" in forbidden and self._has_recursive_call(code):
            return EvaluationResult(False, 0.0, "unit_test_recursion_forbidden")

        try:
            namespace: dict[str, object] = {"__builtins__": self._safe_builtins()}
            exec(code, namespace, namespace)
            total = len(assertions) + len(raises_checks)
            if total == 0:
                return EvaluationResult(False, 0.0, "unit_test_no_executable_checks")

            passed = 0
            for assertion in assertions:
                try:
                    exec(assertion if assertion.startswith("assert ") else f"assert {assertion}", namespace, namespace)
                    passed += 1
                except Exception:
                    pass

            for check in raises_checks:
                if self._raises_check_passed(check, namespace):
                    passed += 1

            score = passed / total
            return EvaluationResult(score >= float(test_spec.get("pass_threshold", 1.0)), score, "unit_test_python")
        except Exception:
            return EvaluationResult(False, 0.0, "unit_test_python_error")

    def _raises_check_passed(self, check: dict[str, Any], namespace: dict[str, object]) -> bool:
        expr = str(check.get("expr", ""))
        error_name = str(check.get("error", ""))
        expected_error = self._safe_builtins().get(error_name)
        if not expr or not isinstance(expected_error, type):
            return False
        try:
            eval(expr, namespace, namespace)
            return False
        except Exception as exc:
            return isinstance(exc, expected_error)

    def _structured_score(self, output: str, test_spec: dict[str, Any]) -> tuple[float, str]:
        text = str(output)
        required_terms = self._as_list(test_spec.get("required_terms"))
        required_concepts = self._as_list(test_spec.get("required_concepts"))
        relations = [item for item in self._as_list(test_spec.get("relations")) if isinstance(item, dict)]
        forbidden_claims = self._as_list(test_spec.get("forbidden_claims"))
        critical_failures = self._as_list(test_spec.get("critical_failures"))

        passed_units = 0.0
        total_units = 0
        requirement_count = 0

        if required_terms:
            passed_units += self._matched_count(text, required_terms)
            total_units += len(required_terms)
            requirement_count += len(required_terms)

        if required_concepts:
            passed_units += self._matched_count(text, required_concepts)
            total_units += len(required_concepts)
            requirement_count += len(required_concepts)

        if relations:
            passed_units += sum(1 for relation in relations if self._relation_present(text, relation))
            total_units += len(relations)
            requirement_count += len(relations)

        bullet_count = test_spec.get("bullet_count")
        if bullet_count is not None:
            passed_units += 1.0 if self._count_bullets(text) == int(bullet_count) else 0.0
            total_units += 1
            requirement_count += 1

        if total_units == 0:
            return 0.0, "no_structured_requirements"

        score = passed_units / total_units
        if self._matched_count(text, critical_failures):
            score = 0.0
        elif self._matched_count(text, forbidden_claims):
            score = min(score, 0.5)

        return score, f"{requirement_count}_requirements"

    def _coverage(self, text: str, requirements: list[Any]) -> float:
        if not requirements:
            return 1.0
        matched = self._matched_count(text, requirements)
        return matched / len(requirements)

    def _matched_count(self, text: str, requirements: list[Any]) -> int:
        normalized_text = text.lower()
        return sum(1 for requirement in requirements if self._requirement_present(normalized_text, requirement))

    def _requirement_present(self, normalized_text: str, requirement: Any) -> bool:
        if isinstance(requirement, dict):
            any_of = self._as_list(requirement.get("any_of"))
            all_of = self._as_list(requirement.get("all_of"))
            if any_of:
                return any(str(item).lower() in normalized_text for item in any_of)
            if all_of:
                return all(str(item).lower() in normalized_text for item in all_of)
            return False
        return str(requirement).lower() in normalized_text

    def _relation_present(self, text: str, relation: dict[str, Any]) -> bool:
        all_of = self._as_list(relation.get("all_of"))
        any_of = self._as_list(relation.get("any_of"))
        window = int(relation.get("window", 160))
        normalized_text = text.lower()
        anchors = [str(item).lower() for item in all_of]
        alternatives = [str(item).lower() for item in any_of]
        if anchors and not all(anchor in normalized_text for anchor in anchors):
            return False
        if alternatives and not any(alt in normalized_text for alt in alternatives):
            return False
        terms = anchors + alternatives[:1]
        if len(terms) < 2:
            return True
        positions = [normalized_text.find(term) for term in terms]
        return max(positions) - min(positions) <= window

    def _as_list(self, value: Any) -> list[Any]:
        return _as_list_static(value)

    def _count_bullets(self, output: str) -> int:
        normalized = self._normalize_code(str(output))
        return sum(1 for line in normalized.splitlines() if line.strip().startswith(("-", "*")))

    def _parse_number(self, text: str) -> float | None:
        try:
            return float(text)
        except ValueError:
            match = re.fullmatch(r"\s*[-+]?\d+(?:\.\d+)?\s*", text)
            return float(match.group(0)) if match else None

    def _parse_json(self, text: str):
        try:
            return json.loads(self._strip_markdown_fence(text).strip())
        except Exception:
            return None

    def _strip_markdown_fence(self, text: str) -> str:
        stripped = str(text).strip()
        match = re.fullmatch(r"```(?:\w+)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
        return match.group(1) if match else stripped

    def _normalize_code(self, code: str) -> str:
        if "\\n" in code and "\n" not in code:
            return code.replace("\\n", "\n")
        return code

    def _has_recursive_call(self, code: str) -> bool:
        function_names = re.findall(r"^\s*def\s+(\w+)\s*\(", code, flags=re.MULTILINE)
        for name in function_names:
            if len(re.findall(rf"\b{re.escape(name)}\s*\(", code)) > 1:
                return True
        return False

    def _safe_builtins(self) -> dict[str, object]:
        return {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "Exception": Exception,
            "float": float,
            "int": int,
            "isinstance": isinstance,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "range": range,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "TypeError": TypeError,
            "ValueError": ValueError,
        }


def build_training_labels(
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None,
    fallback_threshold: float = 0.85,
) -> pd.DataFrame:
    evaluator = OutputEvaluator(fallback_threshold=fallback_threshold)
    specs = {}
    if specs_df is not None and not specs_df.empty:
        specs = {row.prompt_id: row._asdict() for row in specs_df.itertuples(index=False)}
        expected_overrides = {
            row.prompt_id: str(row.expected_min_model)
            for row in specs_df.itertuples(index=False)
            if hasattr(row, "expected_min_model")
            and not pd.isna(row.expected_min_model)
            and str(row.expected_min_model).strip() == "abstain"
        }
    else:
        expected_overrides = {}

    rows = []
    for row in train_df.itertuples(index=False):
        reviewed_pass = getattr(row, "reviewed_pass", None)
        if reviewed_pass is not None and not pd.isna(reviewed_pass) and str(reviewed_pass).strip() != "":
            success = _as_bool_static(reviewed_pass)
            result = EvaluationResult(success, float(row.quality_score), "reviewed_outcome_matrix")
        else:
            spec = specs.get(row.prompt_id)
            result = evaluator.evaluate(row.model_output, spec, row.quality_score)
        rows.append(
            {
                "prompt_id": row.prompt_id,
                "model_id": row.model_id,
                "success": bool(result.success),
                "success_score": float(result.score),
                "success_reason": result.reason,
            }
        )

    labels = pd.DataFrame(rows)
    min_models = []
    for prompt_id, group in labels.groupby("prompt_id", sort=False):
        if prompt_id in expected_overrides:
            expected = expected_overrides[prompt_id]
        else:
            successful = [
                model
                for model in MODEL_ORDER
                if bool(group.loc[group["model_id"] == model, "success"].any())
            ]
            expected = successful[0] if successful else "premium"
        min_models.append({"prompt_id": prompt_id, "expected_min_model": expected})

    return labels.merge(pd.DataFrame(min_models), on="prompt_id", how="left")


def _as_list_static(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_bool_static(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "pass", "passed"}


