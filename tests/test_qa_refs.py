"""QA refs tests: the code-question doc keeps pointing at the code it describes.

What: runs checks/qa_refs.py's selftest and checks docs/CODE_QA.md itself.
Why:  a later fix can move code under a cited line; this test fails then, before a judge opens a stale reference.
How:  calls the checker's functions directly, with the question count from config/ewu.yaml.
"""
from checks import qa_refs


def test_selftest_catches_every_planted_fault():
    assert qa_refs.run_selftest()


def test_code_qa_references_all_resolve():
    text = (qa_refs.ROOT / "docs" / "CODE_QA.md").read_text()
    resolved, problems = qa_refs.check_document(text, qa_refs.files_a_judge_can_open(), qa_refs.required_questions())
    assert problems == [] and resolved
