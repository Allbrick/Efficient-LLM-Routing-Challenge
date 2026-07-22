from routing_stack.training.prompt_label_csv import read_prompt_label_csv_file, read_prompt_label_csv_text


def test_prompt_label_csv_accepts_prompt_answer_headers():
    rows = read_prompt_label_csv_text("Prompt,정답\n안녕,cheap\n")

    assert rows == [{"prompt": "안녕", "label": "cheap"}]


def test_prompt_label_csv_accepts_utf8_bom_header():
    rows = read_prompt_label_csv_text("\ufeffPrompt,정답\n안녕,cheap\n")

    assert rows == [{"prompt": "안녕", "label": "cheap"}]


def test_prompt_label_csv_accepts_korean_alias_headers_with_index():
    rows = read_prompt_label_csv_text("번호,프롬프트,예상\n1,안녕,cheap\n")

    assert rows == [{"prompt": "안녕", "label": "cheap"}]


def test_prompt_label_csv_falls_back_to_first_two_non_index_columns():
    rows = read_prompt_label_csv_text("id,question,target\n1,안녕,cheap\n")

    assert rows == [{"prompt": "안녕", "label": "cheap"}]


def test_prompt_label_csv_file_accepts_txt_extension(tmp_path):
    txt_path = tmp_path / "prompt_labels.txt"
    txt_path.write_text("Prompt,label\nhello,cheap\ncompare A and B,mid\n", encoding="utf-8")

    rows = read_prompt_label_csv_file(txt_path)

    assert rows == [
        {"prompt": "hello", "label": "cheap"},
        {"prompt": "compare A and B", "label": "mid"},
    ]
