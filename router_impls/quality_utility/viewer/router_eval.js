window.ROUTER_EVAL = {
  "summary": {
    "data_path": "../data/public/example_train.csv",
    "artifacts_dir": "artifacts",
    "n_rows": 162,
    "n_prompts": 54,
    "models": [
      "cheap",
      "mid",
      "premium"
    ],
    "lambda_params": {
      "fast": 1.4042293233082703,
      "balanced": 0.05263157894736847,
      "premium": 0.05263157894736847
    },
    "tier_summary": {
      "fast": {
        "selection_counts": {
          "cheap": 45,
          "mid": 6,
          "premium": 3
        },
        "mean_selected_quality": 0.735556,
        "mean_selected_cost": 0.025
      },
      "balanced": {
        "selection_counts": {
          "cheap": 6,
          "mid": 43,
          "premium": 5
        },
        "mean_selected_quality": 0.898889,
        "mean_selected_cost": 0.059444
      },
      "premium": {
        "selection_counts": {
          "cheap": 6,
          "premium": 44,
          "mid": 4
        },
        "mean_selected_quality": 0.955741,
        "mean_selected_cost": 0.167778
      }
    },
    "holdout_report": {
      "holdout_mae": 0.27742826453564184,
      "tier_scores": {
        "fast": 0.8908333333333333,
        "balanced": 0.7908333333333332,
        "premium": 0.7908333333333332
      },
      "weighted_score": 0.8408333333333332
    }
  },
  "prompts": [
    {
      "prompt_id": "e001",
      "prompt": "2 + 3의 값만 숫자로 답해줘.",
      "domain": "math",
      "task_type": "exact_match",
      "benchmark_id": "cheap_exact",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 1.0,
          "cost": 0.01,
          "predicted_quality": 0.503767,
          "calibrated_quality": 0.433959,
          "model_output": "5"
        },
        {
          "model_id": "mid",
          "actual_quality": 1.0,
          "cost": 0.05,
          "predicted_quality": 0.659202,
          "calibrated_quality": 0.690891,
          "model_output": "5"
        },
        {
          "model_id": "premium",
          "actual_quality": 0.0,
          "cost": 0.2,
          "predicted_quality": 0.659202,
          "calibrated_quality": 0.716194,
          "model_output": "5입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2461,
          "utilities": {
            "cheap": 1.184802,
            "mid": 0.411387,
            "premium": -1.08835
          },
          "policy_quality": {
            "cheap": 1.184802,
            "mid": 0.707014,
            "premium": 0.31588
          }
        },
        "balanced": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2461,
          "utilities": {
            "cheap": 0.926892,
            "mid": 0.683788,
            "premium": 0.308484
          },
          "policy_quality": {
            "cheap": 0.926892,
            "mid": 0.694868,
            "premium": 0.361116
          }
        },
        "premium": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2461,
          "utilities": {
            "cheap": 0.893959,
            "mid": 0.599811,
            "premium": 0.323563
          },
          "policy_quality": {
            "cheap": 0.893959,
            "mid": 0.610891,
            "premium": 0.376194
          }
        }
      }
    },
    {
      "prompt_id": "e002",
      "prompt": "대한민국의 수도를 한 단어로 답해줘.",
      "domain": "fact",
      "task_type": "exact_match",
      "benchmark_id": "cheap_exact",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 1.0,
          "cost": 0.01,
          "predicted_quality": 0.532177,
          "calibrated_quality": 0.462369,
          "model_output": "서울"
        },
        {
          "model_id": "mid",
          "actual_quality": 1.0,
          "cost": 0.05,
          "predicted_quality": 0.695992,
          "calibrated_quality": 0.727681,
          "model_output": "서울"
        },
        {
          "model_id": "premium",
          "actual_quality": 0.0,
          "cost": 0.2,
          "predicted_quality": 0.706125,
          "calibrated_quality": 0.763117,
          "model_output": "서울입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.1693,
          "utilities": {
            "cheap": 1.278442,
            "mid": 0.421318,
            "premium": -1.047566
          },
          "policy_quality": {
            "cheap": 1.278442,
            "mid": 0.716945,
            "premium": 0.356663
          }
        },
        "balanced": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.1693,
          "utilities": {
            "cheap": 0.963743,
            "mid": 0.700625,
            "premium": 0.353872
          },
          "policy_quality": {
            "cheap": 0.963743,
            "mid": 0.711706,
            "premium": 0.406504
          }
        },
        "premium": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.1693,
          "utilities": {
            "cheap": 0.922369,
            "mid": 0.636601,
            "premium": 0.370485
          },
          "policy_quality": {
            "cheap": 0.922369,
            "mid": 0.647681,
            "premium": 0.423117
          }
        }
      }
    },
    {
      "prompt_id": "e003",
      "prompt": "문자열 'abc'를 대문자로 변환해줘.",
      "domain": "string",
      "task_type": "exact_match",
      "benchmark_id": "cheap_exact",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 1.0,
          "cost": 0.01,
          "predicted_quality": 0.573972,
          "calibrated_quality": 0.504164,
          "model_output": "ABC"
        },
        {
          "model_id": "mid",
          "actual_quality": 1.0,
          "cost": 0.05,
          "predicted_quality": 0.783442,
          "calibrated_quality": 0.81513,
          "model_output": "ABC"
        },
        {
          "model_id": "premium",
          "actual_quality": 0.0,
          "cost": 0.2,
          "predicted_quality": 0.817793,
          "calibrated_quality": 0.874784,
          "model_output": "'abc'를 대문자로 변환하면 ABC입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2296,
          "utilities": {
            "cheap": 1.269036,
            "mid": 0.52985,
            "premium": -0.93108
          },
          "policy_quality": {
            "cheap": 1.269036,
            "mid": 0.825477,
            "premium": 0.473149
          }
        },
        "balanced": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2296,
          "utilities": {
            "cheap": 0.998912,
            "mid": 0.803736,
            "premium": 0.466744
          },
          "policy_quality": {
            "cheap": 0.998912,
            "mid": 0.814816,
            "premium": 0.519376
          }
        },
        "premium": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2296,
          "utilities": {
            "cheap": 0.964164,
            "mid": 0.72405,
            "premium": 0.482153
          },
          "policy_quality": {
            "cheap": 0.964164,
            "mid": 0.73513,
            "premium": 0.534784
          }
        }
      }
    },
    {
      "prompt_id": "e004",
      "prompt": "다음 중 짝수를 고르세요: 3, 7, 10, 15",
      "domain": "math",
      "task_type": "exact_match",
      "benchmark_id": "cheap_exact",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 1.0,
          "cost": 0.01,
          "predicted_quality": 0.496953,
          "calibrated_quality": 0.427145,
          "model_output": "10"
        },
        {
          "model_id": "mid",
          "actual_quality": 1.0,
          "cost": 0.05,
          "predicted_quality": 0.708523,
          "calibrated_quality": 0.740212,
          "model_output": "10"
        },
        {
          "model_id": "premium",
          "actual_quality": 0.0,
          "cost": 0.2,
          "predicted_quality": 0.758425,
          "calibrated_quality": 0.815417,
          "model_output": "짝수는 10입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3024,
          "utilities": {
            "cheap": 1.130122,
            "mid": 0.480418,
            "premium": -0.984622
          },
          "policy_quality": {
            "cheap": 1.130122,
            "mid": 0.776045,
            "premium": 0.419607
          }
        },
        "balanced": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3024,
          "utilities": {
            "cheap": 0.913883,
            "mid": 0.74775,
            "premium": 0.408833
          },
          "policy_quality": {
            "cheap": 0.913883,
            "mid": 0.758831,
            "premium": 0.461464
          }
        },
        "premium": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3024,
          "utilities": {
            "cheap": 0.887145,
            "mid": 0.649132,
            "premium": 0.422785
          },
          "policy_quality": {
            "cheap": 0.887145,
            "mid": 0.660212,
            "premium": 0.475417
          }
        }
      }
    },
    {
      "prompt_id": "e005",
      "prompt": "다음 문자열의 앞뒤 공백을 제거해줘: '  hello  '",
      "domain": "string",
      "task_type": "exact_match",
      "benchmark_id": "cheap_exact",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 1.0,
          "cost": 0.01,
          "predicted_quality": 0.496953,
          "calibrated_quality": 0.427145,
          "model_output": "hello"
        },
        {
          "model_id": "mid",
          "actual_quality": 1.0,
          "cost": 0.05,
          "predicted_quality": 0.71206,
          "calibrated_quality": 0.743748,
          "model_output": "hello"
        },
        {
          "model_id": "premium",
          "actual_quality": 1.0,
          "cost": 0.2,
          "predicted_quality": 0.765461,
          "calibrated_quality": 0.822453,
          "model_output": "hello"
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2408,
          "utilities": {
            "cheap": 1.182503,
            "mid": 0.462385,
            "premium": -0.982516
          },
          "policy_quality": {
            "cheap": 1.182503,
            "mid": 0.758012,
            "premium": 0.421714
          }
        },
        "balanced": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2408,
          "utilities": {
            "cheap": 0.920662,
            "mid": 0.735264,
            "premium": 0.414637
          },
          "policy_quality": {
            "cheap": 0.920662,
            "mid": 0.746345,
            "premium": 0.467268
          }
        },
        "premium": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2408,
          "utilities": {
            "cheap": 0.887145,
            "mid": 0.652668,
            "premium": 0.429822
          },
          "policy_quality": {
            "cheap": 0.887145,
            "mid": 0.663748,
            "premium": 0.482453
          }
        }
      }
    },
    {
      "prompt_id": "e006",
      "prompt": "두 숫자를 더해 반환하는 파이썬 함수 add(a, b)를 작성해줘.",
      "domain": "tech",
      "task_type": "unit_test",
      "benchmark_id": "cheap_code",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 1.0,
          "cost": 0.01,
          "predicted_quality": 0.72509,
          "calibrated_quality": 0.655282,
          "model_output": "def add(a, b): return a + b"
        },
        {
          "model_id": "mid",
          "actual_quality": 1.0,
          "cost": 0.05,
          "predicted_quality": 0.97629,
          "calibrated_quality": 1.007979,
          "model_output": "def add(a, b):\\n    return a + b"
        },
        {
          "model_id": "premium",
          "actual_quality": 1.0,
          "cost": 0.2,
          "predicted_quality": 1.026192,
          "calibrated_quality": 1.083184,
          "model_output": "def add(a, b):\\n    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):\\n        raise TypeError('numbers required')\\n    return a + b"
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.285,
          "utilities": {
            "cheap": 0.912996,
            "mid": 0.822116,
            "premium": -0.378242
          },
          "policy_quality": {
            "cheap": 0.912996,
            "mid": 1.117744,
            "premium": 1.025987
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.05,
          "prompt_complexity": 0.285,
          "utilities": {
            "cheap": 0.683927,
            "mid": 1.091009,
            "premium": 1.016253
          },
          "policy_quality": {
            "cheap": 0.683927,
            "mid": 1.10209,
            "premium": 1.068885
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.285,
          "utilities": {
            "cheap": 0.655282,
            "mid": 0.996899,
            "premium": 1.030552
          },
          "policy_quality": {
            "cheap": 0.655282,
            "mid": 1.007979,
            "premium": 1.083184
          }
        }
      }
    },
    {
      "prompt_id": "e101",
      "prompt": "정수 n을 입력받아 0 이상이면 n번째 피보나치 수를 반복문으로 반환하고, 음수면 ValueError를 발생시키는 파이썬 함수 fibonacci(n)를 작성해줘.",
      "domain": "tech",
      "task_type": "unit_test",
      "benchmark_id": "mid_code",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.4,
          "cost": 0.01,
          "predicted_quality": 0.65273,
          "calibrated_quality": 0.582921,
          "model_output": "def fibonacci(n): return n if n < 2 else fibonacci(n-1) + fibonacci(n-2)"
        },
        {
          "model_id": "mid",
          "actual_quality": 1.0,
          "cost": 0.05,
          "predicted_quality": 0.914046,
          "calibrated_quality": 0.945735,
          "model_output": "def fibonacci(n):\\n    if n < 0:\\n        raise ValueError('n must be non-negative')\\n    a, b = 0, 1\\n    for _ in range(n):\\n        a, b = b, a + b\\n    return a"
        },
        {
          "model_id": "premium",
          "actual_quality": 1.0,
          "cost": 0.2,
          "predicted_quality": 0.967448,
          "calibrated_quality": 1.02444,
          "model_output": "def fibonacci(n):\\n    if n < 0:\\n        raise ValueError('n must be non-negative')\\n    a, b = 0, 1\\n    for _ in range(n):\\n        a, b = b, a + b\\n    return a"
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "mid",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.05,
          "prompt_complexity": 0.421,
          "utilities": {
            "cheap": 0.725058,
            "mid": 0.807463,
            "premium": -0.426108
          },
          "policy_quality": {
            "cheap": 0.725058,
            "mid": 1.10309,
            "premium": 0.978121
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.05,
          "prompt_complexity": 0.421,
          "utilities": {
            "cheap": 0.596609,
            "mid": 1.064118,
            "premium": 0.960228
          },
          "policy_quality": {
            "cheap": 0.596609,
            "mid": 1.075199,
            "premium": 1.01286
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.421,
          "utilities": {
            "cheap": 0.582921,
            "mid": 0.934654,
            "premium": 0.971808
          },
          "policy_quality": {
            "cheap": 0.582921,
            "mid": 0.945735,
            "premium": 1.02444
          }
        }
      }
    },
    {
      "prompt_id": "e102",
      "prompt": "다음 내용을 정확히 2개의 불릿으로 요약해줘. 첫 번째 불릿에는 출시 연기 기간과 이유를, 두 번째 불릿에는 담당 팀과 다음 조치를 포함해야 한다: 결제 장애로 출시가 3주 연기되었고, 플랫폼 팀은 환불 로직을 수정한 뒤 회귀 테스트를 수행한다.",
      "domain": "business",
      "task_type": "constraint_check",
      "benchmark_id": "mid_summary",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.35,
          "cost": 0.01,
          "predicted_quality": 0.594405,
          "calibrated_quality": 0.524596,
          "model_output": "- 출시가 연기되었습니다.\\n- 팀이 테스트합니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 1.0,
          "cost": 0.05,
          "predicted_quality": 0.861982,
          "calibrated_quality": 0.89367,
          "model_output": "- 결제 장애로 출시가 3주 연기되었습니다.\\n- 플랫폼 팀은 환불 로직을 수정한 뒤 회귀 테스트를 수행합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 1.0,
          "cost": 0.2,
          "predicted_quality": 0.911883,
          "calibrated_quality": 0.968875,
          "model_output": "- 결제 장애로 출시가 3주 연기되었습니다.\\n- 플랫폼 팀은 환불 로직 수정 후 회귀 테스트를 수행합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "mid",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.05,
          "prompt_complexity": 0.5875,
          "utilities": {
            "cheap": 0.525185,
            "mid": 0.750652,
            "premium": -0.385379
          },
          "policy_quality": {
            "cheap": 0.525185,
            "mid": 1.046279,
            "premium": 1.01885
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.05,
          "prompt_complexity": 0.5875,
          "utilities": {
            "cheap": 0.519966,
            "mid": 1.006327,
            "premium": 0.911389
          },
          "policy_quality": {
            "cheap": 0.519966,
            "mid": 1.017407,
            "premium": 0.96402
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.5875,
          "utilities": {
            "cheap": 0.524596,
            "mid": 0.88259,
            "premium": 0.916244
          },
          "policy_quality": {
            "cheap": 0.524596,
            "mid": 0.89367,
            "premium": 0.968875
          }
        }
      }
    },
    {
      "prompt_id": "e103",
      "prompt": "다음 CSV 문자열을 JSON 배열로 변환해줘. age는 숫자여야 한다. name,age Kim,30 Lee,25",
      "domain": "data",
      "task_type": "exact_json",
      "benchmark_id": "mid_transform",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.6,
          "cost": 0.01,
          "predicted_quality": 0.566622,
          "calibrated_quality": 0.496813,
          "model_output": "[{\"name\":\"Kim\",\"age\":\"30\"},{\"name\":\"Lee\",\"age\":\"25\"}]"
        },
        {
          "model_id": "mid",
          "actual_quality": 1.0,
          "cost": 0.05,
          "predicted_quality": 0.81035,
          "calibrated_quality": 0.842038,
          "model_output": "[{\"name\":\"Kim\",\"age\":30},{\"name\":\"Lee\",\"age\":25}]"
        },
        {
          "model_id": "premium",
          "actual_quality": 1.0,
          "cost": 0.2,
          "predicted_quality": 0.863751,
          "calibrated_quality": 0.920743,
          "model_output": "[{\"name\":\"Kim\",\"age\":30},{\"name\":\"Lee\",\"age\":25}]"
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.6,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3492,
          "utilities": {
            "cheap": 0.699981,
            "mid": 0.678636,
            "premium": -0.535549
          },
          "policy_quality": {
            "cheap": 0.699981,
            "mid": 0.974263,
            "premium": 0.86868
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3492,
          "utilities": {
            "cheap": 0.5184,
            "mid": 0.941753,
            "premium": 0.855096
          },
          "policy_quality": {
            "cheap": 0.5184,
            "mid": 0.952834,
            "premium": 0.907728
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.3492,
          "utilities": {
            "cheap": 0.496813,
            "mid": 0.830958,
            "premium": 0.868112
          },
          "policy_quality": {
            "cheap": 0.496813,
            "mid": 0.842038,
            "premium": 0.920743
          }
        }
      }
    },
    {
      "prompt_id": "e201",
      "prompt": "멀티테넌트 SaaS 결제 시스템을 설계해줘. 조건: 테넌트별 데이터 격리, Stripe 웹훅 중복 수신 멱등성, 사용량 기반 과금, 월말 청구서 생성, 결제 실패 재시도, 감사 로그, 개인정보와 결제 데이터 분리, 장애 시 재처리 가능성. 구성요소, 데이터 흐름, 핵심 테이블, 실패 시나리오, 보안 통제를 구분해 설명해줘.",
      "domain": "tech",
      "task_type": "rubric_check",
      "benchmark_id": "premium_architecture",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.15,
          "cost": 0.01,
          "predicted_quality": 0.509108,
          "calibrated_quality": 0.439299,
          "model_output": "API 서버와 데이터베이스, 결제 API를 둡니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.55,
          "cost": 0.05,
          "predicted_quality": 0.696555,
          "calibrated_quality": 0.728244,
          "model_output": "구성요소는 API, 결제 서비스, 웹훅 처리기, DB입니다. 데이터 흐름은 사용량 집계 후 청구서를 만들고 결제 실패 시 재시도합니다. 감사 로그를 남깁니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 1.0,
          "cost": 0.2,
          "predicted_quality": 0.746457,
          "calibrated_quality": 0.803449,
          "model_output": "구성요소: tenant-aware API, billing service, usage aggregator, invoice service, Stripe webhook worker, retry scheduler, DLQ, audit logger, reconciliation job. 데이터 흐름: usage event 수집, tenant isolation 검증, 월말 invoice 생성, idempotency key로 webhook deduplication, 결제 실패 retry와 DLQ 재처리. 핵심 테이블: tenants, subscriptions, usage_events, invoices, payments, webhook_events, audit_logs, reconciliation_runs. 실패 시나리오: 중복 웹훅, 결제 실패, worker crash, 재처리 불일치. 보안 통제: PII separation, payment tokenization, tenant scoped access, audit log immutability."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.7009,
          "utilities": {
            "cheap": 0.343548,
            "mid": 0.54329,
            "premium": 0.705014
          },
          "policy_quality": {
            "cheap": 0.343548,
            "mid": 0.838917,
            "premium": 2.109243
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.55,
          "selected_cost": 0.05,
          "prompt_complexity": 0.7009,
          "utilities": {
            "cheap": 0.422202,
            "mid": 0.806898,
            "premium": 0.799233
          },
          "policy_quality": {
            "cheap": 0.422202,
            "mid": 0.817979,
            "premium": 0.851864
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.7009,
          "utilities": {
            "cheap": 0.439299,
            "mid": 0.717164,
            "premium": 0.750817
          },
          "policy_quality": {
            "cheap": 0.439299,
            "mid": 0.728244,
            "premium": 0.803449
          }
        }
      }
    },
    {
      "prompt_id": "e202",
      "prompt": "WebSocket 이벤트 전송 시스템을 설계해줘. 네트워크 단절, 중복 전송, 메시지 순서 뒤바뀜, 브라우저 종료, 서버 재시작이 발생해도 이벤트를 유실하지 않아야 한다. exactly-once가 실제로 가능한지 구분하고 sequence number, ACK, 재전송, 영속 큐, 중복 제거, 순서 복구 방식을 포함해줘.",
      "domain": "tech",
      "task_type": "rubric_check",
      "benchmark_id": "premium_distributed",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.1,
          "cost": 0.01,
          "predicted_quality": 0.508124,
          "calibrated_quality": 0.438315,
          "model_output": "끊기면 다시 연결해서 보내면 됩니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.65,
          "cost": 0.05,
          "predicted_quality": 0.690728,
          "calibrated_quality": 0.722416,
          "model_output": "sequence number와 ACK를 사용하고 재연결 시 미확인 메시지를 다시 보냅니다. 서버는 중복 ID를 저장해 중복을 제거합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 1.0,
          "cost": 0.2,
          "predicted_quality": 0.733997,
          "calibrated_quality": 0.790988,
          "model_output": "네트워크 수준 strict exactly-once는 보장하기 어렵고 at-least-once plus idempotent consumer로 설계해야 합니다. 클라이언트는 persistent outbox에 event_id와 sequence number를 저장하고 reconnect handshake에서 마지막 ACK를 교환합니다. ACK되지 않은 이벤트는 재전송하며 서버는 deduplication key를 durable store에 기록합니다. ordering window로 순서 복구를 수행하고 gap이 있으면 replay를 요청합니다. 브라우저 종료와 서버 재시작은 영속 큐와 checkpoint로 복구합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.6946,
          "utilities": {
            "cheap": 0.347874,
            "mid": 0.539773,
            "premium": 0.623336
          },
          "policy_quality": {
            "cheap": 0.347874,
            "mid": 0.835401,
            "premium": 2.027565
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.65,
          "selected_cost": 0.05,
          "prompt_complexity": 0.6946,
          "utilities": {
            "cheap": 0.421905,
            "mid": 0.802945,
            "premium": 0.783836
          },
          "policy_quality": {
            "cheap": 0.421905,
            "mid": 0.814025,
            "premium": 0.836468
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.6946,
          "utilities": {
            "cheap": 0.438315,
            "mid": 0.711336,
            "premium": 0.738357
          },
          "policy_quality": {
            "cheap": 0.438315,
            "mid": 0.722416,
            "premium": 0.790988
          }
        }
      }
    },
    {
      "prompt_id": "e203",
      "prompt": "TypeScript로 제한 동시성 비동기 작업 실행기 runWithConcurrency를 작성해줘. 입력은 (() => Promise<T>)[]와 concurrency이고, 반환값은 입력 순서대로 정렬되어야 한다. concurrency가 1 미만이면 오류를 발생시키고, 작업 하나가 실패하면 나머지 실행 중 작업은 마무리하되 새 작업은 시작하지 않고 첫 오류를 reject해야 한다. 빈 배열도 처리해야 한다.",
      "domain": "tech",
      "task_type": "unit_test",
      "benchmark_id": "premium_code",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.2,
          "cost": 0.01,
          "predicted_quality": 0.580447,
          "calibrated_quality": 0.510639,
          "model_output": "async function runWithConcurrency(tasks, concurrency) { return Promise.all(tasks.map(t => t())); }"
        },
        {
          "model_id": "mid",
          "actual_quality": 0.65,
          "cost": 0.05,
          "predicted_quality": 0.771818,
          "calibrated_quality": 0.803506,
          "model_output": "async function runWithConcurrency(tasks, concurrency) { const results = []; let i = 0; async function worker(){ while(i < tasks.length){ const idx = i++; results[idx] = await tasks[idx](); }} await Promise.all(Array.from({length: concurrency}, worker)); return results; }"
        },
        {
          "model_id": "premium",
          "actual_quality": 1.0,
          "cost": 0.2,
          "predicted_quality": 0.800611,
          "calibrated_quality": 0.857603,
          "model_output": "async function runWithConcurrency<T>(tasks: Array<() => Promise<T>>, concurrency: number): Promise<T[]> { if (concurrency < 1) throw new Error('invalid concurrency'); if (tasks.length === 0) return []; const results: T[] = new Array(tasks.length); let next = 0; let firstError: unknown; async function worker() { while (firstError === undefined && next < tasks.length) { const index = next++; try { results[index] = await tasks[index](); } catch (err) { if (firstError === undefined) firstError = err; break; } } } const workers = Array.from({ length: Math.min(concurrency, tasks.length) }, worker); await Promise.allSettled(workers); if (firstError !== undefined) throw firstError; return results; }"
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.7448,
          "utilities": {
            "cheap": 0.37759,
            "mid": 0.602317,
            "premium": 1.245345
          },
          "policy_quality": {
            "cheap": 0.37759,
            "mid": 0.897944,
            "premium": 2.649574
          }
        },
        "balanced": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.7448,
          "utilities": {
            "cheap": 0.488715,
            "mid": 0.868997,
            "premium": 0.87401
          },
          "policy_quality": {
            "cheap": 0.488715,
            "mid": 0.880078,
            "premium": 0.926641
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.7448,
          "utilities": {
            "cheap": 0.510639,
            "mid": 0.792426,
            "premium": 0.804971
          },
          "policy_quality": {
            "cheap": 0.510639,
            "mid": 0.803506,
            "premium": 0.857603
          }
        }
      }
    },
    {
      "prompt_id": "e301",
      "prompt": "이 계약이 법적으로 유효한지 판단해줘.",
      "domain": "legal",
      "task_type": "required_clarification",
      "benchmark_id": "abstain_case",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.0,
          "cost": 0.01,
          "predicted_quality": 0.499983,
          "calibrated_quality": 0.430174,
          "model_output": "유효합니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.3,
          "cost": 0.05,
          "predicted_quality": 0.696946,
          "calibrated_quality": 0.728634,
          "model_output": "계약 내용을 봐야 하지만 일반적으로 서명하면 유효합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 1.0,
          "cost": 0.2,
          "predicted_quality": 0.727796,
          "calibrated_quality": 0.784788,
          "model_output": "계약서 내용과 관할 법률, 당사자 정보가 없으므로 법적 유효성을 판단할 수 없습니다. 계약 전문과 국가 또는 지역, 체결 상황을 제공해 주세요."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.3,
          "selected_cost": 0.05,
          "prompt_complexity": 0.1704,
          "utilities": {
            "cheap": -0.164703,
            "mid": 0.522663,
            "premium": -0.305805
          },
          "policy_quality": {
            "cheap": -0.164703,
            "mid": 0.81829,
            "premium": 1.098424
          }
        },
        "balanced": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.1704,
          "utilities": {
            "cheap": -0.478574,
            "mid": 0.80187,
            "premium": 1.095566
          },
          "policy_quality": {
            "cheap": -0.478574,
            "mid": 0.81295,
            "premium": 1.148197
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.1704,
          "utilities": {
            "cheap": -0.519826,
            "mid": 0.737554,
            "premium": 1.112157
          },
          "policy_quality": {
            "cheap": -0.519826,
            "mid": 0.748634,
            "premium": 1.164788
          }
        }
      }
    },
    {
      "prompt_id": "e302",
      "prompt": "다음 코드를 고쳐줘.",
      "domain": "tech",
      "task_type": "required_clarification",
      "benchmark_id": "abstain_case",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.0,
          "cost": 0.01,
          "predicted_quality": 0.483733,
          "calibrated_quality": 0.413925,
          "model_output": "코드를 수정했습니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.7,
          "cost": 0.05,
          "predicted_quality": 0.699168,
          "calibrated_quality": 0.730856,
          "model_output": "어떤 오류인지 알려주시면 수정하겠습니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 1.0,
          "cost": 0.2,
          "predicted_quality": 0.738937,
          "calibrated_quality": 0.795929,
          "model_output": "수정할 코드가 제공되지 않았습니다. 문제가 발생하는 코드, 기대 동작, 실제 오류 메시지를 보내주시면 원인을 분석해 수정안을 제시하겠습니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.7,
          "selected_cost": 0.05,
          "prompt_complexity": 0.0409,
          "utilities": {
            "cheap": -0.070818,
            "mid": 0.479535,
            "premium": -0.305031
          },
          "policy_quality": {
            "cheap": -0.070818,
            "mid": 0.775162,
            "premium": 1.099198
          }
        },
        "balanced": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.0409,
          "utilities": {
            "cheap": -0.480571,
            "mid": 0.770403,
            "premium": 1.104114
          },
          "policy_quality": {
            "cheap": -0.480571,
            "mid": 0.781484,
            "premium": 1.156746
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.0409,
          "utilities": {
            "cheap": -0.536075,
            "mid": 0.739776,
            "premium": 1.123297
          },
          "policy_quality": {
            "cheap": -0.536075,
            "mid": 0.750856,
            "premium": 1.175929
          }
        }
      }
    },
    {
      "prompt_id": "e401",
      "prompt": "HTTP의 기본 포트 번호는?",
      "domain": "tech",
      "task_type": "exact_match",
      "benchmark_id": "contrast_pair",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 1.0,
          "cost": 0.01,
          "predicted_quality": 0.569168,
          "calibrated_quality": 0.49936,
          "model_output": "80"
        },
        {
          "model_id": "mid",
          "actual_quality": 1.0,
          "cost": 0.05,
          "predicted_quality": 0.724603,
          "calibrated_quality": 0.756292,
          "model_output": "80"
        },
        {
          "model_id": "premium",
          "actual_quality": 0.0,
          "cost": 0.2,
          "predicted_quality": 0.724603,
          "calibrated_quality": 0.781595,
          "model_output": "HTTP의 기본 포트 번호는 80입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.1625,
          "utilities": {
            "cheap": 0.861268,
            "mid": 0.527526,
            "premium": -0.689637
          },
          "policy_quality": {
            "cheap": 0.861268,
            "mid": 0.823153,
            "premium": 0.714592
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.05,
          "prompt_complexity": 0.1625,
          "utilities": {
            "cheap": 0.541489,
            "mid": 0.807451,
            "premium": 0.712213
          },
          "policy_quality": {
            "cheap": 0.541489,
            "mid": 0.818532,
            "premium": 0.764845
          }
        },
        "premium": {
          "selected_model_id": "mid",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.05,
          "prompt_complexity": 0.1625,
          "utilities": {
            "cheap": 0.49936,
            "mid": 0.745212,
            "premium": 0.728964
          },
          "policy_quality": {
            "cheap": 0.49936,
            "mid": 0.756292,
            "premium": 0.781595
          }
        }
      }
    },
    {
      "prompt_id": "e402",
      "prompt": "이 계약의 면책 조항이 무효인지 판단해줘.",
      "domain": "legal",
      "task_type": "required_clarification",
      "benchmark_id": "contrast_pair",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.0,
          "cost": 0.01,
          "predicted_quality": 0.529624,
          "calibrated_quality": 0.459815,
          "model_output": "무효입니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.7,
          "cost": 0.05,
          "predicted_quality": 0.746924,
          "calibrated_quality": 0.778613,
          "model_output": "계약 조항을 봐야 정확히 판단할 수 있습니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 1.0,
          "cost": 0.2,
          "predicted_quality": 0.777775,
          "calibrated_quality": 0.834767,
          "model_output": "면책 조항의 문구, 계약 전체 내용, 관할 법률, 당사자 관계가 없으므로 무효 여부를 단정할 수 없습니다. 조항 전문과 적용 국가 또는 지역을 제공해야 합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.7,
          "selected_cost": 0.05,
          "prompt_complexity": 0.1775,
          "utilities": {
            "cheap": -0.141035,
            "mid": 0.5751,
            "premium": -0.255265
          },
          "policy_quality": {
            "cheap": -0.141035,
            "mid": 0.870728,
            "premium": 1.148965
          }
        },
        "balanced": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.1775,
          "utilities": {
            "cheap": -0.449707,
            "mid": 0.853675,
            "premium": 1.145685
          },
          "policy_quality": {
            "cheap": -0.449707,
            "mid": 0.864755,
            "premium": 1.198316
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.1775,
          "utilities": {
            "cheap": -0.490185,
            "mid": 0.787533,
            "premium": 1.162135
          },
          "policy_quality": {
            "cheap": -0.490185,
            "mid": 0.798613,
            "premium": 1.214767
          }
        }
      }
    },
    {
      "prompt_id": "e403",
      "prompt": "다음 문장에서 '사과'라는 단어가 몇 번 나오는지 숫자로 답해줘: 사과 사과 바나나 사과 포도 사과 바나나 사과",
      "domain": "text",
      "task_type": "exact_match",
      "benchmark_id": "contrast_pair",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 1.0,
          "cost": 0.01,
          "predicted_quality": 0.527297,
          "calibrated_quality": 0.457489,
          "model_output": "5"
        },
        {
          "model_id": "mid",
          "actual_quality": 1.0,
          "cost": 0.05,
          "predicted_quality": 0.682732,
          "calibrated_quality": 0.714421,
          "model_output": "5"
        },
        {
          "model_id": "premium",
          "actual_quality": 0.0,
          "cost": 0.2,
          "predicted_quality": 0.682732,
          "calibrated_quality": 0.739724,
          "model_output": "사과는 총 5번 나옵니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3202,
          "utilities": {
            "cheap": 1.145315,
            "mid": 0.460865,
            "premium": -1.058889
          },
          "policy_quality": {
            "cheap": 1.145315,
            "mid": 0.756492,
            "premium": 0.34534
          }
        },
        "balanced": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3202,
          "utilities": {
            "cheap": 0.942266,
            "mid": 0.726594,
            "premium": 0.333497
          },
          "policy_quality": {
            "cheap": 0.942266,
            "mid": 0.737674,
            "premium": 0.386128
          }
        },
        "premium": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3202,
          "utilities": {
            "cheap": 0.917489,
            "mid": 0.623341,
            "premium": 0.347093
          },
          "policy_quality": {
            "cheap": 0.917489,
            "mid": 0.634421,
            "premium": 0.399724
          }
        }
      }
    },
    {
      "prompt_id": "e404",
      "prompt": "이중지불을 막는 결제 멱등성 설계해줘.",
      "domain": "tech",
      "task_type": "rubric_check",
      "benchmark_id": "contrast_pair",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.2,
          "cost": 0.01,
          "predicted_quality": 0.541595,
          "calibrated_quality": 0.471787,
          "model_output": "요청을 한 번만 처리하면 됩니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.75,
          "cost": 0.05,
          "predicted_quality": 0.755974,
          "calibrated_quality": 0.787663,
          "model_output": "idempotency key를 요청마다 받고 payments 테이블에 저장해 중복 요청이면 기존 결과를 반환합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 1.0,
          "cost": 0.2,
          "predicted_quality": 0.805876,
          "calibrated_quality": 0.862868,
          "model_output": "클라이언트가 idempotency key를 생성하고 서버는 tenant_id, operation_type, key에 unique constraint를 둡니다. 최초 요청은 pending row를 만들고 provider charge id와 결과를 저장합니다. 재시도나 webhook 중복 수신은 같은 key와 provider event id로 deduplication하며, 트랜잭션 경계와 reconciliation job으로 pending stuck 상태를 복구합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.2,
          "selected_cost": 0.01,
          "prompt_complexity": 0.1704,
          "utilities": {
            "cheap": 0.826909,
            "mid": 0.561691,
            "premium": -0.607726
          },
          "policy_quality": {
            "cheap": 0.826909,
            "mid": 0.857319,
            "premium": 0.796504
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.75,
          "selected_cost": 0.05,
          "prompt_complexity": 0.1704,
          "utilities": {
            "cheap": 0.513038,
            "mid": 0.840898,
            "premium": 0.793645
          },
          "policy_quality": {
            "cheap": 0.513038,
            "mid": 0.851979,
            "premium": 0.846277
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 1.0,
          "selected_cost": 0.2,
          "prompt_complexity": 0.1704,
          "utilities": {
            "cheap": 0.471787,
            "mid": 0.776583,
            "premium": 0.810236
          },
          "policy_quality": {
            "cheap": 0.471787,
            "mid": 0.787663,
            "premium": 0.862868
          }
        }
      }
    },
    {
      "prompt_id": "p001",
      "prompt": "API가 무엇인지 한 문장으로 설명해줘.",
      "domain": "general",
      "task_type": "qa",
      "benchmark_id": "basic_qa",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.88,
          "cost": 0.01,
          "predicted_quality": 0.674839,
          "calibrated_quality": 0.60503,
          "model_output": "API는 프로그램끼리 서로 요청하고 응답할 수 있게 해주는 약속입니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.91,
          "cost": 0.05,
          "predicted_quality": 0.896495,
          "calibrated_quality": 0.928184,
          "model_output": "API는 한 소프트웨어가 다른 소프트웨어의 기능이나 데이터를 정해진 방식으로 사용할 수 있게 해주는 인터페이스입니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.9,
          "cost": 0.2,
          "predicted_quality": 0.925288,
          "calibrated_quality": 0.98228,
          "model_output": "API는 애플리케이션들이 정해진 규칙에 따라 요청과 응답을 주고받도록 만드는 계약이자 인터페이스입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.88,
          "selected_cost": 0.01,
          "prompt_complexity": 0.1717,
          "utilities": {
            "cheap": 0.959079,
            "mid": 0.702654,
            "premium": -0.488212
          },
          "policy_quality": {
            "cheap": 0.959079,
            "mid": 0.998281,
            "premium": 0.916017
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.91,
          "selected_cost": 0.05,
          "prompt_complexity": 0.1717,
          "utilities": {
            "cheap": 0.646142,
            "mid": 0.981747,
            "premium": 0.913083
          },
          "policy_quality": {
            "cheap": 0.646142,
            "mid": 0.992828,
            "premium": 0.965715
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.9,
          "selected_cost": 0.2,
          "prompt_complexity": 0.1717,
          "utilities": {
            "cheap": 0.60503,
            "mid": 0.917104,
            "premium": 0.929649
          },
          "policy_quality": {
            "cheap": 0.60503,
            "mid": 0.928184,
            "premium": 0.98228
          }
        }
      }
    },
    {
      "prompt_id": "p002",
      "prompt": "n번째 피보나치 수를 반환하는 파이썬 함수를 작성해줘.",
      "domain": "tech",
      "task_type": "code_generation",
      "benchmark_id": "coding_easy",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.62,
          "cost": 0.01,
          "predicted_quality": 0.638693,
          "calibrated_quality": 0.568885,
          "model_output": "def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)"
        },
        {
          "model_id": "mid",
          "actual_quality": 0.92,
          "cost": 0.05,
          "predicted_quality": 0.88485,
          "calibrated_quality": 0.916539,
          "model_output": "def fib(n):\\n    a, b = 0, 1\\n    for _ in range(n):\\n        a, b = b, a + b\\n    return a"
        },
        {
          "model_id": "premium",
          "actual_quality": 0.95,
          "cost": 0.2,
          "predicted_quality": 0.913643,
          "calibrated_quality": 0.970635,
          "model_output": "def fibonacci(n):\\n    if n < 0:\\n        raise ValueError('n은 0 이상이어야 합니다')\\n    a, b = 0, 1\\n    for _ in range(n):\\n        a, b = b, a + b\\n    return a"
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.62,
          "selected_cost": 0.01,
          "prompt_complexity": 0.194,
          "utilities": {
            "cheap": 0.903965,
            "mid": 0.69882,
            "premium": -0.498072
          },
          "policy_quality": {
            "cheap": 0.903965,
            "mid": 0.994447,
            "premium": 0.906157
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.92,
          "selected_cost": 0.05,
          "prompt_complexity": 0.194,
          "utilities": {
            "cheap": 0.607542,
            "mid": 0.975905,
            "premium": 0.901884
          },
          "policy_quality": {
            "cheap": 0.607542,
            "mid": 0.986985,
            "premium": 0.954516
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.95,
          "selected_cost": 0.2,
          "prompt_complexity": 0.194,
          "utilities": {
            "cheap": 0.568885,
            "mid": 0.905458,
            "premium": 0.918004
          },
          "policy_quality": {
            "cheap": 0.568885,
            "mid": 0.916539,
            "premium": 0.970635
          }
        }
      }
    },
    {
      "prompt_id": "p003",
      "prompt": "회의록을 요약해줘: 팀은 결제 버그를 고치고 온보딩을 개선하기 위해 출시를 2주 미루기로 했다.",
      "domain": "business",
      "task_type": "summarization",
      "benchmark_id": "summarization_short",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.91,
          "cost": 0.01,
          "predicted_quality": 0.733685,
          "calibrated_quality": 0.663876,
          "model_output": "출시는 결제 버그 수정과 온보딩 개선 때문에 2주 연기됩니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.93,
          "cost": 0.05,
          "predicted_quality": 0.912719,
          "calibrated_quality": 0.944408,
          "model_output": "팀은 결제 문제를 해결하고 온보딩을 다듬기 위해 출시 일정을 2주 늦추기로 했습니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.92,
          "cost": 0.2,
          "predicted_quality": 0.955988,
          "calibrated_quality": 1.01298,
          "model_output": "출시는 2주 연기되며, 그 기간 동안 팀은 결제 버그를 수정하고 신규 사용자 온보딩 흐름을 개선할 예정입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.91,
          "selected_cost": 0.01,
          "prompt_complexity": 0.289,
          "utilities": {
            "cheap": 0.918255,
            "mid": 0.759919,
            "premium": -0.448132
          },
          "policy_quality": {
            "cheap": 0.918255,
            "mid": 1.055546,
            "premium": 0.956097
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.93,
          "selected_cost": 0.05,
          "prompt_complexity": 0.289,
          "utilities": {
            "cheap": 0.69209,
            "mid": 1.028459,
            "premium": 0.946128
          },
          "policy_quality": {
            "cheap": 0.69209,
            "mid": 1.039539,
            "premium": 0.998759
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.92,
          "selected_cost": 0.2,
          "prompt_complexity": 0.289,
          "utilities": {
            "cheap": 0.663876,
            "mid": 0.933328,
            "premium": 0.960349
          },
          "policy_quality": {
            "cheap": 0.663876,
            "mid": 0.944408,
            "premium": 1.01298
          }
        }
      }
    },
    {
      "prompt_id": "p004",
      "prompt": "작은 분석 대시보드에 SQLite와 PostgreSQL 중 무엇이 더 적합한지 비교해줘.",
      "domain": "tech",
      "task_type": "reasoning",
      "benchmark_id": "comparison_medium",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.58,
          "cost": 0.01,
          "predicted_quality": 0.65572,
          "calibrated_quality": 0.585911,
          "model_output": "SQLite는 간단하고 PostgreSQL은 더 큰 서비스에 좋습니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.86,
          "cost": 0.05,
          "predicted_quality": 0.863759,
          "calibrated_quality": 0.895448,
          "model_output": "SQLite는 배포가 쉽고 단일 사용자나 가벼운 대시보드에 적합합니다. PostgreSQL은 동시 접속, 큰 데이터, 복잡한 쿼리가 필요한 경우 더 좋습니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.92,
          "cost": 0.2,
          "predicted_quality": 0.902001,
          "calibrated_quality": 0.958993,
          "model_output": "대시보드가 로컬 중심이고 데이터 규모가 작으며 동시 사용자가 거의 없다면 SQLite가 단순하고 효율적입니다. 여러 사용자가 접속하거나 권한 관리, 주기적 적재, 복잡한 분석 쿼리가 필요하다면 PostgreSQL이 더 적합합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.86,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2491,
          "utilities": {
            "cheap": -0.075847,
            "mid": 0.717015,
            "premium": -0.125307
          },
          "policy_quality": {
            "cheap": -0.075847,
            "mid": 1.012642,
            "premium": 1.278923
          }
        },
        "balanced": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.92,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2491,
          "utilities": {
            "cheap": -0.331493,
            "mid": 0.98914,
            "premium": 1.271344
          },
          "policy_quality": {
            "cheap": -0.331493,
            "mid": 1.000221,
            "premium": 1.323975
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.92,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2491,
          "utilities": {
            "cheap": -0.364089,
            "mid": 0.904367,
            "premium": 1.286361
          },
          "policy_quality": {
            "cheap": -0.364089,
            "mid": 0.915448,
            "premium": 1.338993
          }
        }
      }
    },
    {
      "prompt_id": "p005",
      "prompt": "단계별로 풀어줘: 기차가 3시간 동안 180km를 이동했다면 평균 속도는 얼마야?",
      "domain": "math",
      "task_type": "math",
      "benchmark_id": "math_easy",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.9,
          "cost": 0.01,
          "predicted_quality": 0.700281,
          "calibrated_quality": 0.630473,
          "model_output": "60km/h입니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.96,
          "cost": 0.05,
          "predicted_quality": 0.91204,
          "calibrated_quality": 0.943728,
          "model_output": "평균 속도는 거리 나누기 시간입니다. 180km를 3시간으로 나누면 60km/h입니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.96,
          "cost": 0.2,
          "predicted_quality": 0.950281,
          "calibrated_quality": 1.007273,
          "model_output": "평균 속도는 이동 거리 / 걸린 시간으로 계산합니다. 180km / 3시간 = 60km/h이므로 평균 속도는 60km/h입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.9,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2848,
          "utilities": {
            "cheap": 0.888415,
            "mid": 0.757772,
            "premium": -0.454174
          },
          "policy_quality": {
            "cheap": 0.888415,
            "mid": 1.053399,
            "premium": 0.950055
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.96,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2848,
          "utilities": {
            "cheap": 0.659148,
            "mid": 1.026689,
            "premium": 0.940337
          },
          "policy_quality": {
            "cheap": 0.659148,
            "mid": 1.037769,
            "premium": 0.992969
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.96,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2848,
          "utilities": {
            "cheap": 0.630473,
            "mid": 0.932648,
            "premium": 0.954641
          },
          "policy_quality": {
            "cheap": 0.630473,
            "mid": 0.943728,
            "premium": 1.007273
          }
        }
      }
    },
    {
      "prompt_id": "p006",
      "prompt": "피트니스 앱에 넣을 짧은 법적 고지 문구를 작성해줘.",
      "domain": "legal",
      "task_type": "generation",
      "benchmark_id": "legal_generation",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.55,
          "cost": 0.01,
          "predicted_quality": 0.56184,
          "calibrated_quality": 0.492032,
          "model_output": "이 앱은 정보 제공용이며 의학적 조언이 아닙니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.79,
          "cost": 0.05,
          "predicted_quality": 0.762007,
          "calibrated_quality": 0.793696,
          "model_output": "이 앱은 일반적인 피트니스 정보를 제공하며 전문적인 의학적 조언을 대체하지 않습니다. 운동을 시작하기 전 전문가와 상담하세요."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.89,
          "cost": 0.2,
          "predicted_quality": 0.801776,
          "calibrated_quality": 0.858768,
          "model_output": "본 앱은 일반적인 건강 및 피트니스 정보를 제공하기 위한 것이며 의학적 진단, 치료 또는 전문적인 조언을 대체하지 않습니다. 운동 프로그램을 시작하거나 변경하기 전에는 자격을 갖춘 의료 전문가와 상담해야 합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.55,
          "selected_cost": 0.01,
          "prompt_complexity": 0.1965,
          "utilities": {
            "cheap": 0.825041,
            "mid": 0.576829,
            "premium": -0.609745
          },
          "policy_quality": {
            "cheap": 0.825041,
            "mid": 0.872456,
            "premium": 0.794485
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.79,
          "selected_cost": 0.05,
          "prompt_complexity": 0.1965,
          "utilities": {
            "cheap": 0.530421,
            "mid": 0.853695,
            "premium": 0.790065
          },
          "policy_quality": {
            "cheap": 0.530421,
            "mid": 0.864775,
            "premium": 0.842697
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.89,
          "selected_cost": 0.2,
          "prompt_complexity": 0.1965,
          "utilities": {
            "cheap": 0.492032,
            "mid": 0.782615,
            "premium": 0.806136
          },
          "policy_quality": {
            "cheap": 0.492032,
            "mid": 0.793696,
            "premium": 0.858768
          }
        }
      }
    },
    {
      "prompt_id": "p007",
      "prompt": "다음 문장을 영어로 번역해줘: 송장은 다음 주 금요일까지 결제해야 합니다.",
      "domain": "general",
      "task_type": "translation",
      "benchmark_id": "translation_easy",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.88,
          "cost": 0.01,
          "predicted_quality": 0.536118,
          "calibrated_quality": 0.46631,
          "model_output": "The invoice must be paid by next Friday."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.94,
          "cost": 0.05,
          "predicted_quality": 0.747688,
          "calibrated_quality": 0.779377,
          "model_output": "The invoice is due next Friday."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.93,
          "cost": 0.2,
          "predicted_quality": 0.79759,
          "calibrated_quality": 0.854582,
          "model_output": "The invoice is due by next Friday."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.88,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2436,
          "utilities": {
            "cheap": 0.759221,
            "mid": 0.579022,
            "premium": -0.610157
          },
          "policy_quality": {
            "cheap": 0.759221,
            "mid": 0.874649,
            "premium": 0.794073
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.94,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2436,
          "utilities": {
            "cheap": 0.49951,
            "mid": 0.851642,
            "premium": 0.786823
          },
          "policy_quality": {
            "cheap": 0.49951,
            "mid": 0.862722,
            "premium": 0.839455
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.93,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2436,
          "utilities": {
            "cheap": 0.46631,
            "mid": 0.768297,
            "premium": 0.80195
          },
          "policy_quality": {
            "cheap": 0.46631,
            "mid": 0.779377,
            "premium": 0.854582
          }
        }
      }
    },
    {
      "prompt_id": "p008",
      "prompt": "멀티테넌트 SaaS 결제 시스템의 상위 수준 아키텍처를 설계해줘.",
      "domain": "tech",
      "task_type": "complex_design",
      "benchmark_id": "architecture_hard",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.35,
          "cost": 0.01,
          "predicted_quality": 0.56299,
          "calibrated_quality": 0.493181,
          "model_output": "백엔드, 데이터베이스, 결제 API를 사용하면 됩니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.72,
          "cost": 0.05,
          "predicted_quality": 0.765076,
          "calibrated_quality": 0.796765,
          "model_output": "API 서버, 테넌트별 데이터 모델, 결제 작업자, 웹훅 처리기, 결제 제공자 연동을 두는 구조가 적합합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.94,
          "cost": 0.2,
          "predicted_quality": 0.811517,
          "calibrated_quality": 0.868509,
          "model_output": "테넌트 인식 인증, API 계층, 구독 서비스, 청구서 서비스, 사용량 집계 파이프라인, 결제 웹훅 처리기, 비동기 결제 작업자, 감사 로그, 권한 분리된 리포팅 저장소로 구성하는 것이 좋습니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.35,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2109,
          "utilities": {
            "cheap": 0.813891,
            "mid": 0.584963,
            "premium": -0.598846
          },
          "policy_quality": {
            "cheap": 0.813891,
            "mid": 0.880591,
            "premium": 0.805383
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.72,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2109,
          "utilities": {
            "cheap": 0.529979,
            "mid": 0.860527,
            "premium": 0.800096
          },
          "policy_quality": {
            "cheap": 0.529979,
            "mid": 0.871607,
            "premium": 0.852727
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.94,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2109,
          "utilities": {
            "cheap": 0.493181,
            "mid": 0.785685,
            "premium": 0.815877
          },
          "policy_quality": {
            "cheap": 0.493181,
            "mid": 0.796765,
            "premium": 0.868509
          }
        }
      }
    },
    {
      "prompt_id": "p009",
      "prompt": "프론트엔드 모노레포(Monorepo) 구성 시 Turborepo와 Lerna 중 무엇이 나은지 비교해줘.",
      "domain": "tech",
      "task_type": "reasoning",
      "benchmark_id": "comparison_medium",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.62,
          "cost": 0.01,
          "predicted_quality": 0.679291,
          "calibrated_quality": 0.609483,
          "model_output": "Turborepo가 더 빠르고 최근에 나온 툴이라 편합니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.87,
          "cost": 0.05,
          "predicted_quality": 0.88733,
          "calibrated_quality": 0.919019,
          "model_output": "Turborepo는 빌드 캐싱 덕분에 빠르고 설정이 쉽습니다. Lerna는 오래된 대규모 프로젝트에 익숙하지만 속도가 느려 최근에는 Turborepo로 마이그레이션하는 추세입니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.94,
          "cost": 0.2,
          "predicted_quality": 0.925572,
          "calibrated_quality": 0.982564,
          "model_output": "신규 프론트엔드 프로젝트라면 원격 빌드 캐싱과 의존성 그래프 최적화가 뛰어난 Turborepo가 유리합니다. 반면 다중 패키지 배포 및 버전 관리 프로세스가 이미 복잡하게 얽혀 있는 기존 대규모 레거시 모노레포라면 Lerna(Nx 통합 버전)가 안정적인 대안이 될 수 있습니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.62,
          "selected_cost": 0.01,
          "prompt_complexity": 0.307,
          "utilities": {
            "cheap": 0.848502,
            "mid": 0.740854,
            "premium": -0.477103
          },
          "policy_quality": {
            "cheap": 0.848502,
            "mid": 1.036482,
            "premium": 0.927127
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.87,
          "selected_cost": 0.05,
          "prompt_complexity": 0.307,
          "utilities": {
            "cheap": 0.635709,
            "mid": 1.007768,
            "premium": 0.916073
          },
          "policy_quality": {
            "cheap": 0.635709,
            "mid": 1.018848,
            "premium": 0.968705
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.94,
          "selected_cost": 0.2,
          "prompt_complexity": 0.307,
          "utilities": {
            "cheap": 0.609483,
            "mid": 0.907939,
            "premium": 0.929932
          },
          "policy_quality": {
            "cheap": 0.609483,
            "mid": 0.919019,
            "premium": 0.982564
          }
        }
      }
    },
    {
      "prompt_id": "p010",
      "prompt": "주어진 배열에서 중복 요소를 제거하는 가장 효율적인 자바스크립트 함수를 작성해줘.",
      "domain": "tech",
      "task_type": "code_generation",
      "benchmark_id": "coding_easy",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.91,
          "cost": 0.01,
          "predicted_quality": 0.754103,
          "calibrated_quality": 0.684294,
          "model_output": "function unique(arr) { return [...new Set(arr)]; }"
        },
        {
          "model_id": "mid",
          "actual_quality": 0.92,
          "cost": 0.05,
          "predicted_quality": 0.927837,
          "calibrated_quality": 0.959526,
          "model_output": "const removeDuplicates = (arr) => Array.from(new Set(arr)); 이 방식이 가독성이 높고 성능도 좋습니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.96,
          "cost": 0.2,
          "predicted_quality": 0.95663,
          "calibrated_quality": 1.013622,
          "model_output": "function removeDuplicates(arr) {\\n  if (!Array.isArray(arr)) throw new TypeError('배열을 입력해야 합니다');\\n  return [...new Set(arr)];\\n}"
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.91,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2403,
          "utilities": {
            "cheap": 0.980014,
            "mid": 0.758014,
            "premium": -0.451381
          },
          "policy_quality": {
            "cheap": 0.980014,
            "mid": 1.053641,
            "premium": 0.952849
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.92,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2403,
          "utilities": {
            "cheap": 0.717858,
            "mid": 1.030931,
            "premium": 0.945797
          },
          "policy_quality": {
            "cheap": 0.717858,
            "mid": 1.042011,
            "premium": 0.998429
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.96,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2403,
          "utilities": {
            "cheap": 0.684294,
            "mid": 0.948445,
            "premium": 0.960991
          },
          "policy_quality": {
            "cheap": 0.684294,
            "mid": 0.959526,
            "premium": 1.013622
          }
        }
      }
    },
    {
      "prompt_id": "p011",
      "prompt": "고객 피드백 요약해줘: 결제 화면 로딩이 너무 느려서 도중에 이탈하는 사용자가 많음. 결제 자체는 성공함.",
      "domain": "business",
      "task_type": "summarization",
      "benchmark_id": "summarization_short",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.89,
          "cost": 0.01,
          "predicted_quality": 0.757544,
          "calibrated_quality": 0.687735,
          "model_output": "결제 성공은 하지만 로딩이 느려서 이탈자가 많습니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.94,
          "cost": 0.05,
          "predicted_quality": 0.94865,
          "calibrated_quality": 0.980339,
          "model_output": "결제 기능은 정상 작동하지만, 화면 로딩 속도가 느려 결제 도중 사용자가 이탈하는 문제가 핵심입니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.93,
          "cost": 0.2,
          "predicted_quality": 0.966982,
          "calibrated_quality": 1.023974,
          "model_output": "결제 트랜잭션 자체의 성공률은 유효하나, 결제 페이지의 심각한 로딩 지연으로 인해 사용자들의 중도 이탈률이 높으므로 UI/UX 성능 개선이 시급합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.89,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3153,
          "utilities": {
            "cheap": 0.919706,
            "mid": 0.805077,
            "premium": -0.435029
          },
          "policy_quality": {
            "cheap": 0.919706,
            "mid": 1.100704,
            "premium": 0.9692
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.94,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3153,
          "utilities": {
            "cheap": 0.713049,
            "mid": 1.071244,
            "premium": 0.957649
          },
          "policy_quality": {
            "cheap": 0.713049,
            "mid": 1.082324,
            "premium": 1.01028
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.93,
          "selected_cost": 0.2,
          "prompt_complexity": 0.3153,
          "utilities": {
            "cheap": 0.687735,
            "mid": 0.969259,
            "premium": 0.971342
          },
          "policy_quality": {
            "cheap": 0.687735,
            "mid": 0.980339,
            "premium": 1.023974
          }
        }
      }
    },
    {
      "prompt_id": "p012",
      "prompt": "스타트업을 위한 고용 계약서에 반드시 포함되어야 할 3가지 조항을 알려줘.",
      "domain": "legal",
      "task_type": "generation",
      "benchmark_id": "legal_generation",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.52,
          "cost": 0.01,
          "predicted_quality": 0.63257,
          "calibrated_quality": 0.562762,
          "model_output": "급여, 근무 시간, 담당 업무입니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.81,
          "cost": 0.05,
          "predicted_quality": 0.830738,
          "calibrated_quality": 0.862427,
          "model_output": "근무 조건(급여 및 시간), 비밀유지 서약(NDA), 그리고 지식재산권(IP) 귀속 조항이 필수적입니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.93,
          "cost": 0.2,
          "predicted_quality": 0.86898,
          "calibrated_quality": 0.925971,
          "model_output": "임금 구성항목 및 소정근무시간을 명시한 근로조건 조항, 기업 자산을 보호하는 비밀유지(Confidentiality) 조항, 그리고 재직 중 개발한 성과물이 회사에 귀속됨을 명시하는 지식재산권 양도(IP Assignment) 조항이 필수입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.52,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2391,
          "utilities": {
            "cheap": 0.859543,
            "mid": 0.660478,
            "premium": -0.539131
          },
          "policy_quality": {
            "cheap": 0.859543,
            "mid": 0.956105,
            "premium": 0.865098
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.81,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2391,
          "utilities": {
            "cheap": 0.596463,
            "mid": 0.933507,
            "premium": 0.858121
          },
          "policy_quality": {
            "cheap": 0.596463,
            "mid": 0.944588,
            "premium": 0.910753
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.93,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2391,
          "utilities": {
            "cheap": 0.562762,
            "mid": 0.851346,
            "premium": 0.87334
          },
          "policy_quality": {
            "cheap": 0.562762,
            "mid": 0.862427,
            "premium": 0.925971
          }
        }
      }
    },
    {
      "prompt_id": "p013",
      "prompt": "3D 지도 렌더링 엔진을 위한 대용량 공간 데이터 파이프라인의 상위 아키텍처를 설계해줘.",
      "domain": "tech",
      "task_type": "complex_design",
      "benchmark_id": "architecture_hard",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.41,
          "cost": 0.01,
          "predicted_quality": 0.660823,
          "calibrated_quality": 0.591015,
          "model_output": "클라우드 저장소에 데이터를 두고 API로 불러와 렌더링합니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.75,
          "cost": 0.05,
          "predicted_quality": 0.880071,
          "calibrated_quality": 0.911759,
          "model_output": "원천 데이터를 인하이드레이션하고, 공간 인덱싱(3D Tiles) 처리를 거친 후, CDN을 통해 클라이언트 프론트엔드 엔진으로 스트리밍하는 구조입니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.95,
          "cost": 0.2,
          "predicted_quality": 0.893704,
          "calibrated_quality": 0.950696,
          "model_output": "원천 공간 데이터(GIS) 적재 계층, 배치를 통한 3D Tiles/정점 데이터 파싱 및 공간 인덱싱 변환 계층, 분산 오브젝트 스토리지 및 전역 CDN 캐싱 계층, 클라이언트 엔진의 시야(Frustum) 기반 비동기 스트리밍 및 Level of Detail(LOD) 관리 엔진으로 구성합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.41,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2655,
          "utilities": {
            "cheap": 0.865343,
            "mid": 0.719056,
            "premium": -0.512294
          },
          "policy_quality": {
            "cheap": 0.865343,
            "mid": 1.014683,
            "premium": 0.891935
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.75,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2655,
          "utilities": {
            "cheap": 0.62181,
            "mid": 0.989708,
            "premium": 0.883374
          },
          "policy_quality": {
            "cheap": 0.62181,
            "mid": 1.000789,
            "premium": 0.936006
          }
        },
        "premium": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.75,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2655,
          "utilities": {
            "cheap": 0.591015,
            "mid": 0.900679,
            "premium": 0.898064
          },
          "policy_quality": {
            "cheap": 0.591015,
            "mid": 0.911759,
            "premium": 0.950696
          }
        }
      }
    },
    {
      "prompt_id": "p014",
      "prompt": "환자가 갑자기 호흡 곤란을 호소할 때 응급 처치 단계를 순서대로 설명해줘.",
      "domain": "medical",
      "task_type": "reasoning",
      "benchmark_id": "emergency_hard",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.31,
          "cost": 0.01,
          "predicted_quality": 0.587484,
          "calibrated_quality": 0.517676,
          "model_output": "119에 전화하고 편하게 눕히세요."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.82,
          "cost": 0.05,
          "predicted_quality": 0.80616,
          "calibrated_quality": 0.837848,
          "model_output": "1. 즉시 119에 신고합니다. 2. 환자의 단추나 벨트를 풀어 편하게 하고 상체를 올린 자세를 취하게 합니다. 3. 환자의 의식을 확인하며 구급대를 기다립니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.96,
          "cost": 0.2,
          "predicted_quality": 0.856061,
          "calibrated_quality": 0.913053,
          "model_output": "1. 즉시 119에 신고하고 정확한 위치를 알립니다. 2. 기도를 압박하는 넥타이나 옷을 느슨하게 합니다. 3. 눕는 것보다 상체를 45도쯤 세운 반좌위(Semi-Fowler) 자세가 호흡에 유리하므로 받쳐줍니다. 4. 환자가 의식을 잃고 호흡이 멈춘다면 즉시 CPR(심폐소생술)을 시행해야 합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.31,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2344,
          "utilities": {
            "cheap": 0.818478,
            "mid": 0.634244,
            "premium": -0.552428
          },
          "policy_quality": {
            "cheap": 0.818478,
            "mid": 0.929871,
            "premium": 0.851801
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.82,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2344,
          "utilities": {
            "cheap": 0.551897,
            "mid": 0.907699,
            "premium": 0.845109
          },
          "policy_quality": {
            "cheap": 0.551897,
            "mid": 0.91878,
            "premium": 0.89774
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.96,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2344,
          "utilities": {
            "cheap": 0.517676,
            "mid": 0.826768,
            "premium": 0.860422
          },
          "policy_quality": {
            "cheap": 0.517676,
            "mid": 0.837848,
            "premium": 0.913053
          }
        }
      }
    },
    {
      "prompt_id": "p015",
      "prompt": "커피숍 개업을 알리는 짧고 감성적인 인스타그램 홍보 문구를 작성해줘.",
      "domain": "creative",
      "task_type": "generation",
      "benchmark_id": "marketing_short",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.6,
          "cost": 0.01,
          "predicted_quality": 0.614208,
          "calibrated_quality": 0.544399,
          "model_output": "카페 오픈했습니다! 맛있는 커피 드시러 오세요."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.88,
          "cost": 0.05,
          "predicted_quality": 0.857936,
          "calibrated_quality": 0.889624,
          "model_output": "따스한 햇살과 은은한 원두 향이 가득한 공간, 드디어 문을 열었습니다. 일상 속 작은 쉼표가 필요할 때 들러주세요."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.91,
          "cost": 0.2,
          "predicted_quality": 0.911337,
          "calibrated_quality": 0.968329,
          "model_output": "매일 아침을 깨우는 로스팅 향, 서두르던 발걸음도 잠시 쉬어가는 곳. 우리의 이야기가 시작되는 작은 공간으로 당신을 초대합니다. 로컬 블렌드와 함께하는 아늑한 주말 되세요."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.6,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2197,
          "utilities": {
            "cheap": 0.857618,
            "mid": 0.680907,
            "premium": -0.498321
          },
          "policy_quality": {
            "cheap": 0.857618,
            "mid": 0.976534,
            "premium": 0.905909
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.88,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2197,
          "utilities": {
            "cheap": 0.580227,
            "mid": 0.955677,
            "premium": 0.900092
          },
          "policy_quality": {
            "cheap": 0.580227,
            "mid": 0.966757,
            "premium": 0.952724
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.91,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2197,
          "utilities": {
            "cheap": 0.544399,
            "mid": 0.878544,
            "premium": 0.915698
          },
          "policy_quality": {
            "cheap": 0.544399,
            "mid": 0.889624,
            "premium": 0.968329
          }
        }
      }
    },
    {
      "prompt_id": "p016",
      "prompt": "데이터베이스 인덱스(Index)의 작동 원리를 한 문장으로 설명해줘.",
      "domain": "tech",
      "task_type": "qa",
      "benchmark_id": "basic_qa",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.85,
          "cost": 0.01,
          "predicted_quality": 0.714775,
          "calibrated_quality": 0.644966,
          "model_output": "인덱스는 책의 색인처럼 데이터를 빨리 찾게 해주는 표입니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.92,
          "cost": 0.05,
          "predicted_quality": 0.941459,
          "calibrated_quality": 0.973147,
          "model_output": "인덱스는 B-Tree 등의 자료구조를 파일에 색인화하여 특정 테이블의 검색 성능을 극대화하는 메커니즘입니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.94,
          "cost": 0.2,
          "predicted_quality": 0.970252,
          "calibrated_quality": 1.027244,
          "model_output": "데이터베이스 인덱스는 지정된 컬럼의 데이터를 키-포인터 쌍의 포인터 파일 및 B-Tree 자료구조로 미리 정렬해두어 풀 스캔을 방지하고 검색 속도를 비약적으로 높이는 기술입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.85,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2621,
          "utilities": {
            "cheap": 0.922198,
            "mid": 0.779248,
            "premium": -0.436019
          },
          "policy_quality": {
            "cheap": 0.922198,
            "mid": 1.074875,
            "premium": 0.96821
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.92,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2621,
          "utilities": {
            "cheap": 0.676137,
            "mid": 1.050208,
            "premium": 0.959854
          },
          "policy_quality": {
            "cheap": 0.676137,
            "mid": 1.061288,
            "premium": 1.012486
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.94,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2621,
          "utilities": {
            "cheap": 0.644966,
            "mid": 0.962067,
            "premium": 0.974612
          },
          "policy_quality": {
            "cheap": 0.644966,
            "mid": 0.973147,
            "premium": 1.027244
          }
        }
      }
    },
    {
      "prompt_id": "p017",
      "prompt": "CSS Flexbox와 Grid 아키텍처의 레이아웃 결정 기준 차이를 비교해줘.",
      "domain": "tech",
      "task_type": "reasoning",
      "benchmark_id": "comparison_medium",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.68,
          "cost": 0.01,
          "predicted_quality": 0.668289,
          "calibrated_quality": 0.598481,
          "model_output": "Flex는 가로세로 한 줄이고 Grid는 바둑판 배열입니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.89,
          "cost": 0.05,
          "predicted_quality": 0.876842,
          "calibrated_quality": 0.908531,
          "model_output": "Flexbox는 행 또는 열 기준의 1차원 레이아웃에 적합하며, Grid는 행과 열을 동시에 제어하는 거시적인 2차원 대형 웹 레이아웃 시스템에 적합합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.95,
          "cost": 0.2,
          "predicted_quality": 0.915084,
          "calibrated_quality": 0.972076,
          "model_output": "Flexbox는 컴포넌트 내부 요소의 유연한 콘텐츠 흐름 및 1차원 정렬을 정의할 때 강력하며, Grid는 열(Column)과 행(Row)을 사전에 정의하여 전체 웹 서비스 페이지의 거시적인 2차원 틀을 다룰 때 아키텍처적 무결성을 제공합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.68,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2336,
          "utilities": {
            "cheap": 0.899933,
            "mid": 0.704659,
            "premium": -0.493467
          },
          "policy_quality": {
            "cheap": 0.899933,
            "mid": 1.000286,
            "premium": 0.910763
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.89,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2336,
          "utilities": {
            "cheap": 0.632787,
            "mid": 0.978183,
            "premium": 0.904116
          },
          "policy_quality": {
            "cheap": 0.632787,
            "mid": 0.989263,
            "premium": 0.956748
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.95,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2336,
          "utilities": {
            "cheap": 0.598481,
            "mid": 0.897451,
            "premium": 0.919444
          },
          "policy_quality": {
            "cheap": 0.598481,
            "mid": 0.908531,
            "premium": 0.972076
          }
        }
      }
    },
    {
      "prompt_id": "p018",
      "prompt": "자바스크립트에서 클로저(Closure)가 발생하는 이유를 한 문장으로 설명해줘.",
      "domain": "tech",
      "task_type": "qa",
      "benchmark_id": "basic_qa",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.89,
          "cost": 0.01,
          "predicted_quality": 0.696919,
          "calibrated_quality": 0.627111,
          "model_output": "함수가 끝난 뒤에도 내부 변수를 계속 기억해서 그렇습니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.95,
          "cost": 0.05,
          "predicted_quality": 0.933365,
          "calibrated_quality": 0.965054,
          "model_output": "자바스크립트 함수가 생성될 당시의 렉시컬 환경(Lexical Environment)을 기억하여 외부 함수 스코프 밖에서 호출되어도 해당 스코프에 접근할 수 있기 때문입니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.96,
          "cost": 0.2,
          "predicted_quality": 0.986767,
          "calibrated_quality": 1.043759,
          "model_output": "외부 함수의 실행 텍스트가 종료되어 콜 스택에서 반환되더라도, 내부 함수가 여전히 상위 스코프의 변수를 참조하고 있다면 렉시컬 환경이 가비지 컬렉션(GC) 대상에서 제외되어 클로저 현상이 발생합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.89,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2711,
          "utilities": {
            "cheap": 0.896643,
            "mid": 0.774325,
            "premium": -0.418779
          },
          "policy_quality": {
            "cheap": 0.896643,
            "mid": 1.069952,
            "premium": 0.98545
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.95,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2711,
          "utilities": {
            "cheap": 0.657286,
            "mid": 1.044469,
            "premium": 0.97655
          },
          "policy_quality": {
            "cheap": 0.657286,
            "mid": 1.05555,
            "premium": 1.029182
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.96,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2711,
          "utilities": {
            "cheap": 0.627111,
            "mid": 0.953973,
            "premium": 0.991127
          },
          "policy_quality": {
            "cheap": 0.627111,
            "mid": 0.965054,
            "premium": 1.043759
          }
        }
      }
    },
    {
      "prompt_id": "p019",
      "prompt": "주어진 문자열을 뒤집는 가장 간결한 자바스크립트 한 줄 코드를 작성해줘.",
      "domain": "tech",
      "task_type": "code_generation",
      "benchmark_id": "coding_easy",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.93,
          "cost": 0.01,
          "predicted_quality": 0.754749,
          "calibrated_quality": 0.68494,
          "model_output": "str.split('').reverse().join('');"
        },
        {
          "model_id": "mid",
          "actual_quality": 0.94,
          "cost": 0.05,
          "predicted_quality": 0.944296,
          "calibrated_quality": 0.975985,
          "model_output": "const reverseStr = str => [...str].reverse().join(''); 이 방식이 이모지 처리 등에서도 안전합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.95,
          "cost": 0.2,
          "predicted_quality": 0.969589,
          "calibrated_quality": 1.026581,
          "model_output": "function reverseString(str) {\\n  if (typeof str !== 'string') return '';\\n  return [...str].reverse().join('');\\n}"
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.93,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2287,
          "utilities": {
            "cheap": 0.990586,
            "mid": 0.770386,
            "premium": -0.439356
          },
          "policy_quality": {
            "cheap": 0.990586,
            "mid": 1.066013,
            "premium": 0.964873
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.94,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2287,
          "utilities": {
            "cheap": 0.719788,
            "mid": 1.044354,
            "premium": 0.958523
          },
          "policy_quality": {
            "cheap": 0.719788,
            "mid": 1.055434,
            "premium": 1.011154
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.95,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2287,
          "utilities": {
            "cheap": 0.68494,
            "mid": 0.964904,
            "premium": 0.97395
          },
          "policy_quality": {
            "cheap": 0.68494,
            "mid": 0.975985,
            "premium": 1.026581
          }
        }
      }
    },
    {
      "prompt_id": "p020",
      "prompt": "배달 앱 알림 문구 요약해줘: 주문하신 치킨이 조리 완료되어 라이더에게 전달되었습니다. 20분 내 도착 예정.",
      "domain": "business",
      "task_type": "summarization",
      "benchmark_id": "summarization_short",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.9,
          "cost": 0.01,
          "predicted_quality": 0.747236,
          "calibrated_quality": 0.677428,
          "model_output": "치킨 조리 끝, 20분 안에 배달 완료됩니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.93,
          "cost": 0.05,
          "predicted_quality": 0.945738,
          "calibrated_quality": 0.977427,
          "model_output": "주문 상품의 조리가 완료되어 라이더가 배달을 시작했으며, 20분 이내에 수령 가능합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.92,
          "cost": 0.2,
          "predicted_quality": 0.98048,
          "calibrated_quality": 1.037471,
          "model_output": "주문 건의 조리 완료 후 배송 파트너 픽업이 완료되었으며, 고객님 계신 곳까지 향후 20분 이내 도착 예정으로 요약됩니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.9,
          "selected_cost": 0.01,
          "prompt_complexity": 0.332,
          "utilities": {
            "cheap": 0.895232,
            "mid": 0.807998,
            "premium": -0.420198
          },
          "policy_quality": {
            "cheap": 0.895232,
            "mid": 1.103625,
            "premium": 0.984031
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.93,
          "selected_cost": 0.05,
          "prompt_complexity": 0.332,
          "utilities": {
            "cheap": 0.700908,
            "mid": 1.072665,
            "premium": 0.97148
          },
          "policy_quality": {
            "cheap": 0.700908,
            "mid": 1.083746,
            "premium": 1.024111
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.92,
          "selected_cost": 0.2,
          "prompt_complexity": 0.332,
          "utilities": {
            "cheap": 0.677428,
            "mid": 0.966346,
            "premium": 0.98484
          },
          "policy_quality": {
            "cheap": 0.677428,
            "mid": 0.977427,
            "premium": 1.037471
          }
        }
      }
    },
    {
      "prompt_id": "p021",
      "prompt": "스타트업 제품 출시 전 이용약관에 명시해야 할 핵심 고지 사항 2가지를 알려줘.",
      "domain": "legal",
      "task_type": "generation",
      "benchmark_id": "legal_generation",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.55,
          "cost": 0.01,
          "predicted_quality": 0.635602,
          "calibrated_quality": 0.565793,
          "model_output": "환불 규정 및 서비스 이용 제한 조건입니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.82,
          "cost": 0.05,
          "predicted_quality": 0.834233,
          "calibrated_quality": 0.865921,
          "model_output": "서비스 이용에 따른 회사와 이용자 간의 귀속 권리 책임 및 면책 조항, 그리고 결제 취소나 환불에 대한 명확한 환불 정책입니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.94,
          "cost": 0.2,
          "predicted_quality": 0.874002,
          "calibrated_quality": 0.930993,
          "model_output": "부정사용자나 시스템 장애 발생 시 회사의 법적 분쟁을 방어하는 서비스 면책(Limitation of Liability) 조항과 소비자분쟁해결기준에 부합하도록 적법하게 짜인 계약해지 및 환불 규정이 가장 핵심적입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.55,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2531,
          "utilities": {
            "cheap": 0.85068,
            "mid": 0.66887,
            "premium": -0.53299
          },
          "policy_quality": {
            "cheap": 0.85068,
            "mid": 0.964497,
            "premium": 0.871239
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.82,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2531,
          "utilities": {
            "cheap": 0.597955,
            "mid": 0.94064,
            "premium": 0.863423
          },
          "policy_quality": {
            "cheap": 0.597955,
            "mid": 0.951721,
            "premium": 0.916055
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.94,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2531,
          "utilities": {
            "cheap": 0.565793,
            "mid": 0.854841,
            "premium": 0.878362
          },
          "policy_quality": {
            "cheap": 0.565793,
            "mid": 0.865921,
            "premium": 0.930993
          }
        }
      }
    },
    {
      "prompt_id": "p022",
      "prompt": "CesiumJS와 OpenLayers 라이브러리의 3D 공간 데이터 표현 능력 차이를 비교해줘.",
      "domain": "tech",
      "task_type": "reasoning",
      "benchmark_id": "comparison_medium",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.64,
          "cost": 0.01,
          "predicted_quality": 0.674413,
          "calibrated_quality": 0.604605,
          "model_output": "Cesium은 대규모 3D에 좋고, OpenLayers는 2D 평면 지도 중심입니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.88,
          "cost": 0.05,
          "predicted_quality": 0.887994,
          "calibrated_quality": 0.919683,
          "model_output": "CesiumJS는 지구 스케일의 가상 구체 렌더링 및 3D Tiles 스트리밍에 최적화되어 있고, OpenLayers는 강력한 2D/2.5D 데이터 관리 레이어를 기반으로 가벼운 뷰를 구성할 때 유리합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.95,
          "cost": 0.2,
          "predicted_quality": 0.926236,
          "calibrated_quality": 0.983228,
          "model_output": "CesiumJS는 WebGL 기반의 글로벌 디지털 트윈을 위해 고정밀 지형(Terrain) 데이터 및 대용량 3D Tiles 개체를 계층적(LOD)으로 파이프라이닝하는 데 강점이 있으며, OpenLayers는 OGC 표준 포맷을 지원하는 전통적인 2D 벡터 레이어 제어와 평면 웹 맵 구현에 효율적인 아키텍처적 차이를 가집니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.64,
          "selected_cost": 0.01,
          "prompt_complexity": 0.266,
          "utilities": {
            "cheap": 0.87848,
            "mid": 0.727166,
            "premium": -0.479719
          },
          "policy_quality": {
            "cheap": 0.87848,
            "mid": 1.022793,
            "premium": 0.92451
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.88,
          "selected_cost": 0.05,
          "prompt_complexity": 0.266,
          "utilities": {
            "cheap": 0.635341,
            "mid": 0.99777,
            "premium": 0.915917
          },
          "policy_quality": {
            "cheap": 0.635341,
            "mid": 1.00885,
            "premium": 0.968548
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.95,
          "selected_cost": 0.2,
          "prompt_complexity": 0.266,
          "utilities": {
            "cheap": 0.604605,
            "mid": 0.908602,
            "premium": 0.930596
          },
          "policy_quality": {
            "cheap": 0.604605,
            "mid": 0.919683,
            "premium": 0.983228
          }
        }
      }
    },
    {
      "prompt_id": "p023",
      "prompt": "실시간 데이터 시각화 웹 대시보드를 위한 고성능 클라이언트 아키텍처를 설계해줘.",
      "domain": "tech",
      "task_type": "complex_design",
      "benchmark_id": "architecture_hard",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.38,
          "cost": 0.01,
          "predicted_quality": 0.623077,
          "calibrated_quality": 0.553269,
          "model_output": "웹소켓으로 데이터를 받아서 리액트 상태로 변경하고 화면을 갱신합니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.76,
          "cost": 0.05,
          "predicted_quality": 0.842998,
          "calibrated_quality": 0.874687,
          "model_output": "Websocket 통신 전용 비동기 스레드(Worker)를 분리하고, 전역 상태 스토어에서 버퍼링을 처리하여 차트 렌더링 프레임을 최적화하는 구조가 적합합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.96,
          "cost": 0.2,
          "predicted_quality": 0.88124,
          "calibrated_quality": 0.938232,
          "model_output": "네트워크 메인 스레드를 방해하지 않는 Web Worker 기반의 바이너리 소켓 스트림 관리 파이프라인, 프론트엔드 메인 렌더러의 가비지 컬렉터 부하를 최소화하는 버퍼/링 버퍼 큐, React의 불필요한 리렌더링을 격리하는 Zustand 상태 구조, 가상 DOM을 우회하고 Canvas/WebGL로 다이렉트 푸시하는 시각화 컴포넌트 레이어로 구성합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.38,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2367,
          "utilities": {
            "cheap": 0.852033,
            "mid": 0.671921,
            "premium": -0.527058
          },
          "policy_quality": {
            "cheap": 0.852033,
            "mid": 0.967549,
            "premium": 0.877171
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.76,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2367,
          "utilities": {
            "cheap": 0.587227,
            "mid": 0.945161,
            "premium": 0.870335
          },
          "policy_quality": {
            "cheap": 0.587227,
            "mid": 0.956241,
            "premium": 0.922967
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.96,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2367,
          "utilities": {
            "cheap": 0.553269,
            "mid": 0.863606,
            "premium": 0.8856
          },
          "policy_quality": {
            "cheap": 0.553269,
            "mid": 0.874687,
            "premium": 0.938232
          }
        }
      }
    },
    {
      "prompt_id": "p024",
      "prompt": "심정지 환자가 발생했을 때 목격자가 취해야 할 행동 단계를 순서대로 설명해줘.",
      "domain": "medical",
      "task_type": "reasoning",
      "benchmark_id": "emergency_hard",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.35,
          "cost": 0.01,
          "predicted_quality": 0.604076,
          "calibrated_quality": 0.534267,
          "model_output": "의식을 확인하고 즉시 가슴을 압박하세요."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.85,
          "cost": 0.05,
          "predicted_quality": 0.822751,
          "calibrated_quality": 0.85444,
          "model_output": "1. 환자의 어깨를 두드리며 반응을 봅니다. 2. 주위 사람에게 119 신고와 AED 지참을 요청합니다. 3. 구급대가 올 때까지 분당 100~120회 속도로 가슴 압박 소생술을 실시합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.97,
          "cost": 0.2,
          "predicted_quality": 0.872653,
          "calibrated_quality": 0.929645,
          "model_output": "1. 환자의 의식 및 호흡 유무를 정확하게 판별합니다. 2. 특정인을 지목하여 119 신고 및 자동심장충격기(AED) 수거를 지시합니다. 3. 환자의 복장 해체 후 복장뼈 하단 2분의 1 지점을 5~6cm 깊이로 강하고 빠르게 가슴 압박합니다. 4. AED가 도착하면 기기 음성 안내에 따라 패드 부착 및 제동 사이클을 반복 적용합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.35,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2384,
          "utilities": {
            "cheap": 0.831601,
            "mid": 0.652264,
            "premium": -0.53551
          },
          "policy_quality": {
            "cheap": 0.831601,
            "mid": 0.947891,
            "premium": 0.86872
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.85,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2384,
          "utilities": {
            "cheap": 0.56804,
            "mid": 0.925352,
            "premium": 0.861782
          },
          "policy_quality": {
            "cheap": 0.56804,
            "mid": 0.936432,
            "premium": 0.914414
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.97,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2384,
          "utilities": {
            "cheap": 0.534267,
            "mid": 0.84336,
            "premium": 0.877013
          },
          "policy_quality": {
            "cheap": 0.534267,
            "mid": 0.85444,
            "premium": 0.929645
          }
        }
      }
    },
    {
      "prompt_id": "p025",
      "prompt": "로컬 베이커리의 건강한 쌀 식빵 출시를 알리는 감성적인 카피라이팅을 작성해줘.",
      "domain": "creative",
      "task_type": "generation",
      "benchmark_id": "marketing_short",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.58,
          "cost": 0.01,
          "predicted_quality": 0.649931,
          "calibrated_quality": 0.580122,
          "model_output": "밀가루 없는 건강한 쌀 식빵 구워냈습니다. 사러 오세요."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.86,
          "cost": 0.05,
          "predicted_quality": 0.861549,
          "calibrated_quality": 0.893238,
          "model_output": "속 편한 아침을 위해 밀가루 대신 국내산 쌀로 꾹꾹 눌러 담았습니다. 갓 구워낸 쫄깃하고 담백한 식감을 만나보세요."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.92,
          "cost": 0.2,
          "predicted_quality": 0.914951,
          "calibrated_quality": 0.971943,
          "model_output": "부스스 눈을 뜬 아침, 나를 위해 준비하는 가장 무해한 식사. 밀가루를 비우고 정직한 우리 쌀의 포근함만 채워 넣은 담백한 속 편한 쌀 식빵이 노릇하게 구워졌습니다. 오늘부터 매일 아침 테이블에서 기다릴게요."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.58,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2353,
          "utilities": {
            "cheap": 0.88012,
            "mid": 0.689964,
            "premium": -0.493463
          },
          "policy_quality": {
            "cheap": 0.88012,
            "mid": 0.985591,
            "premium": 0.910766
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.86,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2353,
          "utilities": {
            "cheap": 0.614239,
            "mid": 0.963334,
            "premium": 0.904017
          },
          "policy_quality": {
            "cheap": 0.614239,
            "mid": 0.974415,
            "premium": 0.956649
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.92,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2353,
          "utilities": {
            "cheap": 0.580122,
            "mid": 0.882157,
            "premium": 0.919311
          },
          "policy_quality": {
            "cheap": 0.580122,
            "mid": 0.893238,
            "premium": 0.971943
          }
        }
      }
    },
    {
      "prompt_id": "p026",
      "prompt": "화학 반응 속도론에서 활성화 에너지($E_a$)의 개념을 한 문장으로 정의해줘.",
      "domain": "math",
      "task_type": "qa",
      "benchmark_id": "basic_qa",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.86,
          "cost": 0.01,
          "predicted_quality": 0.733017,
          "calibrated_quality": 0.663209,
          "model_output": "화학 반응이 일어나기 위해 필요한 최소한의 에너지 고개입니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.94,
          "cost": 0.05,
          "predicted_quality": 0.951851,
          "calibrated_quality": 0.983539,
          "model_output": "활성화 에너지는 반응물들이 화학 반응을 일으켜 생성물로 변환되기 위해 반드시 넘어야 하는 최소한의 문턱 에너지 장벽입니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.95,
          "cost": 0.2,
          "predicted_quality": 0.977144,
          "calibrated_quality": 1.034136,
          "model_output": "활성화 에너지($E_a$)는 출발 물질이 전이 상태(Transition State)의 활성화 착물을 형성하여 자발적 내지 비자발적 화학 반응으로 진행되기 위해 공급되어야 하는 통계역학적 최저 에너지 장벽을 의미합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.86,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3253,
          "utilities": {
            "cheap": 0.886667,
            "mid": 0.811782,
            "premium": -0.424066
          },
          "policy_quality": {
            "cheap": 0.886667,
            "mid": 1.107409,
            "premium": 0.980163
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.94,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3253,
          "utilities": {
            "cheap": 0.687421,
            "mid": 1.077048,
            "premium": 0.968011
          },
          "policy_quality": {
            "cheap": 0.687421,
            "mid": 1.088128,
            "premium": 1.020642
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.95,
          "selected_cost": 0.2,
          "prompt_complexity": 0.3253,
          "utilities": {
            "cheap": 0.663209,
            "mid": 0.972459,
            "premium": 0.981504
          },
          "policy_quality": {
            "cheap": 0.663209,
            "mid": 0.983539,
            "premium": 1.034136
          }
        }
      }
    },
    {
      "prompt_id": "p027",
      "prompt": "피타고라스 정리의 수학적 정의를 한 문장으로 기술해줘.",
      "domain": "math",
      "task_type": "qa",
      "benchmark_id": "basic_qa",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.92,
          "cost": 0.01,
          "predicted_quality": 0.688199,
          "calibrated_quality": 0.618391,
          "model_output": "직각삼각형에서 밑변 제곱 더하기 높이 제곱은 빗변 제곱과 같습니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.95,
          "cost": 0.05,
          "predicted_quality": 0.925358,
          "calibrated_quality": 0.957047,
          "model_output": "직각삼각형에서 두 직각변의 길이를 각각 제곱하여 더한 값은 빗변의 길이를 제곱한 값과 항상 일치한다는 정리입니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.96,
          "cost": 0.2,
          "predicted_quality": 0.97876,
          "calibrated_quality": 1.035752,
          "model_output": "직각삼각형의 직각을 낀 두 변의 길이를 $a, b$라 하고 대변인 빗변의 길이를 $c$라 할 때, Euclidean 평면 구조 하에서 $a^2 + b^2 = c^2$이 성립한다는 기하학적 정리입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.92,
          "selected_cost": 0.01,
          "prompt_complexity": 0.194,
          "utilities": {
            "cheap": 0.953471,
            "mid": 0.739328,
            "premium": -0.432955
          },
          "policy_quality": {
            "cheap": 0.953471,
            "mid": 1.034955,
            "premium": 0.971274
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.95,
          "selected_cost": 0.05,
          "prompt_complexity": 0.194,
          "utilities": {
            "cheap": 0.657048,
            "mid": 1.016413,
            "premium": 0.967001
          },
          "policy_quality": {
            "cheap": 0.657048,
            "mid": 1.027493,
            "premium": 1.019632
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.96,
          "selected_cost": 0.2,
          "prompt_complexity": 0.194,
          "utilities": {
            "cheap": 0.618391,
            "mid": 0.945967,
            "premium": 0.98312
          },
          "policy_quality": {
            "cheap": 0.618391,
            "mid": 0.957047,
            "premium": 1.035752
          }
        }
      }
    },
    {
      "prompt_id": "p028",
      "prompt": "거스름돈 반환 알고리즘용 탐욕 알고리즘(Greedy)의 한계점을 예시와 함께 설명해줘.",
      "domain": "math",
      "task_type": "reasoning",
      "benchmark_id": "comparison_medium",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.62,
          "cost": 0.01,
          "predicted_quality": 0.632076,
          "calibrated_quality": 0.562267,
          "model_output": "가장 큰 동전부터 주면 가끔 동전 개수가 더 많아집니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.9,
          "cost": 0.05,
          "predicted_quality": 0.852549,
          "calibrated_quality": 0.884238,
          "model_output": "탐욕 알고리즘은 매순간 가장 단위가 큰 동전을 고르기 때문에, 동전 단위가 배수 관계가 아닐 때(예: 10원, 40원, 50원 화폐 구조에서 80원 반환 시) 최적해를 구하지 못합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.96,
          "cost": 0.2,
          "predicted_quality": 0.905951,
          "calibrated_quality": 0.962943,
          "model_output": "그리디 기법은 국소적인 최적 선택이 전역적 최적해(Global Optimum)를 보장한다는 전제로 동작하므로, 동전 액면가가 서로의 배수 형태(권종 설계)를 이루지 않는 배타적 집합일 경우, DP(동적 계획법)와 달리 탐욕적 선택 조건이 무너져 최소 동전 개수 산출에 실패하게 됩니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.62,
          "selected_cost": 0.01,
          "prompt_complexity": 0.2869,
          "utilities": {
            "cheap": 0.818382,
            "mid": 0.699034,
            "premium": -0.498332
          },
          "policy_quality": {
            "cheap": 0.818382,
            "mid": 0.994661,
            "premium": 0.905897
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.9,
          "selected_cost": 0.05,
          "prompt_complexity": 0.2869,
          "utilities": {
            "cheap": 0.590706,
            "mid": 0.967758,
            "premium": 0.89605
          },
          "policy_quality": {
            "cheap": 0.590706,
            "mid": 0.978838,
            "premium": 0.948681
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.96,
          "selected_cost": 0.2,
          "prompt_complexity": 0.2869,
          "utilities": {
            "cheap": 0.562267,
            "mid": 0.873158,
            "premium": 0.910311
          },
          "policy_quality": {
            "cheap": 0.562267,
            "mid": 0.884238,
            "premium": 0.962943
          }
        }
      }
    },
    {
      "prompt_id": "p029",
      "prompt": "대용량 점구름(Point Cloud) 데이터를 웹 브라우저에 최적화하여 렌더링하기 위한 포맷 체계를 비교해줘.",
      "domain": "tech",
      "task_type": "reasoning",
      "benchmark_id": "comparison_medium",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.61,
          "cost": 0.01,
          "predicted_quality": 0.671859,
          "calibrated_quality": 0.60205,
          "model_output": "Potree나 3D Tiles 포맷을 쓰면 웹 환경에서 점 데이터를 빠르게 볼 수 있습니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.89,
          "cost": 0.05,
          "predicted_quality": 0.888499,
          "calibrated_quality": 0.920188,
          "model_output": "옥트리(Octree) 기반의 Potree 형식은 정밀한 점구름 뷰에 강하며, OGC 표준인 3D Tiles(PNTS)는 타일링 스트리밍을 통해 다른 3D 빌딩 개체들과 함께 GIS 레이어에 올리기 유리합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.96,
          "cost": 0.2,
          "predicted_quality": 0.902132,
          "calibrated_quality": 0.959124,
          "model_output": "정밀 포인트 인덱싱 중심인 Potree의 Octree 구조는 로컬 피처 밀도가 높은 스캔 분석에 적합한 반면, OGC 3D Tiles의 pnts 레이어는 계층적 LoD 아키텍처를 따라 대규모 거시 공간 웹 스트리밍 및 타 공간 데이터(BIM, Terrain)와의 파이프라인 통합 측면에서 압도적인 호환성을 가집니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.61,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3263,
          "utilities": {
            "cheap": 0.824656,
            "mid": 0.748782,
            "premium": -0.498998
          },
          "policy_quality": {
            "cheap": 0.824656,
            "mid": 1.044409,
            "premium": 0.905232
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.89,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3263,
          "utilities": {
            "cheap": 0.626152,
            "mid": 1.013957,
            "premium": 0.893019
          },
          "policy_quality": {
            "cheap": 0.626152,
            "mid": 1.025038,
            "premium": 0.945651
          }
        },
        "premium": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.89,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3263,
          "utilities": {
            "cheap": 0.60205,
            "mid": 0.909108,
            "premium": 0.906493
          },
          "policy_quality": {
            "cheap": 0.60205,
            "mid": 0.920188,
            "premium": 0.959124
          }
        }
      }
    },
    {
      "prompt_id": "p030",
      "prompt": "웹 브라우저 환경에서 투명도가 있는 3D 오브젝트들을 올바르게 정렬하여 렌더링(OIT)하는 알고리즘을 비교해줘.",
      "domain": "tech",
      "task_type": "reasoning",
      "benchmark_id": "comparison_medium",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.45,
          "cost": 0.01,
          "predicted_quality": 0.631524,
          "calibrated_quality": 0.561716,
          "model_output": "앞뒤 순서대로 깊이 정렬을 해서 렌더링하거나 알파 블렌딩을 하면 됩니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.84,
          "cost": 0.05,
          "predicted_quality": 0.847908,
          "calibrated_quality": 0.879597,
          "model_output": "매 프레임 카메라 거리에 따라 CPU에서 정렬하는 뎁스 정렬(Depth Sorting) 방식과, 가비지 컬렉터 부하를 피하기 위해 셰이더 레벨에서 처리하는 순서 무관 투명도(OIT) 알고리즘 방식이 있으며 후자가 고성능 대형 씬에 적합합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.95,
          "cost": 0.2,
          "predicted_quality": 0.851408,
          "calibrated_quality": 0.9084,
          "model_output": "매 프레임 프리미티브를 CPU에서 정렬하는 전통적인 방식은 동적 데이터에서 드로우콜 병목을 유발하므로, WebGL 환경에서는 Fragment Shader 레벨에서 가중치 평균을 내는 WBOIT(Weighted Blended OIT)나 복잡한 링크드 리스트를 구성하는 페어와이즈 스크린 공간 가상 버퍼 트리를 구성하는 것이 대형 디지털 트윈 엔진 설계의 핵심입니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.45,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3339,
          "utilities": {
            "cheap": 0.777901,
            "mid": 0.710834,
            "premium": -0.549117
          },
          "policy_quality": {
            "cheap": 0.777901,
            "mid": 1.006462,
            "premium": 0.855112
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.84,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3339,
          "utilities": {
            "cheap": 0.584987,
            "mid": 0.97533,
            "premium": 0.842447
          },
          "policy_quality": {
            "cheap": 0.584987,
            "mid": 0.986411,
            "premium": 0.895078
          }
        },
        "premium": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.84,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3339,
          "utilities": {
            "cheap": 0.561716,
            "mid": 0.868517,
            "premium": 0.855769
          },
          "policy_quality": {
            "cheap": 0.561716,
            "mid": 0.879597,
            "premium": 0.9084
          }
        }
      }
    },
    {
      "prompt_id": "p031",
      "prompt": "CesiumJS 엔지니어링 관점에서 3D Tiles의 지형 고도(Terrain) 고정 방식을 한 문장으로 설명해줘.",
      "domain": "tech",
      "task_type": "qa",
      "benchmark_id": "basic_qa",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.81,
          "cost": 0.01,
          "predicted_quality": 0.681413,
          "calibrated_quality": 0.611605,
          "model_output": "지형 높이에 3D 모델을 붙이려면 height 조절이나 clamp To Ground 옵션을 씁니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.91,
          "cost": 0.05,
          "predicted_quality": 0.911668,
          "calibrated_quality": 0.943357,
          "model_output": "CesiumJS에서는 타일셋 데이터가 가상 지구 고도에 묻히지 않도록 `HeightReference.CLAMP_TO_GROUND` 속성을 사용해 타일셋을 타겟 지형 메시에 동적으로 정렬합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.96,
          "cost": 0.2,
          "predicted_quality": 0.930329,
          "calibrated_quality": 0.987321,
          "model_output": "Cesium 공간 연산 엔진 내에서 3D Tileset 레이어의 물리 고도는 Quantized-Mesh 지형 파일의 레이캐스팅 고도 벡터 정보와 동기화되며, `sampleTerrainMostDetailed` 비동기 API 또는 엔티티의 래핑 클램핑 프로퍼티를 통해 정밀 유효 고도가 정렬됩니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.81,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3356,
          "utilities": {
            "cheap": 0.826315,
            "mid": 0.775202,
            "premium": -0.470058
          },
          "policy_quality": {
            "cheap": 0.826315,
            "mid": 1.070829,
            "premium": 0.934171
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.91,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3356,
          "utilities": {
            "cheap": 0.634685,
            "mid": 1.039542,
            "premium": 0.921402
          },
          "policy_quality": {
            "cheap": 0.634685,
            "mid": 1.050622,
            "premium": 0.974033
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.96,
          "selected_cost": 0.2,
          "prompt_complexity": 0.3356,
          "utilities": {
            "cheap": 0.611605,
            "mid": 0.932277,
            "premium": 0.934689
          },
          "policy_quality": {
            "cheap": 0.611605,
            "mid": 0.943357,
            "premium": 0.987321
          }
        }
      }
    },
    {
      "prompt_id": "p032",
      "prompt": "웹소켓(WebSocket) 연결이 빈번히 끊기는 환경에서 유실 없는 데이터 재전송 보장 메커니즘을 설계해줘.",
      "domain": "tech",
      "task_type": "complex_design",
      "benchmark_id": "architecture_hard",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.39,
          "cost": 0.01,
          "predicted_quality": 0.616915,
          "calibrated_quality": 0.547107,
          "model_output": "끊기면 다시 커넥션을 맺고 메시지를 보내는 코드를 만듭니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.78,
          "cost": 0.05,
          "predicted_quality": 0.814525,
          "calibrated_quality": 0.846213,
          "model_output": "클라이언트 단에 지수 백오프(Exponential Backoff) 기반 재연결 로직을 구현하고, 인메모리 큐를 두어 미전송된 메시지를 담았다가 웹소켓이 재오픈되는 시점에 한 번에 발행(Flush)합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.95,
          "cost": 0.2,
          "predicted_quality": 0.839133,
          "calibrated_quality": 0.896125,
          "model_output": "시퀀스 넘버(Sequence Number) 기반의 클라이언트-서버 간 ACK 응답 프로토콜을 구현하고, 재연결 세션 시 인메모리 링버퍼(Ring Buffer)에서 미확인된 메시지를 추적하여 지수 백오프 전략에 따라 재전송하며, 클라이언트 로컬 스토리지에 오프라인 이벤트 로그 스토어를 두어 네트워크 단절 장기화 시 브라우저 크래시와 데이터 유실을 방어하는 복합 아키텍처를 설계합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.39,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3242,
          "utilities": {
            "cheap": 0.771548,
            "mid": 0.674051,
            "premium": -0.562169
          },
          "policy_quality": {
            "cheap": 0.771548,
            "mid": 0.969679,
            "premium": 0.84206
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.78,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3242,
          "utilities": {
            "cheap": 0.571446,
            "mid": 0.939421,
            "premium": 0.829977
          },
          "policy_quality": {
            "cheap": 0.571446,
            "mid": 0.950502,
            "premium": 0.882609
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.95,
          "selected_cost": 0.2,
          "prompt_complexity": 0.3242,
          "utilities": {
            "cheap": 0.547107,
            "mid": 0.835133,
            "premium": 0.843494
          },
          "policy_quality": {
            "cheap": 0.547107,
            "mid": 0.846213,
            "premium": 0.896125
          }
        }
      }
    },
    {
      "prompt_id": "p033",
      "prompt": "리액트 19(React 19)에 도입된 Server Actions의 핵심 개념과 이점을 한 문장으로 요약해줘.",
      "domain": "tech",
      "task_type": "qa",
      "benchmark_id": "basic_qa",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.88,
          "cost": 0.01,
          "predicted_quality": 0.749539,
          "calibrated_quality": 0.67973,
          "model_output": "클라이언트 컴포넌트에서 서버 함수를 직접 불러와 실행하는 새로운 데이터 통신 방식입니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.94,
          "cost": 0.05,
          "predicted_quality": 0.95218,
          "calibrated_quality": 0.983868,
          "model_output": "Server Actions는 별도의 백엔드 API 엔드포인트를 개설하지 않고도 비동기 RPC 함수를 정의해 폼 제출 및 클라이언트 상태 업데이트를 서버 측에서 직접 실행하도록 돕는 기능입니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.96,
          "cost": 0.2,
          "predicted_quality": 0.97084,
          "calibrated_quality": 1.027832,
          "model_output": "React 19의 Server Actions는 클라이언트-서버 경계를 제거한 네트워크 단일화 RPC 아키텍처로, 폼 바인딩과 유효성 검사, 낙관적 업데이트(useOptimistic)와의 원활한 결합을 통해 네트워크 오버헤드와 보일러플레이트 코드를 근본적으로 줄여줍니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.88,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3467,
          "utilities": {
            "cheap": 0.885058,
            "mid": 0.819577,
            "premium": -0.428664
          },
          "policy_quality": {
            "cheap": 0.885058,
            "mid": 1.115204,
            "premium": 0.975566
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.94,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3467,
          "utilities": {
            "cheap": 0.701596,
            "mid": 1.082923,
            "premium": 0.962134
          },
          "policy_quality": {
            "cheap": 0.701596,
            "mid": 1.094003,
            "premium": 1.014765
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.96,
          "selected_cost": 0.2,
          "prompt_complexity": 0.3467,
          "utilities": {
            "cheap": 0.67973,
            "mid": 0.972788,
            "premium": 0.9752
          },
          "policy_quality": {
            "cheap": 0.67973,
            "mid": 0.983868,
            "premium": 1.027832
          }
        }
      }
    },
    {
      "prompt_id": "p034",
      "prompt": "이진 검색 트리(Binary Search Tree)가 한쪽으로 편향되었을 때의 문제점과 해결책을 설명해줘.",
      "domain": "math",
      "task_type": "reasoning",
      "benchmark_id": "comparison_medium",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.65,
          "cost": 0.01,
          "predicted_quality": 0.647518,
          "calibrated_quality": 0.577709,
          "model_output": "노드가 한 줄로 늘어서면 탐색 속도가 느려지므로 균형 잡힌 트리로 바꿔야 합니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.92,
          "cost": 0.05,
          "predicted_quality": 0.880701,
          "calibrated_quality": 0.91239,
          "model_output": "트리가 한쪽으로 쏠리면 최악의 경우 검색 시간 복잡도가 $O(\\log N)$에서 $O(N)$으로 악화되어 연결 리스트와 다름없어집니다. 이를 방지하기 위해 AVL 트리나 레드-블랙 트리(Red-Black Tree) 같은 자가 균형 트리 알고리즘을 사용합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.97,
          "cost": 0.2,
          "predicted_quality": 0.934103,
          "calibrated_quality": 0.991095,
          "model_output": "데이터가 정렬된 순서대로 삽입될 때 BST는 편향 트리(Skewed Tree)로 퇴화하여 최악의 조회 연산 성능인 $O(N)$을 유발합니다. 이를 아키텍처적으로 개선하기 위해 삽입 및 삭제 연산 시 노드의 balance factor를 검사하고 트리 회전(Rotation) 연산을 수행하여 서브트리의 높이 균형을 $O(\\log N)$으로 강제 조율하는 자가 균형 이진 탐색 알고리즘(AVL, RB-Tree)을 도입해야 합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.65,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3165,
          "utilities": {
            "cheap": 0.80865,
            "mid": 0.737552,
            "premium": -0.467811
          },
          "policy_quality": {
            "cheap": 0.80865,
            "mid": 1.033179,
            "premium": 0.936418
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.92,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3165,
          "utilities": {
            "cheap": 0.60289,
            "mid": 1.00361,
            "premium": 0.924794
          },
          "policy_quality": {
            "cheap": 0.60289,
            "mid": 1.01469,
            "premium": 0.977425
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.97,
          "selected_cost": 0.2,
          "prompt_complexity": 0.3165,
          "utilities": {
            "cheap": 0.577709,
            "mid": 0.901309,
            "premium": 0.938463
          },
          "policy_quality": {
            "cheap": 0.577709,
            "mid": 0.91239,
            "premium": 0.991095
          }
        }
      }
    },
    {
      "prompt_id": "p035",
      "prompt": "산림 디지털 트윈 환경에서 개별 나무(단목)의 수고(높이) 및 흉고직경 데이터를 추출하는 알고리즘 프로세스를 작성해줘.",
      "domain": "tech",
      "task_type": "complex_design",
      "benchmark_id": "architecture_hard",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.32,
          "cost": 0.01,
          "predicted_quality": 0.624743,
          "calibrated_quality": 0.554934,
          "model_output": "드론으로 찍은 포인트 클라우드에서 나무 꼭대기와 아래를 재서 높이를 구합니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.74,
          "cost": 0.05,
          "predicted_quality": 0.819429,
          "calibrated_quality": 0.851118,
          "model_output": "LiDAR 점구름 데이터에서 지면(DTM)과 산림 표고(DSM)를 분리하여 수관고안내도(CHM)를 생성하고, 국지 최댓값 필터를 이용해 나무 꼭대기를 찾아 수고를 정한 뒤 1.2m 높이 단면에서 점들을 피팅하여 흉고직경을 산출합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.96,
          "cost": 0.2,
          "predicted_quality": 0.848222,
          "calibrated_quality": 0.905214,
          "model_output": "항공/지상형 LiDAR 로우 데이터를 기하 보정 후 CSF(Cloth Simulation Filter) 알고리즘을 적용해 지면 포인트와 식생 포인트를 분리합니다. 지면 제거 후 CHM(Canopy Height Model) 상에서 임목 영역 분할 알고리즘(Watershed 또는 Region Growing)으로 단목을 개별 세그멘테이션하고, 각 세그먼트의 최상단 z값 차이로 수고를 추출하며, 지면으로부터 대략 1.2~1.3m 높이 레이어의 포인트 클라우드 단면 분포를 RANSAC 알고리즘 원형 피팅으로 추정하여 흉고직경(DBH)을 수학적으로 산출하는 아키텍처 파이프라인을 구축합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.32,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3803,
          "utilities": {
            "cheap": 0.73166,
            "mid": 0.698604,
            "premium": -0.548589
          },
          "policy_quality": {
            "cheap": 0.73166,
            "mid": 0.994231,
            "premium": 0.85564
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.74,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3803,
          "utilities": {
            "cheap": 0.573099,
            "mid": 0.958921,
            "premium": 0.840189
          },
          "policy_quality": {
            "cheap": 0.573099,
            "mid": 0.970002,
            "premium": 0.892821
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.96,
          "selected_cost": 0.2,
          "prompt_complexity": 0.3803,
          "utilities": {
            "cheap": 0.554934,
            "mid": 0.840037,
            "premium": 0.852583
          },
          "policy_quality": {
            "cheap": 0.554934,
            "mid": 0.851118,
            "premium": 0.905214
          }
        }
      }
    },
    {
      "prompt_id": "p036",
      "prompt": "회사의 오픈소스 컴포넌트를 사내 사설 npm 저장소에 배포하기 위해 필요한 CI/CD 파이프라인 단계를 작성해줘.",
      "domain": "tech",
      "task_type": "code_generation",
      "benchmark_id": "coding_easy",
      "candidates": [
        {
          "model_id": "cheap",
          "actual_quality": 0.75,
          "cost": 0.01,
          "predicted_quality": 0.703727,
          "calibrated_quality": 0.633919,
          "model_output": "코드 빌드하고 npm publish 명령어로 패키지를 저장소에 올립니다."
        },
        {
          "model_id": "mid",
          "actual_quality": 0.9,
          "cost": 0.05,
          "predicted_quality": 0.872522,
          "calibrated_quality": 0.90421,
          "model_output": "Git에 태그나 푸시가 감지되면 1) 린트 및 테스트 실행, 2) 빌드 도구로 컴포넌트 번들링, 3) `.npmrc` 파일에 사설 레지스트리 토큰 바인딩 후 `npm publish`를 자동 실행하는 파이프라인을 구성합니다."
        },
        {
          "model_id": "premium",
          "actual_quality": 0.96,
          "cost": 0.2,
          "predicted_quality": 0.915791,
          "calibrated_quality": 0.972783,
          "model_output": "GitHub Actions 또는 GitLab CI에서 checkout, dependency install, lint, test, build, version validation, .npmrc registry token injection, npm publish, release note generation 순서로 구성하고, 배포 토큰은 CI secret으로 관리하며 태그 또는 main 브랜치 머지 조건에서만 publish되도록 제한합니다."
        }
      ],
      "routing": {
        "fast": {
          "selected_model_id": "cheap",
          "selected_actual_quality": 0.75,
          "selected_cost": 0.01,
          "prompt_complexity": 0.3101,
          "utilities": {
            "cheap": 0.870305,
            "mid": 0.72713,
            "premium": -0.486636
          },
          "policy_quality": {
            "cheap": 0.870305,
            "mid": 1.022757,
            "premium": 0.917593
          }
        },
        "balanced": {
          "selected_model_id": "mid",
          "selected_actual_quality": 0.9,
          "selected_cost": 0.05,
          "prompt_complexity": 0.3101,
          "utilities": {
            "cheap": 0.659804,
            "mid": 0.993765,
            "premium": 0.906354
          },
          "policy_quality": {
            "cheap": 0.659804,
            "mid": 1.004845,
            "premium": 0.958985
          }
        },
        "premium": {
          "selected_model_id": "premium",
          "selected_actual_quality": 0.96,
          "selected_cost": 0.2,
          "prompt_complexity": 0.3101,
          "utilities": {
            "cheap": 0.633919,
            "mid": 0.89313,
            "premium": 0.920151
          },
          "policy_quality": {
            "cheap": 0.633919,
            "mid": 0.90421,
            "premium": 0.972783
          }
        }
      }
    }
  ]
};
