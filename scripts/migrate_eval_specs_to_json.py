from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


DATA_PATH = Path("data/public/example_eval_specs.csv")


CLARIFICATION_SPECS = {
    "e301": {
        "required_requests": [
            {"any_of": ["계약서 내용", "계약 전문", "contract text"]},
            {"any_of": ["관할 법률", "국가", "지역", "jurisdiction"]},
        ],
        "clarification_markers": [{"any_of": ["판단할 수 없습니다", "제공", "provide"]}],
        "forbidden_claims": ["유효합니다.", "valid."],
        "pass_threshold": 0.7,
    },
    "e302": {
        "required_requests": [
            {"any_of": ["코드", "code"]},
            {"any_of": ["기대 동작", "expected behavior"]},
            {"any_of": ["오류 메시지", "error message"]},
        ],
        "clarification_markers": [{"any_of": ["제공", "보내", "provide"]}],
        "forbidden_claims": ["수정했습니다."],
        "pass_threshold": 0.7,
    },
    "e402": {
        "required_requests": [
            {"any_of": ["조항 전문", "문구", "contract clause"]},
            {"any_of": ["관할 법률", "국가", "지역", "jurisdiction"]},
        ],
        "clarification_markers": [{"any_of": ["단정할 수 없습니다", "제공", "cannot"]}],
        "forbidden_claims": ["무효입니다."],
        "pass_threshold": 0.7,
    },
    "e701": {
        "required_requests": [
            {"any_of": ["원문", "contract clause"]},
            {"any_of": ["관할", "jurisdiction"]},
            {"any_of": ["관련 사실", "facts"]},
        ],
        "clarification_markers": [{"any_of": ["정보가 부족", "제공", "provide"]}],
        "forbidden_claims": ["가능합니다."],
        "pass_threshold": 0.7,
    },
    "e702": {
        "required_requests": [
            {"any_of": ["원문", "actual report"]},
            {"any_of": ["관련 사실", "상황", "context"]},
        ],
        "clarification_markers": [{"any_of": ["정보가 부족", "제공", "provide"]}],
        "forbidden_claims": ["가능합니다."],
        "pass_threshold": 0.7,
    },
    "e703": {
        "required_requests": [
            {"any_of": ["원문", "코드", "code"]},
            {"any_of": ["오류", "error message"]},
        ],
        "clarification_markers": [{"any_of": ["정보가 부족", "제공", "provide"]}],
        "forbidden_claims": ["가능합니다."],
        "pass_threshold": 0.7,
    },
    "e704": {
        "required_requests": [
            {"any_of": ["원문", "데이터", "data"]},
            {"any_of": ["관련 사실", "맥락", "context"]},
        ],
        "clarification_markers": [{"any_of": ["정보가 부족", "제공", "provide"]}],
        "forbidden_claims": ["가능합니다.", "100%"],
        "pass_threshold": 0.7,
    },
}


def dump_spec(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def split_terms(value: str) -> list[str]:
    return [term.strip() for term in re.split(r"\s*\|\s*|,\s*", value) if term.strip()]


def convert_row(row: pd.Series) -> str:
    prompt_id = str(row["prompt_id"])
    evaluation_type = str(row["evaluation_type"])
    legacy = "" if pd.isna(row["test_spec"]) else str(row["test_spec"])

    if legacy.strip().startswith("{"):
        return legacy

    if evaluation_type in {"exact_match", "numeric_count"}:
        return dump_spec({"note": legacy}) if legacy else ""

    if evaluation_type == "exact_json":
        return dump_spec({"compare": "semantic_json_with_types"})

    if evaluation_type == "unit_test":
        if "assert " in legacy:
            return dump_spec(
                {
                    "language": "python",
                    "assertions": [part.strip() for part in legacy.split(";") if part.strip()],
                    "pass_threshold": 1.0,
                }
            )
        if "raises ValueError" in legacy:
            parts = [part.strip() for part in legacy.split(";") if part.strip()]
            assertions = [
                part
                for part in parts
                if "raises " not in part and "recursion forbidden" not in part
            ]
            raises = []
            for part in parts:
                match = re.match(r"(.+?)\s+raises\s+(\w+)", part)
                if match:
                    raises.append({"expr": match.group(1).strip(), "error": match.group(2).strip()})
            forbidden = ["recursive_call"] if "recursion forbidden" in legacy else []
            return dump_spec(
                {
                    "language": "python",
                    "assertions": assertions,
                    "raises": raises,
                    "forbidden": forbidden,
                    "pass_threshold": 1.0,
                }
            )
        return dump_spec({"required_concepts": [part.strip() for part in legacy.split(";") if part.strip()], "pass_threshold": 0.7})

    if evaluation_type == "constraint_check":
        payload = {"pass_threshold": 0.8}
        bullet_match = re.search(r"bullet_count\s*=\s*(\d+)", legacy)
        include_match = re.search(r"must_include\s*=\s*([^;]+)", legacy)
        if bullet_match:
            payload["bullet_count"] = int(bullet_match.group(1))
        if include_match:
            payload["required_terms"] = split_terms(include_match.group(1))
        return dump_spec(payload)

    if evaluation_type == "rubric_check":
        required_match = re.search(r"required\s*=\s*([^;]+)", legacy)
        if required_match:
            return dump_spec({"required_concepts": split_terms(required_match.group(1)), "relations": [], "forbidden_claims": [], "critical_failures": [], "pass_threshold": 0.7})
        return dump_spec({"required_concepts": [legacy], "relations": [], "forbidden_claims": [], "critical_failures": [], "pass_threshold": 0.7})

    if evaluation_type == "required_clarification":
        return dump_spec(CLARIFICATION_SPECS.get(prompt_id, {"required_requests": [], "clarification_markers": [], "forbidden_claims": [], "pass_threshold": 0.7}))

    return legacy


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    df["test_spec"] = df.apply(convert_row, axis=1)
    df.to_csv(DATA_PATH, index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
