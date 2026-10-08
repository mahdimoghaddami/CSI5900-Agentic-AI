"""Provided tools for Graded Lab 2. All records are fictional teaching data."""
import copy
import json
import os
import re
import time
from pathlib import Path
from types import SimpleNamespace

def configured_model():
    """AISuite model identifier; accept existing bare Gemini model settings."""
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    return model if model.startswith("openai:") else "openai:" + model


MODEL = configured_model()
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
REVISION_FORMAT = {
    "type": "json_schema",
    "json_schema": {"name": "evidence_review", "strict": True, "schema": {
        "type": "object", "properties": {
            "reflection": {"type": "string"}, "revised_report": {"type": "string"}},
        "required": ["reflection", "revised_report"], "additionalProperties": False}},
}

# These are invented, matched-condition measurements, not published results.
STUDIES = [
    {"source_id": "ST-21", "title": "Cedar: compact campus sound classifier",
     "application": "campus sound", "model_id": "cedar",
     "summary": "A small integer model for classifying fan, speech, and traffic sounds.",
     "limitation": "Only indoor recordings from one building were used."},
    {"source_id": "ST-22", "title": "Birch: higher accuracy campus sound classifier",
     "application": "campus sound", "model_id": "birch",
     "summary": "A wider model intended to reduce confusion between speech and traffic.",
     "limitation": "No outdoor evaluation; memory use may limit deployment."},
    {"source_id": "ST-23", "title": "Willow: low memory campus sound classifier",
     "application": "campus sound", "model_id": "willow",
     "summary": "An aggressively compressed sound classifier for small devices.",
     "limitation": "Compression reduces accuracy on quiet speech."},
]
MEASUREMENTS = {
    "cedar": {"source_id": "BM-21", "model_id": "cedar", "board": "CampusBoard-A",
              "accuracy_pct": 91.2, "latency_ms": 18, "peak_ram_kb": 112,
              "conditions": "Same 600-clip held-out test, 1-second inputs, 80 MHz CPU."},
    "birch": {"source_id": "BM-22", "model_id": "birch", "board": "CampusBoard-A",
              "accuracy_pct": 94.1, "latency_ms": 24, "peak_ram_kb": 176,
              "conditions": "Same 600-clip held-out test, 1-second inputs, 80 MHz CPU."},
    "willow": {"source_id": "BM-23", "model_id": "willow", "board": "CampusBoard-A",
               "accuracy_pct": 88.4, "latency_ms": 12, "peak_ram_kb": 80,
               "conditions": "Same 600-clip held-out test, 1-second inputs, 80 MHz CPU."},
}

BRIEF = (
    "Recommend one model for a campus sound sensor on CampusBoard-A. "
    "Compare all three candidates. Requirements: accuracy at least 90%, "
    "latency at most 25 ms, and peak RAM at most 128 KB. "
    "Use search_studies to find the candidates, then get_measurements for each. "
    "Use only the returned evidence; cite source IDs in square brackets, "
    "include the relevant numbers and one limitation. If none qualify, say so. "
    "Keep the recommendation under 220 words. These are fictional classroom data."
)


