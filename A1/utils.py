"""
utils.py — helper code.

You do NOT need to modify this file, but you SHOULD read two things:

  1. get_client()    — how the notebook talks to the model API.
  2. check_summary() — the deterministic rule checker your agent has to satisfy.
                       This is the "tool" that your critic will be allowed to use.

"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

# --------------------------------------------------------------------------
# 1. Model configuration
# --------------------------------------------------------------------------
# We talk to Google's Gemini API through its OpenAI-compatible endpoint, so
# `aisuite`'s "openai" provider works unchanged. The "openai:" prefix below
# selects the *wire protocol*, not the vendor — the request goes to Google and
# is billed against your own free-tier key.
#
# ---------------------------------------------------------------------------
# Free-tier limits, measured against a real key on 2026-09-13. Check your own
# live numbers at https://aistudio.google.com/rate-limit
#
#   gemini-3.5-flash-lite      15 req/min    500 req/day   <- what we use
#   gemini-3.1-flash-lite      15 req/min    500 req/day   <- verified alternate
#   gemini-3.5-flash            5 req/min     20 req/day   <- too small for a class
#   gemini-2.5-flash            404: no longer available to new users
#   gemini-2.5-flash-lite       404: no longer available to new users
#
# A full run of the notebook is about 21 requests, so 500/day is roughly 23 runs.
# If a model id starts returning 404, Google has retired it: pick a current
# Flash-Lite id from https://ai.google.dev/gemini-api/docs/models and put it here.
# ---------------------------------------------------------------------------

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Two separate constants on purpose. In a production system the critic would get
# a stronger (and more expensive) model than the writer, because judging work is
# harder than producing it. The free tier only offers one usable class of model,
# so for now both point at the same one — and upgrading the critic later is a
# one-line change right here.
DRAFT_MODEL = "openai:gemini-3.5-flash-lite"
CRITIC_MODEL = "openai:gemini-3.5-flash-lite"

# The models above allow 15 requests per minute. get_client() returns a client
# that spaces its own calls out by this many seconds, which works out to 12 per
# minute, so a long loop never trips a 429. You do not have to think about it.
MIN_SECONDS_BETWEEN_CALLS = 5.0


class _ThrottledCompletions:
    def __init__(self, inner, owner):
        self._inner = inner
        self._owner = owner

    def create(self, *args, **kwargs):
        wait = self._owner._last_call + MIN_SECONDS_BETWEEN_CALLS - time.time()
        if wait > 0:
            time.sleep(wait)
        self._owner._last_call = time.time()
        self._owner.n_calls += 1
        return self._inner.create(*args, **kwargs)


class _ThrottledChat:
    def __init__(self, inner, owner):
        self.completions = _ThrottledCompletions(inner.completions, owner)


class ThrottledClient:
    """Thin wrapper around the real client that rate-limits and counts calls.

    Same call surface as the underlying client:
        client.chat.completions.create(model=..., messages=[...])
    """

    def __init__(self, inner):
        self._inner = inner
        self._last_call = 0.0
        self.n_calls = 0
        self.chat = _ThrottledChat(inner.chat, self)


def get_client():
    """Return a rate-limited client wired to the Gemini API.

    Requires GEMINI_API_KEY in the environment (put it in a .env file next to
    this notebook). Get a free key at https://aistudio.google.com/apikey
    """
    from dotenv import load_dotenv

    # Look for .env next to this file first (so the notebook works even when it
    # is opened from a different folder), then fall back to the usual search.
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(here):
        load_dotenv(here)
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set.\n"
            "  1. Get a free key at https://aistudio.google.com/apikey\n"
            "  2. Copy .env.example to .env\n"
            "  3. Paste the key after GEMINI_API_KEY=\n"
            "  4. Restart the notebook kernel."
        )

    import aisuite as ai

    return ThrottledClient(
        ai.Client({"openai": {"api_key": api_key, "base_url": GEMINI_BASE_URL}})
    )


# --------------------------------------------------------------------------
# 2. Pretty printing
# --------------------------------------------------------------------------
def show_output(title: str, content: str, background: str = "#f0f0f0",
                text_color: str = "#000000") -> None:
    """Display a block of model output in a labelled, coloured box."""
    from IPython.display import HTML, display

    safe = (str(content).replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;"))
    html = f"""
    <div style="border:1px solid #ccc;border-radius:10px;padding:15px;
                margin-bottom:15px;background-color:{background};
                color:{text_color};">
        <h3 style="margin-top:0;">{title}</h3>
        <pre style="white-space:pre-wrap;font-family:monospace;font-size:14px;">{safe}</pre>
    </div>
    """
    display(HTML(html))


# --------------------------------------------------------------------------
# 3. The task definition
# --------------------------------------------------------------------------
@dataclass
class SummaryTask:
    """One 'explain this abstract in plain language' job, plus its rules."""

    id: str
    title: str
    abstract: str
    must_include: List[str] = field(default_factory=list)
    banned_terms: List[str] = field(default_factory=list)
    max_words: int = 100
    max_sentence_words: int = 20

    def rules_text(self) -> str:
        """The rules, written out in English, for use inside a prompt."""
        return (
            f"1. At most {self.max_words} words in total.\n"
            f"2. Must contain these exact strings, spelled exactly as given: "
            f"{', '.join(repr(s) for s in self.must_include)}\n"
            f"3. Must NOT use any of these words or phrases (or forms of them): "
            f"{', '.join(repr(s) for s in self.banned_terms)}\n"
            f"4. No sentence longer than {self.max_sentence_words} words."
        )


# --------------------------------------------------------------------------
# 4. The deterministic checker  ("the tool")
# --------------------------------------------------------------------------
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _words(text: str) -> List[str]:
    return [w for w in re.split(r"\s+", text.strip()) if w]


def _find_banned(text: str, term: str) -> bool:
    """Case-insensitive match. Single words also match their inflections
    ('distillation' matches 'distillations'; 'teacher' matches 'teachers')."""
    if " " in term or "-" in term:
        return term.lower() in text.lower()
    pattern = r"\b" + re.escape(term) + r"\w*"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def check_summary(summary: str, task: SummaryTask) -> Dict[str, Any]:
    """Score a candidate summary against the task's four rules.

    Returns a dict with:
        passed  (bool)  — all four rules satisfied
        score   (int)   — how many of the four rules are satisfied, 0-4
        results (list)  — one {"rule", "ok", "detail"} dict per rule
        report  (str)   — a human-readable report, safe to paste into a prompt
    """
    summary = "" if summary is None else str(summary)
    results: List[Dict[str, Any]] = []

    # Rule 1 — length
    n_words = len(_words(summary))
    results.append({
        "rule": "length",
        "ok": n_words <= task.max_words,
        "detail": f"{n_words} words (limit {task.max_words})",
    })

    # Rule 2 — grounding: required strings present, verbatim
    missing = [s for s in task.must_include if s.lower() not in summary.lower()]
    results.append({
        "rule": "grounding",
        "ok": not missing,
        "detail": ("all required strings present"
                   if not missing
                   else "missing: " + ", ".join(repr(m) for m in missing)),
    })

    # Rule 3 — plain language: no banned jargon
    used = [t for t in task.banned_terms if _find_banned(summary, t)]
    results.append({
        "rule": "plain_language",
        "ok": not used,
        "detail": ("no banned terms used"
                   if not used
                   else "banned terms used: " + ", ".join(repr(u) for u in used)),
    })

    # Rule 4 — readability: no over-long sentence
    long_sents = []
    for sent in _SENTENCE_SPLIT.split(summary.strip()):
        k = len(_words(sent))
        if k > task.max_sentence_words:
            long_sents.append((k, sent.strip()[:60]))
    results.append({
        "rule": "readability",
        "ok": not long_sents,
        "detail": (f"longest sentence is within {task.max_sentence_words} words"
                   if not long_sents
                   else "; ".join(f"{k} words: \"{s}...\"" for k, s in long_sents)),
    })

    score = sum(1 for r in results if r["ok"])
    return {
        "passed": score == len(results),
        "score": score,
        "max_score": len(results),
        "results": results,
        "report": format_report(results, score, len(results)),
    }


REPORT_HEADER = "RULE CHECK REPORT"


def format_report(results, score: int, max_score: int) -> str:
    """Render check results as text. Starts with REPORT_HEADER so the grader
    can tell whether you actually handed this to the critic model."""
    lines = [REPORT_HEADER, f"score: {score}/{max_score}"]
    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        lines.append(f"  [{mark}] {r['rule']}: {r['detail']}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 5. Part A data — the worked example
# --------------------------------------------------------------------------
STUDY_PASSAGE = """
A model that is trained for too long will eventually start to fit the noise in
its training set rather than the pattern underneath it. The symptom is easy to
see: training error keeps falling while error on held-out data starts to rise.
Regularization is the family of techniques used to push back on this. Weight
decay adds a penalty proportional to the size of the weights, which keeps any
single feature from dominating. Dropout randomly switches off units during
training, so the network cannot lean on one pathway. Early stopping simply ends
training at the point where held-out error is lowest. None of these techniques
add information; they all trade a little training accuracy for a model that
generalizes better.
""".strip()


# --------------------------------------------------------------------------
# 6. Part B data — the abstracts your agent must explain
# --------------------------------------------------------------------------
PRACTICE_TASK = SummaryTask(
    id="practice",
    title="Cold-Start Recommendation with Session Signals",
    abstract=(
        "Recommenders degrade badly for accounts with no interaction history. "
        "We propose a two-tower architecture in which the user tower is "
        "conditioned on within-session behavioural signals - dwell time, scroll "
        "depth, and query reformulations - rather than on a learned user "
        "embedding. This removes the dependence on historical interactions "
        "entirely for new accounts, at the cost of a slightly weaker "
        "personalization signal for long-tenured ones. On the ShopStream-4M "
        "click log our approach improves recall@20 for first-session users from "
        "0.121 to 0.194, a 60 percent relative gain, while leaving performance "
        "on established accounts unchanged within noise. We also report an "
        "online A/B test over three weeks confirming the offline result."
    ),
    must_include=["ShopStream-4M", "0.194"],
    banned_terms=["embedding", "two-tower", "recall", "architecture", "signal",
                  "personalization", "offline"],
)

BENCHMARK_TASKS: List[SummaryTask] = [
    SummaryTask(
        id="b1",
        title="Compressing Language Models for On-Device Question Answering",
        abstract=(
            "We ask whether a 125M-parameter encoder can match a 1.3B-parameter "
            "teacher on extractive question answering once the teacher's output "
            "distribution is transferred during training. Our recipe combines "
            "response-based distillation with an intermediate feature-matching "
            "loss, and adds an annealing schedule that lowers the weight of the "
            "soft-target term as training proceeds. On the CivicQA-2M benchmark "
            "the compressed model reaches 88.6 F1, within 1.4 points of the "
            "teacher, while running 7.9 times faster on a single mobile CPU "
            "core. Ablations show the feature-matching term accounts for most "
            "of the gain, and that the schedule matters more than the choice of "
            "temperature."
        ),
        must_include=["CivicQA-2M", "88.6"],
        banned_terms=["distillation", "teacher", "student", "logits",
                      "temperature", "F1", "parameter", "encoder", "ablation"],
    ),
    SummaryTask(
        id="b2",
        title="Federated Training of Chest Radiograph Classifiers",
        abstract=(
            "Hospitals cannot pool radiographs, which caps the size of any "
            "single training set. We report a federated protocol across eleven "
            "sites in which only gradient updates leave each institution, "
            "aggregated under secure summation with differential privacy noise "
            "calibrated to an epsilon of 3.0. The resulting classifier reaches "
            "0.921 AUROC on the ThoraxNet-11 held-out split, against 0.934 for "
            "a centrally trained model that is not privacy constrained and "
            "0.876 for the best single-site model. We find that most of the "
            "remaining gap comes from label-definition drift between sites "
            "rather than from the privacy noise itself."
        ),
        must_include=["ThoraxNet-11", "0.921"],
        banned_terms=["federated", "gradient", "differential privacy",
                      "aggregat", "epsilon", "AUROC", "classifier", "drift"],
    ),
    SummaryTask(
        id="b3",
        title="Short-Horizon Traffic Forecasting on Sparse Sensor Networks",
        abstract=(
            "Loop-detector coverage in mid-sized cities is sparse and "
            "irregular, which defeats grid-based forecasters. We treat the road "
            "network as a graph and learn diffusion kernels over it, so that a "
            "road segment with no sensor inherits an estimate from its "
            "neighbours along the direction of travel. Trained on the "
            "MetroFlow-18 corpus, the model lowers fifteen-minute mean absolute "
            "error to 3.42 vehicles per minute, compared with 4.81 for a "
            "recurrent baseline and 5.60 for historical averaging. The gain is "
            "concentrated on segments more than two hops from the nearest "
            "sensor, which is precisely where operators currently have no "
            "information at all."
        ),
        must_include=["MetroFlow-18", "3.42"],
        banned_terms=["graph", "diffusion", "kernel", "recurrent", "baseline",
                      "corpus", "hop", "forecaster"],
    ),
    SummaryTask(
        id="b4",
        title="Speech Recognition for Languages With Under Ten Hours of Audio",
        abstract=(
            "Most speech systems assume thousands of hours of transcribed "
            "audio. We study the opposite regime, fine-tuning a multilingual "
            "self-supervised backbone on between two and ten hours of "
            "transcribed speech for nine languages of the Sahel. Adding a "
            "character-level language model trained on scraped text, which is "
            "far cheaper to obtain than transcripts, cuts word error rate on "
            "the SahelVoice-9 test set from 41.7 to 28.3 percent. Error "
            "analysis shows the remaining failures are concentrated in code-"
            "switched utterances, which make up a fifth of the test set but "
            "over half of the residual errors."
        ),
        must_include=["SahelVoice-9", "28.3"],
        banned_terms=["fine-tun", "self-supervised", "backbone", "multilingual",
                      "word error rate", "utterance", "corpus", "transcript"],
    ),
    SummaryTask(
        id="b5",
        title="Learned Dispatch Policies for Warehouse Robot Fleets",
        abstract=(
            "Assigning picking tasks to a fleet of mobile robots is usually "
            "solved greedily, which produces congestion at aisle entrances "
            "under heavy load. We learn a dispatch policy with proximal policy "
            "optimization in a simulator calibrated against a real facility, "
            "rewarding throughput while penalising time spent stationary. In "
            "the DepotSim-500 evaluation the learned policy raises completed "
            "picks per hour from 1,840 to 2,310 at peak load, and its advantage "
            "disappears at light load, where the greedy rule is already near "
            "optimal. Deployment remains limited by the fidelity of the "
            "simulator's model of human pickers sharing the floor."
        ),
        must_include=["DepotSim-500", "2,310"],
        banned_terms=["policy", "proximal", "reward", "simulator", "greedy",
                      "throughput", "dispatch", "optimal"],
    ),
]


def get_task(task_id: str) -> SummaryTask:
    """Look up a benchmark task by id ('b1' ... 'b5', or 'practice')."""
    if task_id == "practice":
        return PRACTICE_TASK
    for t in BENCHMARK_TASKS:
        if t.id == task_id:
            return t
    raise KeyError(f"no such task: {task_id!r}")
