"""
unittests.py — offline tests.

These tests never touch the network. They run your functions against a *fake*
model that returns scripted text and records the prompts you sent it, so you
can debug for free and stay well inside the free-tier quota.

Usage inside the notebook:

    import unittests
    unittests.test_generate_summary(generate_summary)
    ...
    unittests.run_all_tests(generate_summary, critique_summary, revise_summary)

"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import utils
from utils import PRACTICE_TASK, REPORT_HEADER, check_summary

# --------------------------------------------------------------------------
# A fake model. Same call surface as the real client:
#     client.chat.completions.create(model=..., messages=[...]).choices[0].message.content
# --------------------------------------------------------------------------


class _Msg:
    def __init__(self, content: str):
        self.content = content


class _Choice:
    def __init__(self, content: str):
        self.message = _Msg(content)


class _Response:
    def __init__(self, content: str):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, owner: "FakeClient"):
        self._owner = owner

    def create(self, model: str = "", messages: Optional[List[dict]] = None,
               **kwargs) -> _Response:
        messages = messages or []
        prompt = "\n".join(str(m.get("content", "")) for m in messages)
        self._owner.calls.append(
            {"model": model, "messages": messages, "prompt": prompt,
             "kwargs": kwargs}
        )
        if self._owner.script:
            content = self._owner.script.pop(0)
        else:
            content = self._owner.default
        return _Response(content)


class _Chat:
    def __init__(self, owner: "FakeClient"):
        self.completions = _Completions(owner)


class FakeClient:
    """Returns each string in `script` in turn, then `default` forever."""

    def __init__(self, script: Optional[List[str]] = None,
                 default: str = "FAKE MODEL OUTPUT"):
        self.script = list(script or [])
        self.default = default
        self.calls: List[Dict[str, Any]] = []
        self.chat = _Chat(self)

    @property
    def n_calls(self) -> int:
        return len(self.calls)

    @property
    def last_prompt(self) -> str:
        return self.calls[-1]["prompt"] if self.calls else ""


# --------------------------------------------------------------------------
# Fixtures: one summary that passes every rule of PRACTICE_TASK, one that does not
# --------------------------------------------------------------------------
PASSING_SUMMARY = (
    "Online stores rarely know what to suggest to a brand new shopper. "
    "This work builds a picture of that shopper from the current visit alone. "
    "It watches how long they pause and how far they scroll. "
    "It also watches how they retype their searches. "
    "On the ShopStream-4M click log, the share of first-visit shoppers who "
    "found a wanted item rose from 0.121 to 0.194. "
    "That is a sixty percent jump. "
    "Results for long-time customers did not change."
)

FAILING_SUMMARY = (
    "The authors describe a two-tower architecture in which the user embedding "
    "is replaced by within-session behavioural signal features such as dwell "
    "time, scroll depth and query reformulations, which allows the system to "
    "produce a useful personalization signal for accounts that have no "
    "interaction history at all, and they report a substantial improvement in "
    "recall on the ShopStream-4M click log while leaving established accounts "
    "unchanged."
)


# A draft that breaks ONLY the length rule. Used to prove that critique_summary
# really runs the checker on whatever draft it was given, instead of pasting in a
# report it copied from somewhere else.
LONG_BUT_CLEAN_SUMMARY = (
    "Online stores rarely know what to suggest to a brand new shopper. "
    "This work builds a picture of that shopper from the current visit alone. "
    "It watches how long they pause and how far they scroll. "
    "It also watches how they retype their searches. "
    "On the ShopStream-4M click log, the share of first-visit shoppers who "
    "found a wanted item rose from 0.121 to 0.194. "
    "That is a sixty percent jump. "
    "Results for long-time customers did not change. "
    "The team also ran a live test that lasted three weeks. "
    "The live test agreed with what they had measured before launching it. "
    "They say the method costs nothing extra to run in production. "
    "A brand new visitor needs no past history at all."
)


def _fmt(ok: bool, name: str, detail: str = "") -> tuple:
    if ok:
        return True, f"PASS  {name}"
    return False, f"FAIL  {name}\n      {detail}"


# --------------------------------------------------------------------------
# Exercise 1
# --------------------------------------------------------------------------
def test_generate_summary(fn) -> tuple:
    name = "test_generate_summary"
    try:
        fake = FakeClient(script=["SENTINEL-DRAFT"])
        out = fn(PRACTICE_TASK, client=fake)

        if not isinstance(out, str):
            return _fmt(False, name, f"returned {type(out).__name__}, expected str")
        if fake.n_calls != 1:
            return _fmt(False, name,
                        f"made {fake.n_calls} model call(s); exactly 1 is expected")
        if out.strip() != "SENTINEL-DRAFT":
            return _fmt(False, name,
                        "did not return the model's reply verbatim. Return "
                        "response.choices[0].message.content, and do not "
                        "post-process or hard-code the text.")

        prompt = fake.last_prompt
        if PRACTICE_TASK.abstract[:60] not in prompt:
            return _fmt(False, name,
                        "the abstract was not included in the prompt you sent")
        missing = [s for s in PRACTICE_TASK.must_include if s not in prompt]
        if missing:
            return _fmt(False, name,
                        f"the prompt never mentions the required string(s) {missing}. "
                        "State the task's rules in the prompt — task.rules_text() "
                        "gives you all four.")
        unstated = [t for t in PRACTICE_TASK.banned_terms
                    if t.lower() not in prompt.lower()]
        if unstated:
            return _fmt(False, name,
                        f"the prompt never lists the banned term(s) {unstated}. "
                        "The model cannot avoid words it was not told about — "
                        "include task.rules_text().")
        return _fmt(True, name)
    except Exception as exc:  # noqa: BLE001
        return _fmt(False, name, f"{type(exc).__name__}: {exc}")


# --------------------------------------------------------------------------
# Exercise 2
# --------------------------------------------------------------------------
def test_critique_summary(fn) -> tuple:
    name = "test_critique_summary"
    try:
        fake = FakeClient(script=["SENTINEL-CRITIQUE"])
        out = fn(FAILING_SUMMARY, PRACTICE_TASK, client=fake)

        if not isinstance(out, str):
            return _fmt(False, name, f"returned {type(out).__name__}, expected str")
        if fake.n_calls != 1:
            return _fmt(False, name,
                        f"made {fake.n_calls} model call(s); exactly 1 is expected")
        if out.strip() != "SENTINEL-CRITIQUE":
            return _fmt(False, name,
                        "did not return the model's reply verbatim")

        prompt = fake.last_prompt
        if FAILING_SUMMARY[:60] not in prompt:
            return _fmt(False, name,
                        "the draft being critiqued was not included in the prompt")
        if REPORT_HEADER not in prompt:
            return _fmt(False, name,
                        "the prompt does not contain the output of "
                        "check_summary(...)['report']. This exercise is about "
                        "giving the critic a tool: run the checker first and paste "
                        "its report into the prompt.")
        if "FAIL" not in prompt:
            return _fmt(False, name,
                        "the report in your prompt shows no failures — you may be "
                        "checking the wrong text. Check the draft that was passed in.")

        # Run it again on a different draft: one that breaks only the length rule.
        # The report has to change accordingly, which it cannot do if the student
        # pasted fixed report text into the prompt instead of calling the checker.
        fake2 = FakeClient(script=["SENTINEL-CRITIQUE-2"])
        fn(LONG_BUT_CLEAN_SUMMARY, PRACTICE_TASK, client=fake2)
        prompt2 = fake2.last_prompt
        expected = check_summary(LONG_BUT_CLEAN_SUMMARY, PRACTICE_TASK)
        for line in expected["report"].splitlines():
            if line.strip().startswith("[") and line.strip() not in prompt2:
                return _fmt(False, name,
                            "the report in your prompt does not match the draft you "
                            "were given. Call check_summary(summary, task) inside "
                            "this function on the summary argument — do not copy a "
                            "report's text into the prompt by hand.")
        return _fmt(True, name)
    except Exception as exc:  # noqa: BLE001
        return _fmt(False, name, f"{type(exc).__name__}: {exc}")


# --------------------------------------------------------------------------
# Exercise 3
# --------------------------------------------------------------------------
def test_revise_summary(fn) -> tuple:
    name = "test_revise_summary"
    critique = "CRITIQUE-TEXT-12345: cut the jargon and shorten the sentences."
    try:
        fake = FakeClient(script=["SENTINEL-REVISION"])
        out = fn(FAILING_SUMMARY, critique, PRACTICE_TASK, client=fake)

        if not isinstance(out, str):
            return _fmt(False, name, f"returned {type(out).__name__}, expected str")
        if fake.n_calls != 1:
            return _fmt(False, name,
                        f"made {fake.n_calls} model call(s); exactly 1 is expected")
        if out.strip() != "SENTINEL-REVISION":
            return _fmt(False, name, "did not return the model's reply verbatim")

        prompt = fake.last_prompt
        if FAILING_SUMMARY[:60] not in prompt:
            return _fmt(False, name, "the draft to revise was not in the prompt")
        if "CRITIQUE-TEXT-12345" not in prompt:
            return _fmt(False, name,
                        "the critique was not in the prompt — the revision step has "
                        "to actually receive the feedback")
        return _fmt(True, name)
    except Exception as exc:  # noqa: BLE001
        return _fmt(False, name, f"{type(exc).__name__}: {exc}")


# --------------------------------------------------------------------------
def run_all_tests(generate_summary, critique_summary, revise_summary) -> bool:
    results = [
        test_generate_summary(generate_summary),
        test_critique_summary(critique_summary),
        test_revise_summary(revise_summary),
    ]
    for _, msg in results:
        print(msg)
    passed = sum(1 for ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} tests passed.")
    return passed == len(results)


# A sanity check on the fixtures themselves (used by the instructor smoke test).
def _self_check() -> None:
    assert check_summary(PASSING_SUMMARY, PRACTICE_TASK)["passed"], \
        check_summary(PASSING_SUMMARY, PRACTICE_TASK)["report"]
    assert not check_summary(FAILING_SUMMARY, PRACTICE_TASK)["passed"]
    assert utils.REPORT_HEADER in check_summary(FAILING_SUMMARY, PRACTICE_TASK)["report"]


if __name__ == "__main__":
    _self_check()
    print("fixtures OK")
