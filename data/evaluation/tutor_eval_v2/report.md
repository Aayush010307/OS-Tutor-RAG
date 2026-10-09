# Tutor Quality Evaluation

Scripted student dialogues (data/evaluation/tutor_scenarios_v1.json: 8 questions x 3 profiles) run through the tutor with the E2 hybrid retriever and a local Ollama model. Measurements only.

Generation settings: qwen3:8b {'temperature': 0.3, 'seed': 42, 'num_ctx': 8192}; llama3.1:8b {'temperature': 0.3, 'seed': 42, 'num_ctx': 8192}

## Automatic checks

| Check | qwen3:8b | llama3.1:8b |
| --- | --- | --- |
| Dialogues following the expected path | 23/24 (96%) | 24/24 (100%) |
| Analysis: exact level agreement | 46/48 (96%) | 48/48 (100%) |
| Analysis: solid / not-solid agreement | 55/56 (98%) | 56/56 (100%) |
| Analysis: valid JSON | 56/56 (100%) | 56/56 (100%) |
| DIAGNOSE asks exactly one question | 24/24 (100%) | 24/24 (100%) |
| CHECK asks exactly one question | 7/8 (88%) | 4/8 (50%) |
| EXPLAIN ends with a check question | 25/25 (100%) | 24/24 (100%) |
| WRAP_UP asks no question | 15/15 (100%) | 16/16 (100%) |
| EXPLAIN / WRAP_UP / ANSWER cite a source | 40/48 (83%) | 34/48 (71%) |
| All citations point to a given source | 80/80 (100%) | 80/80 (100%) |
| Turns within 120 words | 70/80 (88%) | 39/80 (49%) |
| Turns mentioning context / instructions | 4/80 (5%) | 6/80 (8%) |
| Grade-2 chunk among the 5 retrieved (per dialogue) | 24/24 (100%) | 24/24 (100%) |

| Expected path followed, by student profile | qwen3:8b | llama3.1:8b |
| --- | --- | --- |
| solid | 8/8 (100%) | 8/8 (100%) |
| misconception | 7/8 (88%) | 8/8 (100%) |
| unsure | 8/8 (100%) | 8/8 (100%) |

| Latency per model call (s) | qwen3:8b | llama3.1:8b |
| --- | --- | --- |
| tutor: median / max | 21.1 / 43.6 | 33.7 / 88.3 |
| analysis: median / max | 5.7 / 22.6 | 4.3 / 26.0 |

Tutor turns scored: qwen3:8b 80, llama3.1:8b 80.

## Manual rubric (0-2 per turn, single annotator)

| Criterion | qwen3:8b | llama3.1:8b |
| --- | --- | --- |
| correct | mean 1.98; 2: 79, 1: 0, 0: 1 | mean 1.84; 2: 69, 1: 9, 0: 2 |
| grounded | mean 1.89; 2: 72, 1: 7, 0: 1 | mean 1.81; 2: 65, 1: 15, 0: 0 |
| pedagogy | mean 1.38; 2: 33, 1: 44, 0: 3 | mean 1.40; 2: 48, 1: 16, 0: 16 |

| Mean pedagogy by turn type | qwen3:8b | llama3.1:8b |
| --- | --- | --- |
| DIAGNOSE | 1.00 (n=24) | 2.00 (n=24) |
| EXPLAIN | 1.08 (n=25) | 1.29 (n=24) |
| CHECK | 1.75 (n=8) | 0.50 (n=8) |
| WRAP_UP | 2.00 (n=15) | 0.81 (n=16) |
| ANSWER | 1.88 (n=8) | 2.00 (n=8) |

