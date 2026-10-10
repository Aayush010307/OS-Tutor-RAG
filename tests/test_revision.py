"""Product upgrade tests: Smart Revision with a scripted LLM, a fake retriever and a real learner model (no Ollama, no index).

    python3 -m pytest tests -q
"""
import json

import pytest

from src.learner.model import LearnerModel
from src.revision.service import (DIFFICULTY, FEEDBACK, LEVELS, NO_WEAK_CONCEPTS, QUESTION, RevisionService,
                                  split_question, start_level)
from src.tutor.llm import LLMError
from src.tutor.service import TutorInputError


def chunk(i, text="Course passage about the concept."):
    return {"chunk_id": f"doc::c{i:04d}", "filename": "doc.pdf", "section": "S", "page_start": i, "slide_start": None,
            "text": text, "metadata": {"subtopics": ["Race Conditions"], "source": "VIT", "document_title": "Notes"}}


class Retriever:
    def __init__(self, results=None):
        self.queries, self.results = [], results

    def search(self, query, top_k=5):
        self.queries.append(query)
        return [chunk(1), chunk(2)] if self.results is None else self.results


class Script:
    """Text replies are numbered questions; analysis levels are popped in order."""
    def __init__(self, levels=()):
        self.levels, self.prompts, self.n = list(levels), [], 0

    def __call__(self, prompt, json_mode=False, on_token=None):
        self.prompts.append(prompt)
        if json_mode:
            return json.dumps({"level": self.levels.pop(0), "gap": "the lost-update idea"})
        self.n += 1
        out = f"Feedback number {self.n} [S1].\n\nQuestion number {self.n}: what happens next?"
        if on_token:
            on_token(out)
        return out


def task_of(prompt):
    return prompt.split("\nTASK\n", 1)[1].split("\n\nCOURSE CONTEXT", 1)[0]


def weak_learner(confidence_kind="misconception", concept="race_condition"):
    learner = LearnerModel()
    learner.record_doubt([concept], "Why does counter++ cause a race condition?")
    if confidence_kind:
        learner.record_evidence(concept, confidence_kind, "thinks races need two processes")
    return learner


def make(levels=(), learner=None, results=None, steps=5):
    learner = learner or weak_learner()
    llm, retriever = Script(levels), Retriever(results)
    return RevisionService(retriever, llm, learner, top_k=3, steps=steps), llm, retriever, learner


# ------------------------------------------------------------------ choosing what to revise
def test_nothing_to_revise_is_said_plainly():
    svc, llm, _, _ = make(learner=LearnerModel())
    with pytest.raises(TutorInputError, match="nothing to revise"):
        svc.start()
    assert NO_WEAK_CONCEPTS.startswith("There is nothing to revise") and llm.prompts == []


def test_the_weakest_concept_is_chosen_with_the_reason():
    learner = weak_learner("misconception", "race_condition")
    learner.record_doubt(["semaphore"], "what is a semaphore?")
    svc, _, _, _ = make(learner=learner)
    session, turn = svc.start()
    assert session.concept == "race_condition" and turn.concept["id"] == "race_condition"
    assert "misconception: thinks races need two processes" in turn.reason and turn.stage == "QUESTION"
    assert [t["id"] for t in svc.topics()] == ["race_condition", "semaphore"]


def test_the_student_can_pick_a_concept_and_unknown_ones_are_refused():
    svc, _, _, _ = make()
    session, turn = svc.start("mutex")
    assert session.concept == "mutex" and turn.reason == "You chose this concept to revise."
    with pytest.raises(TutorInputError, match="not part of this course"):
        svc.start("paging")


@pytest.mark.parametrize("conf,level", [(None, "recall"), (0.2, "recall"), (0.45, "understanding"),
                                        (0.7, "application"), (0.9, "reasoning")])
def test_the_starting_level_fits_what_the_learner_knows(conf, level):
    assert start_level(conf) == level


def test_questions_are_built_from_the_students_own_history_and_the_course_material():
    svc, llm, retriever, _ = make()
    session, turn = svc.start()
    prompt = llm.prompts[0]
    assert task_of(prompt) == QUESTION["recall"] and turn.level == "recall" and turn.difficulty == "easy"
    assert "the student once asked: Why does counter++ cause a race condition?" in prompt
    assert "earlier misconception on record: thinks races need two processes" in prompt
    assert "Course passage about the concept." in prompt and "race condition" in retriever.queries[0]
    assert turn.question == turn.message and turn.feedback is None
    assert turn.progress == {"step": 1, "total": 5} and [s["ref"] for s in turn.sources] == ["S1", "S2"]


