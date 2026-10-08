"""Offline contract checks. Instructor reruns these original tests for grading."""
import json
from lab_tools import FakeMessage, ScriptedClient, fake_call, TOOLS, get_measurements, search_studies


def _check(condition, message):
    if not condition:
        raise AssertionError(message)


def _prompt(request):
    return "\n".join(m.get("content", "") or "" for m in request["messages"])


def _run(label, cases, verbose=True):
    score, total = 0, sum(points for _, points, _ in cases)
    failures = []
    for title, points, check in cases:
        try:
            check()
            score += points
            if verbose:
                print(f"PASS {title}: {points}/{points}")
        except Exception as exc:
            failures.append(title)
            if verbose:
                print(f"FAIL {title}: 0/{points} — {type(exc).__name__}: {exc}")
    if verbose:
        print(f"{label}: {score}/{total}\n")
    return {"score": score, "total": total, "failed": failures}


def _check_request(req, brief, model):
    _check(req.get("model") == model, "Pass the supplied model argument.")
    _check(req.get("tools") == TOOLS, "Pass TOOLS to the model.")
    _check(req.get("tool_choice") == "auto", 'Use tool_choice="auto".')
    _check(any(m.get("role") == "user" and m.get("content") == brief for m in req["messages"]),
           "The supplied brief must reach the model as a user message.")


def test_build_recommendation(fn, verbose=True):
    def basic():
        for key in ("cedar", "willow"):
            cid, brief = "lookup-" + key, "Compare " + key + " for test deployment."
            client = ScriptedClient([FakeMessage(calls=[fake_call("get_measurements", {"model_id": key}, cid)]),
                                     FakeMessage("  Result for " + key + "  ")])
            out = fn(brief, client=client, model="test-model")
            _check(client.n_calls == 2, "Send tool results back in a second model call.")
            _check_request(client.requests[0], brief, "test-model")
            _check_request(client.requests[1], brief, "test-model")
            hist = client.requests[1]["messages"]
            _check(hist[-2].get("role") == "assistant" and hist[-2].get("tool_calls"),
                   "Append the assistant's tool request before its result.")
            result = hist[-1]
            _check(result.get("role") == "tool", 'Tool result role must be "tool".')
            _check(result.get("tool_call_id") == cid, "Use the current call.id.")
            _check(result.get("name") == "get_measurements", "Use the requested tool name.")
            _check(isinstance(result.get("content"), str), "Serialize result with json.dumps.")
            _check(json.loads(result["content"]) == get_measurements(key), "Send the actual tool result.")
            _check(out["report"] == "Result for " + key, "Return final model text, stripped.")
            _check(out["messages"][:-1] == hist, "Return full history with its final assistant reply.")

    def multiple():
        calls = [fake_call("get_measurements", {"model_id": x}, "parallel-" + x) for x in ("birch", "cedar")]
        client = ScriptedClient([FakeMessage(calls=calls), FakeMessage("Both received.")])
        out = fn("Compare two candidates", client=client, model="parallel-model")
        replies = [m for m in client.requests[-1]["messages"] if m["role"] == "tool"]
        _check(len(replies) == 2, "Handle all tool calls in one assistant reply.")
        for reply, key in zip(replies, ("birch", "cedar")):
            _check(reply.get("tool_call_id") == "parallel-" + key, "Do not reuse another call's ID.")
            _check(json.loads(reply["content"]) == get_measurements(key), "Pair each ID with its own result.")
        request = out["messages"][2]
        _check(request["tool_calls"][0].get("extra_content"), "Keep message_dict(msg) to preserve metadata.")

    def sequential():
        client = ScriptedClient([
            FakeMessage(calls=[fake_call("search_studies", {"query": "campus sound"}, "search-a")]),
            FakeMessage(calls=[fake_call("get_measurements", {"model_id": "birch"}, "measure-b")]),
            FakeMessage("Sequential result.")])
        out = fn("Find candidates then inspect one", client=client, model="sequence-model")
        _check(client.n_calls == 3, "Continue after a second tool-requesting reply.")
        replies = [m for m in out["messages"] if m["role"] == "tool"]
        _check(json.loads(replies[0]["content"]) == search_studies("campus sound"), "Send the search results.")
        _check(json.loads(replies[1]["content"]) == get_measurements("birch"), "Send the later lookup result.")
        _check(out["report"] == "Sequential result.", "Return the final answer, not an intermediate result.")

    def errors():
        bad = [fake_call("not_registered", {}, "bad-name"),
               fake_call("get_measurements", "{broken json", "bad-json"),
               fake_call("get_measurements", {"model_id": "missing"}, "bad-id")]
        client = ScriptedClient([FakeMessage(calls=bad), FakeMessage("Evidence unavailable.")])
        out = fn("Handle lookup errors", client=client, model="error-model")
        results = [m for m in out["messages"] if m["role"] == "tool"]
        _check(len(results) == 3, "Return one tool reply for every failed request too.")
        for m, c in zip(results, bad):
            _check(m.get("tool_call_id") == c.id and "error" in json.loads(m["content"]),
                   "Serialize the provided error result with the right call ID.")

    def stopping():
        client = ScriptedClient([FakeMessage("  Direct answer.  ")])
        out = fn("A question requiring no tools", client=client, model="stop-model")
        _check_request(client.requests[0], "A question requiring no tools", "stop-model")
        _check(client.n_calls == 1 and out["report"] == "Direct answer.", "Stop on a final text reply.")
        for budget in (1, 2):
            loop = ScriptedClient([FakeMessage(calls=[fake_call("search_studies", {"query": "campus"}, str(i))])
                                   for i in range(budget + 1)])
            try:
                fn("Keep looking", client=loop, max_turns=budget)
            except RuntimeError as exc:
                _check("max_turns" in str(exc), "Use the provided clear turn-limit error.")
            else:
                raise AssertionError("Do not return a fabricated final answer when the budget is exhausted.")
            _check(loop.n_calls == budget, "Respect the supplied max_turns budget.")

    return _run("Exercise 1", [("request and one tool reply", 8, basic),
                               ("multiple calls in one reply", 8, multiple),
                               ("dependent tool turns", 8, sequential),
                               ("error-result messages", 8, errors),
                               ("final answer and turn limit", 8, stopping)], verbose)


