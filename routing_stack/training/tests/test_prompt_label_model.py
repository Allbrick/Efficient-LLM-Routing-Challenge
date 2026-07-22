from routing_stack.training.prompt_label_model import PromptLabelRouterModel


def test_prompt_label_model_learns_general_task_shape():
    prompts = [
        "안녕",
        "1024MB는 몇 GB인가?",
        "FooDB와 BarQueue의 차이를 비교해줘",
        "XAlgo를 구현하고 시간복잡도를 증명해줘",
        "YSystem의 운영 전략을 설계하고 한계를 분석해줘",
        "오늘은 무슨 요일이야?",
    ]
    labels = ["cheap", "cheap", "mid", "premium", "premium", "cheap"]

    model = PromptLabelRouterModel().fit(prompts, labels)

    assert model.predict("2048MB는 몇 GB인가?").selected_label == "cheap"
    assert model.predict("NewDB와 OldDB를 언제 각각 선택하는 것이 좋은가?").selected_label in {"mid", "premium"}
    assert model.predict("QAlgo를 구현하고 복잡도를 증명해줘").selected_label == "premium"


def test_prompt_label_model_exposes_geometric_memory():
    prompts = [
        "hello",
        "what day is today",
        "compare FooDB and BarQueue",
        "design a service deployment strategy",
        "implement cache and prove complexity",
        "analyze execution plan and suggest indexes",
    ]
    labels = ["cheap", "cheap", "mid", "mid", "premium", "premium"]

    model = PromptLabelRouterModel().fit(prompts, labels)
    prediction = model.predict("compare NewDB and OldQueue")

    assert prediction.raw_probabilities
    assert prediction.geometry["centroid_distances"]
    assert prediction.geometry["centroid_probabilities"]
    assert prediction.geometry["nearest_examples"]
    assert prediction.geometry["nearest_centroid_label"] in {"cheap", "mid", "premium"}
