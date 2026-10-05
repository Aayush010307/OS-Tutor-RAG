# Tutor Quality Evaluation

Scripted student dialogues (data/evaluation/tutor_scenarios_v1.json: 8 questions x 3 profiles) run through the tutor with the E2 hybrid retriever and a local Ollama model (temperature 0, seed 42). Measurements only.

## Automatic checks

| Check | qwen3:8b | llama3.1:8b |
| --- | --- | --- |
| Dialogues following the expected path | 21/24 (88%) | 19/24 (79%) |
| Analysis: exact level agreement | 39/48 (81%) | 34/46 (74%) |
| Analysis: solid / not-solid agreement | 52/56 (93%) | 46/54 (85%) |
| Analysis: valid JSON | 56/56 (100%) | 54/54 (100%) |
| DIAGNOSE asks exactly one question | 24/24 (100%) | 12/24 (50%) |
| CHECK asks exactly one question | 7/7 (100%) | 7/11 (64%) |
| EXPLAIN ends with a check question | 28/28 (100%) | 20/21 (95%) |
| WRAP_UP asks no question | 13/13 (100%) | 19/19 (100%) |
| EXPLAIN / WRAP_UP / ANSWER cite a source | 16/49 (33%) | 41/43 (95%) |
| All citations point to a given source | 80/80 (100%) | 78/78 (100%) |
| Turns within 120 words | 78/80 (98%) | 60/78 (77%) |
| Turns mentioning context / instructions | 5/80 (6%) | 2/78 (3%) |
| Grade-2 chunk among the 5 retrieved (per dialogue) | 24/24 (100%) | 24/24 (100%) |

| Expected path followed, by student profile | qwen3:8b | llama3.1:8b |
| --- | --- | --- |
| solid | 7/8 (88%) | 7/8 (88%) |
| misconception | 6/8 (75%) | 8/8 (100%) |
| unsure | 8/8 (100%) | 4/8 (50%) |

| Latency per model call (s) | qwen3:8b | llama3.1:8b |
| --- | --- | --- |
| tutor: median / max | 8.9 / 18.3 | 11.7 / 25.1 |
| analysis: median / max | 4.3 / 12.7 | 3.7 / 6.5 |

Tutor turns scored: qwen3:8b 80, llama3.1:8b 78.

## Manual rubric (0-2 per turn, single annotator)

| Criterion | qwen3:8b | llama3.1:8b |
| --- | --- | --- |
| correct | mean 1.76; 2: 62, 1: 17, 0: 1 | mean 1.51; 2: 48, 1: 22, 0: 8 |
| grounded | mean 1.94; 2: 75, 1: 5, 0: 0 | mean 1.77; 2: 61, 1: 16, 0: 1 |
| pedagogy | mean 1.39; 2: 38, 1: 35, 0: 7 | mean 1.26; 2: 31, 1: 36, 0: 11 |

| Mean pedagogy by turn type | qwen3:8b | llama3.1:8b |
| --- | --- | --- |
| DIAGNOSE | 1.00 (n=24) | 1.12 (n=24) |
| EXPLAIN | 1.21 (n=28) | 1.29 (n=21) |
| CHECK | 1.71 (n=7) | 0.91 (n=11) |
| WRAP_UP | 1.92 (n=13) | 1.47 (n=19) |
| ANSWER | 2.00 (n=8) | 2.00 (n=3) |