def test_course_material_is_retrieved_once_per_concept_and_reused():
    svc, _, retriever, _ = make(["solid", "solid"])
    session, _ = svc.start()
    svc.answer(session, "an answer that is long enough to count as one")
    svc.answer(session, "another answer that is long enough to count too")
    assert len(retriever.queries) == 1  # recall, understanding, application all share one retrieval
    svc2, _, retriever2, _ = make(["solid"] * 4, steps=6)
    s2, _ = svc2.start()
    for _ in range(4):  # recall -> understanding -> application -> reasoning -> code
        svc2.answer(s2, "a solid answer with enough words in it")
    assert len(retriever2.queries) == 2 and retriever2.queries[1].endswith("code example")  # the code level wants code


# ------------------------------------------------------------------ adapting to the answers
def run(levels, learner=None, steps=5):
    svc, llm, retriever, learner = make(levels, learner, steps=steps)
    session, turn = svc.start()
    turns = [turn]
    for _ in levels:
        if session.stage == "SUMMARY":
            break
        turns.append(svc.answer(session, "my answer to the question, in a few words"))
    return svc, llm, learner, session, turns


def test_correct_answers_climb_the_levels():
    _, _, _, _, turns = run(["solid", "solid", "solid"])
    assert [t.level for t in turns] == ["recall", "understanding", "application", "reasoning"]
    assert [t.difficulty for t in turns] == ["easy", "easy", "medium", "hard"]
    assert turns[1].stage == "FEEDBACK" and turns[1].feedback.startswith("Feedback number 2") and \
        turns[1].question.startswith("Question number 2") and turns[1].analysis["level"] == "solid"


def test_a_partial_answer_gets_a_follow_up_at_the_same_level():
    _, llm, _, _, turns = run(["solid", "partial"])
    assert [t.level for t in turns] == ["recall", "understanding", "understanding"]
    prompt = llm.prompts[-1]
    assert "GAP\nthe lost-update idea" in prompt and "follow-up question about the missing idea" in task_of(prompt)


def test_a_misconception_is_corrected_and_the_next_question_is_easier():
    _, llm, _, _, turns = run(["solid", "solid", "misconception"])
    assert [t.level for t in turns] == ["recall", "understanding", "application", "understanding"]
    assert "not correct" in FEEDBACK["misconception"] and task_of(llm.prompts[-1]).startswith("The student's answer contains")


def test_an_unclear_answer_gets_a_simpler_explanation_and_the_question_again():
    _, llm, _, _, turns = run(["solid", "unclear"])
    assert turns[-1].level == "recall" and task_of(llm.prompts[-1]).startswith("The student could not answer")


def test_dont_know_needs_no_model_call_and_just_tell_me_counts_as_not_knowing():
    svc, llm, _, learner = make()
    session, _ = svc.start()
    calls = len(llm.prompts)
    turn = svc.answer(session, "I don't know")
    assert turn.analysis["level"] == "unclear" and not any("Reply with JSON" in p for p in llm.prompts[calls:])
    assert svc.answer(session, "just tell me the answer").analysis["level"] == "unclear"


def test_questions_already_asked_are_not_repeated():
    svc, llm, _, _ = make(["solid", "solid"])
    session, first = svc.start()
    svc.answer(session, "an answer with several words in it")
    assert "QUESTIONS ALREADY ASKED" not in llm.prompts[0]
    assert f"- {first.question}" in llm.prompts[-1]


# ------------------------------------------------------------------ stepping back to a prerequisite
def questions_asked(llm):
    """The prompts that asked for a question or feedback (the analysis calls are filtered out)."""
    return [p for p in llm.prompts if "Reply with JSON only" not in p]


def test_two_misses_in_a_row_step_back_to_a_prerequisite_then_return_to_reassess():
    svc, llm, learner, session, turns = run(["unclear", "unclear", "solid", "solid"])
    assert [t.concept["id"] for t in turns] == ["race_condition", "race_condition", "shared_data", "race_condition",
                                                "race_condition"]
    gen = questions_asked(llm)
    assert turns[2].level == "understanding" and "stepping back to a concept this builds on: Shared data" in gen[2]
    assert turns[3].level == "application" and "returning to Race condition" in gen[3]
    assert session.concept == "race_condition" and session.focus == "race_condition"


def test_the_detour_happens_only_once_per_session():
    _, _, _, _, turns = run(["unclear", "unclear", "unclear", "unclear", "unclear", "unclear"], steps=8)
    assert [t.concept["id"] for t in turns].count("shared_data") == 1


