from routing_stack.training.prompt_label_csv import read_prompt_label_csv_file, read_prompt_label_csv_text


def test_prompt_label_csv_accepts_prompt_routing_score_headers():
    rows = read_prompt_label_csv_text("prompt,routing_score\n안녕,8\n")

    assert rows == [{"prompt": "안녕", "routing_score": 8.0}]


def test_prompt_label_csv_accepts_utf8_bom_header():
    rows = read_prompt_label_csv_text("\ufeffprompt,routing_score\n안녕,8\n")

    assert rows == [{"prompt": "안녕", "routing_score": 8.0}]


def test_prompt_label_csv_accepts_korean_alias_headers_with_index():
    rows = read_prompt_label_csv_text("번호,프롬프트,점수\n1,안녕,8\n")

    assert rows == [{"prompt": "안녕", "routing_score": 8.0}]


def test_prompt_label_csv_falls_back_to_first_two_non_index_columns():
    rows = read_prompt_label_csv_text("id,question,target\n1,안녕,8\n")

    assert rows == [{"prompt": "안녕", "routing_score": 8.0}]


def test_prompt_label_csv_file_accepts_txt_extension(tmp_path):
    txt_path = tmp_path / "prompt_labels.txt"
    txt_path.write_text("prompt,routing_score\nhello,8\ncompare A and B,55\n", encoding="utf-8")

    rows = read_prompt_label_csv_file(txt_path)

    assert rows == [
        {"prompt": "hello", "routing_score": 8.0},
        {"prompt": "compare A and B", "routing_score": 55.0},
    ]


def test_prompt_label_csv_repairs_unquoted_commas_in_prompt():
    rows = read_prompt_label_csv_text(
        "prompt,routing_score\n"
        "React, Zustand, TanStack Query architecture,85\n"
    )

    assert rows == [
        {"prompt": "React,Zustand,TanStack Query architecture", "routing_score": 85.0}
    ]


def test_prompt_label_csv_accepts_legacy_labels_as_migration_input():
    rows = read_prompt_label_csv_text("Prompt,정답\n안녕,cheap\n비교해줘,mid\n설계해줘,premium\n")

    assert rows == [
        {"prompt": "안녕", "routing_score": 20.0},
        {"prompt": "비교해줘", "routing_score": 55.0},
        {"prompt": "설계해줘", "routing_score": 85.0},
    ]
