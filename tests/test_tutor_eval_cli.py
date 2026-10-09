"""Tutor evaluation CLI: single-model reports by default, multi-model only when asked, nothing overwritten.

Works on copies of the real Phase 4.1 transcripts in a temporary directory; no model is run, Ollama is not needed.

    python3 -m pytest tests -q
"""
import shutil
from pathlib import Path

import pytest

from src.evaluation import tutor_eval
from src.tutor.llm import DEFAULT_MODEL

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/evaluation/tutor_eval_v2"
BENCH = ROOT / "data/evaluation/retrieval_queries_v1.1.json"
QWEN, LLAMA = "qwen3:8b", "llama3.1:8b"


@pytest.fixture
def out(tmp_path):
    for name in ("qwen3_8b_transcripts.json", "llama3.1_8b_transcripts.json",
                 "manual_grades_qwen3_8b.json", "manual_grades_llama3.1_8b.json"):
        shutil.copy(SRC / name, tmp_path / name)
    (tmp_path / "report.md").write_text("earlier comparison\n")  # stands in for an existing result
    return tmp_path


def test_qwen_is_still_the_application_default():
    assert DEFAULT_MODEL == QWEN


def test_single_model_report_scores_only_that_model(out):
    (out / "llama3.1_8b_transcripts.json").unlink()  # the other model's data is not needed
    path = tutor_eval.report([QWEN], out, BENCH)
    assert path == out / "report_qwen3_8b.md"
    text = path.read_text()
    assert text.startswith("# Tutor Quality Evaluation — qwen3:8b\n")
    assert "Model evaluated: `qwen3:8b` (single-model report" in text
    assert LLAMA not in text and "| Check | qwen3:8b |" in text


def test_multi_model_report_only_when_requested(out):
    path = tutor_eval.report([QWEN, LLAMA], out, BENCH)
    assert path == out / "report_qwen3_8b_vs_llama3.1_8b.md"
    text = path.read_text()
    assert "Models evaluated (comparison requested explicitly): `qwen3:8b`, `llama3.1:8b`" in text
    assert "| Check | qwen3:8b | llama3.1:8b |" in text


def test_comparison_path_and_content_ignore_typing_order(out):
    a = tutor_eval.report([QWEN, LLAMA], out, BENCH)
    first = a.read_bytes()
    b = tutor_eval.report([LLAMA, QWEN], out, BENCH)
    assert a == b == out / "report_qwen3_8b_vs_llama3.1_8b.md" and b.read_bytes() == first
    assert tutor_eval.report_path([LLAMA, QWEN], out) == tutor_eval.report_path([QWEN, LLAMA], out)
    assert tutor_eval.canonical(["zeta:1b", LLAMA, QWEN, LLAMA]) == [QWEN, LLAMA, "zeta:1b"]  # primary first, deduped
    assert tutor_eval.report_path([QWEN], out) == out / "report_qwen3_8b.md"  # single-model name unchanged
    assert not (out / "report_llama3.1_8b_vs_qwen3_8b.md").exists()


def test_reports_never_overwrite_existing_results(out):
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    tutor_eval.report([QWEN], out, BENCH)
    tutor_eval.report([QWEN, LLAMA], out, BENCH)
    assert {p.name: p.read_bytes() for p in out.iterdir() if p.name in before} == before
    assert sorted(p.name for p in out.glob("report*.md")) == \
        ["report.md", "report_qwen3_8b.md", "report_qwen3_8b_vs_llama3.1_8b.md"]


def test_missing_model_fails_clearly_without_writing(out):
    (out / "llama3.1_8b_transcripts.json").unlink()
    with pytest.raises(FileNotFoundError, match=r"no transcripts for llama3\.1:8b .*run --model llama3\.1:8b"):
        tutor_eval.report([QWEN, LLAMA], out, BENCH)
    assert not list(out.glob("report_*.md"))


def test_cli_single_and_multi(out, capsys):
    assert tutor_eval.main(["report", QWEN, "--output-dir", str(out)]) == 0
    assert capsys.readouterr().out.strip().endswith("report_qwen3_8b.md")
    assert tutor_eval.main(["report", QWEN, LLAMA, "--output-dir", str(out)]) == 0
    assert capsys.readouterr().out.strip().endswith("report_qwen3_8b_vs_llama3.1_8b.md")
    with pytest.raises(SystemExit, match="no transcripts for mistral:7b"):
        tutor_eval.main(["report", "mistral:7b", "--output-dir", str(out)])


def test_cli_requires_an_explicit_model(out):
    with pytest.raises(SystemExit):
        tutor_eval.main(["report", "--output-dir", str(out)])
    with pytest.raises(SystemExit):
        tutor_eval.main(["run", "--output-dir", str(out)])
