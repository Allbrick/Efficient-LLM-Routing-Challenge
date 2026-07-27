from scripts.download_public_dataset_samples import (
    expected_from_mt_bench,
    first_user_prompt,
    infer_expected_min_model,
)


def test_first_user_prompt_extracts_user_content():
    conversation = [{"role": "user", "content": "Write a summary."}, {"role": "assistant", "content": "Ok"}]

    assert first_user_prompt(conversation) == "Write a summary."


def test_expected_from_mt_bench_uses_strong_winner_for_hard_prompt():
    row = {"model_a": "gpt-4", "model_b": "llama-13b", "winner": "model_a"}

    assert expected_from_mt_bench(row, "Design a distributed system with security and audit controls.") == "premium"


def test_infer_expected_min_model_keeps_easy_prompt_cheap():
    assert infer_expected_min_model("Say hello politely.") == "cheap"