def test_the_weakest_prerequisite_is_the_one_chosen():
    learner = weak_learner(concept="condition_variable")
    learner.record_evidence("mutex", "solid"), learner.record_evidence("mutex", "solid")  # strong: skipped
    svc, _, _, _ = make(learner=learner)
    assert svc._weakest_prerequisite("condition_variable") is None
    learner.record_evidence("mutex", "misconception")
    assert svc._weakest_prerequisite("condition_variable") == "mutex"


# ------------------------------------------------------------------ the learner model and the end of the session
def test_every_answer_updates_the_learner_model():
    svc, _, learner, session, turns = run(["solid", "misconception"])
    assert turns[1].learner_update["concept_id"] == "race_condition" and turns[1].learner_update["change"] > 0
    assert turns[2].learner_update["change"] < 0
    assert learner.concept_state("race_condition")["attempts"] == 3  # the setup misconception + two answers


def test_the_session_ends_with_a_deterministic_summary():
    svc, llm, learner, session, turns = run(["solid"] * 5, steps=3)
    end = turns[-1]
    assert end.stage == "SUMMARY" and end.done and end.question is None and session.stage == "SUMMARY"
    assert end.progress == {"step": 3, "total": 3} and end.summary["answered"] == 3 and end.summary["correct"] == 3
    assert "Revision complete: 3 of 3 answers were fully correct." in end.message
    row = end.summary["concepts"][0]
    assert row["id"] == "race_condition" and row["after"] > row["before"] and "→" in end.message
    assert task_of(llm.prompts[-1]) == FEEDBACK["final"]  # the last answer still gets feedback, without a new question
    with pytest.raises(TutorInputError, match="finished"):
        svc.answer(session, "one more")


def test_solid_answers_all_the_way_up_finish_early():
    _, _, _, session, turns = run(["solid"] * 6, steps=9)
    assert [t.level for t in turns][:5] == list(LEVELS) and turns[-1].stage == "SUMMARY" and session.answered == 5


def test_a_session_that_helped_says_so_and_one_that_did_not_says_that_too():
    _, _, _, _, turns = run(["unclear", "unclear"], steps=2)
    assert "not strong yet; another round is worth it" in turns[-1].message


def test_improvement_between_first_and_later_attempts_is_recorded():
    _, _, learner, session, turns = run(["misconception", "partial", "solid", "solid"], steps=4)
    changes = [r["update"]["confidence"] for r in session.results]
    assert changes[0] < changes[-1] and turns[-1].summary["concepts"][0]["after"] > turns[-1].summary["concepts"][0]["before"]


# ------------------------------------------------------------------ failures
def test_a_failed_model_call_changes_neither_the_session_nor_the_learner():
    svc, llm, learner, session, _ = run([])
    session = svc.start()[0]
    before = (session.answered, list(session.history), session.question, learner.profile())
    good = svc.llm

    def down(prompt, json_mode=False, on_token=None):
        if json_mode:
            return '{"level": "solid", "gap": ""}'
        raise LLMError("unavailable", "refused")
    svc.llm = down
    with pytest.raises(LLMError):
        svc.answer(session, "a perfectly good answer with many words")
    assert (session.answered, session.history, session.question, learner.profile()) == before
    svc.llm = Script(["solid"])
    svc.answer(session, "a perfectly good answer with many words")
    assert session.answered == 1 and learner.concept_state("race_condition")["attempts"] == 2  # counted once, not twice


def test_no_course_material_means_no_made_up_question():
    svc, llm, _, _ = make(results=[])
    with pytest.raises(TutorInputError, match="relevant course material"):
        svc.start()
    assert llm.prompts == []


def test_blank_answers_are_refused():
    svc, _, _, _ = make()
    session, _ = svc.start()
    with pytest.raises(TutorInputError, match="Type an answer"):
        svc.answer(session, "   ")


# ------------------------------------------------------------------ splitting feedback from the next question
@pytest.mark.parametrize("message,feedback,question", [
    ("Good.\n\nWhy does it fail?", "Good.", "Why does it fail?"),
    ("Why does it fail?", None, "Why does it fail?"),
    ("Just a statement.", "Just a statement.", None),
    ("Right [S1].\n\n```c\nint x;\n\nx++;\n```\n\nWhere is the bug?", "Right [S1].\n\n```c\nint x;\n\nx++;\n```", "Where is the bug?"),
    ("", None, None),
])
def test_feedback_and_question_are_separated(message, feedback, question):
    assert split_question(message) == (feedback, question)


def test_every_level_has_a_question_instruction_and_a_difficulty():
    assert set(QUESTION) == set(LEVELS) == set(DIFFICULTY)