def _revision_case(fn, variant=1):
    # New evidence values, not the assignment's worked sample.
    record = {"source_id": f"CHECK-{variant}", "accuracy_pct": 90 + variant,
              "peak_ram_kb": 111 + variant, "latency_ms": 13 + variant,
              "note": f"new measurement batch {variant}"}
    messages = [{"role": "assistant", "content": "Preliminary prose is not a tool result."},
                {"role": "tool", "tool_call_id": f"t-{variant}", "name": "get_measurements",
                 "content": json.dumps(record)}]
    report, brief = f"Draft proposal {variant}: check this claim.", f"Budget {150 + variant} KB, compare carefully."
    data = {"reflection": f"Distinct critique {variant}.", "revised_report": f"Distinct revision {variant}."}
    client = ScriptedClient([FakeMessage(json.dumps(data))])
    out = fn(report, messages, brief, client=client, model=f"review-{variant}", temperature=0.17)
    _check(all(isinstance(m.get("content"), str) and m["content"].strip()
               for m in client.requests[0]["messages"]), "Replace the prompt placeholder with a nonempty string.")
    return client, out, data, report, brief, record


def test_revise_with_evidence(fn, verbose=True):
    def parameters():
        c, *_ = _revision_case(fn)
        _check(c.n_calls == 1, "Make exactly one model call.")
        _check(c.requests[0].get("model") == "review-1", "Pass the supplied model.")
        _check(c.requests[0].get("temperature") == 0.17, "Pass the supplied temperature.")
    def inputs():
        c, _, _, report, brief, _ = _revision_case(fn)
        p = _prompt(c.requests[0])
        _check(report in p and brief in p, "Include both the report and deployment brief in the prompt.")
    def evidence():
        for variant in (2, 7):
            c, _, _, _, _, record = _revision_case(fn, variant)
            p = _prompt(c.requests[0])
            for key, value in record.items():
                _check(str(key) in p and str(value) in p,
                       f"Include the actual tool evidence from this call; missing {key}: {value}.")
    def json_contract():
        c, *_ = _revision_case(fn)
        p = _prompt(c.requests[0]).lower()
        _check(all(x in p for x in ("json", "reflection", "revised_report")),
               "Ask for JSON with reflection and revised_report fields.")
    def return_value():
        for variant in (3, 8):
            _, out, data, *_ = _revision_case(fn, variant)
            _check(out == data, "Return the model's two distinct parsed fields; do not duplicate the full reply.")
    return _run("Exercise 2", [("one call and supplied settings", 7, parameters),
                               ("report and brief transfer", 7, inputs),
                               ("current tool evidence transfer", 7, evidence),
                               ("JSON output request", 7, json_contract),
                               ("distinct returned fields", 7, return_value)], verbose)


def test_format_recommendation(fn, verbose=True):
    def run_case(which):
        report = f"Recommendation {which}: 93.{which}% accuracy [EVID-{which}]; outdoor performance unknown."
        html = f"<html><body><h1>Result {which}</h1><p>{report}</p></body></html>"
        client = ScriptedClient([FakeMessage(" \n" + html + "\n ")])
        out = fn(report, client=client, model="format-test", temperature=0.13)
        return client, out, html, report
    def calls():
        c, *_ = run_case(1)
        _check(c.n_calls == 1, "Make one model call.")
    def settings():
        c, *_ = run_case(2)
        _check(c.requests[0].get("model") == "format-test" and c.requests[0].get("temperature") == 0.13,
               "Use supplied model and temperature.")
    def report_input():
        for i in (3, 6):
            c, _, _, report = run_case(i)
            _check(report in _prompt(c.requests[0]), "Include this function's report in the prompt.")
    def format_request():
        c, *_ = run_case(4)
        _check("html" in _prompt(c.requests[0]).lower(), "Ask for HTML output.")
    def reply():
        for i in (5, 9):
            _, out, html, _ = run_case(i)
            _check(out == html, "Return the model reply with only outer whitespace stripped.")
    return _run("Exercise 3", [("one model call", 5, calls), ("supplied settings", 5, settings),
                               ("report transfer", 5, report_input), ("HTML output request", 5, format_request),
                               ("model reply returned", 5, reply)], verbose)


def run_all_tests(build, revise, format_html, verbose=True):
    results = [test_build_recommendation(build, verbose), test_revise_with_evidence(revise, verbose),
               test_format_recommendation(format_html, verbose)]
    total = sum(x["score"] for x in results)
    if verbose:
        print(f"TOTAL: {total}/100 (offline contract checks)")
    return {"score": total, "total": 100, "exercises": results}