def search_studies(query: str):
    """Simple local keyword search; returns summaries, not benchmark numbers."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a nonempty string")
    terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    hits = []
    for item in STUDIES:
        words = set(re.findall(r"[a-z0-9]+", json.dumps(item).lower()))
        if terms & words:
            hits.append(copy.deepcopy(item))
    return hits


def get_measurements(model_id: str):
    """Look up matched-condition measurements by an ID returned by search."""
    if model_id not in MEASUREMENTS:
        raise ValueError(f"Unknown model_id: {model_id}")
    return copy.deepcopy(MEASUREMENTS[model_id])


def tool_schema(name, description, argument, argument_description):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": {
            argument: {"type": "string", "description": argument_description}},
            "required": [argument], "additionalProperties": False}}}


TOOLS = [
    tool_schema("search_studies", "Search fictional study summaries by keywords; use campus sound to find all candidates.",
                "query", "Keywords such as campus sound"),
    tool_schema("get_measurements", "Get accuracy, latency, and peak RAM on CampusBoard-A for a candidate.",
                "model_id", "A model_id returned by search_studies"),
]
TOOL_MAPPING = {"search_studies": search_studies, "get_measurements": get_measurements}


def execute_tool(call, mapping):
    """Provided error handling: model requests select only registered functions."""
    try:
        args = json.loads(call.function.arguments)
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be a JSON object")
        return mapping[call.function.name](**args)
    except (KeyError, ValueError, TypeError) as exc:
        return {"error": str(exc)}


def message_dict(message):
    """Keep complete assistant messages, including provider tool-call metadata."""
    return message.model_dump(exclude_none=True)


def evidence_from_messages(messages):
    """Keep tool names and decoded results. Do not treat assistant prose as evidence."""
    return [{"tool": m.get("name", ""), "result": json.loads(m["content"])}
            for m in messages if m.get("role") == "tool"]


def parse_revision(text):
    """Accept plain/fenced JSON, then enforce the two-field output contract."""
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)[:-3].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Expected JSON with reflection and revised_report; rerun or clarify your prompt.") from exc
    if not isinstance(data, dict) or any(
        not isinstance(data.get(k), str) or not data[k].strip()
        for k in ("reflection", "revised_report")
    ):
        raise ValueError("reflection and revised_report must both be nonempty strings")
    return {k: data[k].strip() for k in ("reflection", "revised_report")}


class PacedClient:
    """A configurable pause reduces bursts; it does not guarantee quota availability."""
    def __init__(self, inner, seconds):
        self.inner, self.seconds, self.last, self.n_calls = inner, seconds, 0.0, 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        time.sleep(max(0, self.last + self.seconds - time.monotonic()))
        self.last = time.monotonic()
        self.n_calls += 1
        return self.inner.chat.completions.create(**kwargs)


def get_client():
    from dotenv import load_dotenv
    import aisuite as ai
    load_dotenv(Path(__file__).with_name(".env"))
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Set GEMINI_API_KEY in .env or use RUN_LIVE=False. See README.md.")
    return PacedClient(ai.Client({"openai": {"api_key": key, "base_url": BASE_URL,
                                            "timeout": 60, "max_retries": 0}}),
                       float(os.getenv("MIN_CALL_INTERVAL", "5")))



class FakeMessage:
    """Small stand-in for an SDK message; used only for offline teaching/tests."""
    def __init__(self, content=None, calls=None):
        self.content, self.tool_calls = content, calls or []

    def model_dump(self, **kwargs):
        out = {"role": "assistant"}
        if self.content is not None:
            out["content"] = self.content
        if self.tool_calls:
            out["tool_calls"] = [{"id": c.id, "type": "function", "function": {
                "name": c.function.name, "arguments": c.function.arguments},
                "extra_content": {"google": {"thought_signature": "offline-test-metadata"}}}
                for c in self.tool_calls]
        return out


def fake_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(
        name=name, arguments=json.dumps(arguments) if not isinstance(arguments, str) else arguments))


class ScriptedClient:
    """Fixed replies, NOT an LLM. Does not decide tools or evaluate your prompts."""
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        self.n_calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        self.n_calls += 1
        if not self.replies:
            raise AssertionError("Unexpected extra model call")
        msg = self.replies.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def room_capacity(room):
    """Worked example: fictional rooms, not a live campus booking service."""
    rooms = {"Maple": 6, "Oak": 10}
    if room not in rooms:
        raise ValueError("Unknown room")
    return {"source_id": "ROOM-1", "room": room, "capacity": rooms[room]}


ROOM_TOOLS = [tool_schema("room_capacity", "Look up a fictional room's seat capacity.",
                          "room", "Maple or Oak")]


def example_client():
    return ScriptedClient([
        FakeMessage(calls=[fake_call("room_capacity", {"room": "Maple"})]),
        FakeMessage("Maple has 6 seats, so it fits a group of 5 [ROOM-1]. Availability is unknown."),
        FakeMessage(json.dumps({"reflection": "Strengths: cites capacity. Limitations: no availability data. "
            "Suggestions: keep that uncertainty. Opportunities: add a booking tool later.",
            "revised_report": "Maple can seat 5 people because its capacity is 6 [ROOM-1]. "
            "This does not confirm that the room is available."})),
        FakeMessage('<html><body><h1>Study room advice</h1><p>Maple has 6 seats, enough for 5 people '
                    '[ROOM-1]. Availability is unknown.</p></body></html>'),
    ])


def inspect_trace(messages):
    for i, m in enumerate(messages):
        if m.get("tool_calls"):
            print(i, "assistant requests:", [c["function"]["name"] for c in m["tool_calls"]])
        elif m["role"] == "tool":
            print(i, "tool result:", m.get("name"), "id=", m.get("tool_call_id"))
        else:
            print(i, m["role"], str(m.get("content", ""))[:90])


def show_html(html_text):
    """Preview in a sandboxed frame; no scripts, forms, or external resources."""
    import html
    from IPython.display import HTML, display
    clean = re.sub(r"^```(?:html)?\s*|\s*```$", "", html_text.strip(), flags=re.I)
    policy = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
    display(HTML('<iframe sandbox="" style="width:100%;height:460px;border:1px solid #ccc" '
                 'srcdoc="' + html.escape(policy + clean, quote=True) + '"></iframe>'))
