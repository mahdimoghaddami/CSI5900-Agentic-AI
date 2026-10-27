"""Offline public contract tests. Tests do not assess live-model writing quality."""
import copy
import json
import math
from lab_tools import ScriptedClient, PLAN_FORMAT, demo_plan


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def run_checks(label, cases, verbose=True):
    earned, feedback = 0, []
    for name, points, case in cases:
        try:
            case()
            earned += points
            feedback.append({"check": name, "earned": points, "possible": points, "message": "PASS"})
        except Exception as exc:
            feedback.append({"check": name, "earned": 0, "possible": points,
                             "message": f"{type(exc).__name__}: {exc}"})
    possible = sum(p for _, p, _ in cases)
    if verbose:
        print(f"{label}: {earned}/{possible}")
        for row in feedback:
            print(f"  {row['earned']}/{row['possible']} {row['check']}: {row['message']}")
    return {"earned": earned, "possible": possible, "checks": feedback}


def test_plan_brief(fn, verbose=True):
    def call(topic="Topic-47", model="test:planner-47", steps=None):
        steps = steps if steps is not None else demo_plan(topic)
        client = ScriptedClient([json.dumps({"steps": steps})])
        result = fn(topic, client=client, model=model)
        return client, result, steps

    def settings():
        c, _, _ = call()
        check(c.n_calls == 1, "Make exactly one model call.")
        check(c.requests[0].get("model") == "test:planner-47", "Use the supplied model.")

    def prompt():
        c, _, _ = call(topic="Unique seed exchange question")
        messages = c.requests[0].get("messages", [])
        check(any(m.get("role") == "user" and isinstance(m.get("content"), str)
                  and "Unique seed exchange question" in m["content"] for m in messages),
              "Send the supplied topic in the user prompt.")

    def protocol():
        c, _, _ = call()
        req = c.requests[0]
        check(req.get("temperature") == 0.2, "Use temperature 0.2.")
        check(req.get("response_format") == PLAN_FORMAT, "Keep the provided response format.")

    def returned():
        for marker in ["oak-31", "elm-58"]:
            steps = [f"{tag} {marker} task {i}" for i, tag in enumerate(["[SEARCH]", "[VALIDATE]", "[WRITE]", "[EDIT]"])]
            _, result, expected = call(steps=steps)
            check(result == expected, "Return this response's parsed plan, not a fixed example.")

    def invalid():
        for steps in [["[SEARCH] only"], ["[WRITE] too early"] * 4]:
            try:
                call(steps=steps)
            except ValueError:
                continue
            raise AssertionError("Keep the supplied parser's plan validation.")
    return run_checks("Exercise 1", [("one call and supplied model", 5, settings),
        ("topic reaches prompt", 5, prompt), ("temperature and JSON format", 5, protocol),
        ("response-dependent plan", 5, returned), ("invalid plans rejected", 5, invalid)], verbose)


def test_evaluate_sources(fn, verbose=True):
    def expect(urls, domains, threshold, ids, passed):
        records = [{"id": f"T-{i}", "url": url, "snippet": f"evidence {i}"} for i, url in enumerate(urls)]
        before = copy.deepcopy(records)
        domain_before = set(domains)
        out = fn(records, domains, threshold)
        total, approved = len(records), len(ids)
        check(isinstance(out, dict), "Return the required dictionary.")
        check(out.get("total") == total and out.get("approved") == approved, "Count all records and approved records correctly.")
        check(out.get("approved_ids") == [f"T-{i}" for i in ids], "Return approved IDs in input order.")
        check(isinstance(out.get("ratio"), (int, float)) and math.isclose(out["ratio"], approved / total if total else 0), "Compute approved / total, or 0.0 for no records.")
        check(out.get("passed") is passed, "Return a Boolean using a nonempty set and the inclusive threshold.")
        check(records == before and domains == domain_before, "Do not modify inputs.")

    return run_checks("Exercise 2", [
        ("exact and subdomain matches", 5, lambda: expect(["https://archive.example/a", "https://docs.archive.example/b", "https://else.example/c"], {"archive.example"}, 0.6, [0, 1], True)),
        ("lookalike hosts rejected", 5, lambda: expect(["https://archive.example.evil.example/a", "https://notarchive.example/b", "https://else.example/archive.example"], {"archive.example"}, 0.4, [], False)),
        ("malformed URLs stay in denominator", 5, lambda: expect(["https://archive.example/a", "invalid", "", "ftp://archive.example/a"], {"archive.example"}, 0.5, [0], False)),
        ("empty input fails even at zero", 5, lambda: expect([], {"archive.example"}, 0, [], False)),
        ("inclusive threshold boundary", 5, lambda: expect(["https://archive.example/a", "https://other.example/b"], {"archive.example"}, 0.5, [0], True)),
        ("changing domain policy", 5, lambda: expect(["https://archive.example/a", "https://other.example/b"], {"other.example"}, 1, [1], False)),
        ("URL normalization and userinfo", 5, lambda: expect(["HTTPS://WWW.ARCHIVE.EXAMPLE:443/a", "https://archive.example@evil.example/a", "https://archive.example./b"], {"archive.example"}, 0.6, [0, 2], True)),
        ("empty policy and input preservation", 5, lambda: expect(["https://archive.example/a"], set(), 0.1, [], False)),
    ], verbose)


def pipeline_fixture():
    events = []
    records = [{"id": "K-72", "url": "https://trusted.example/a", "snippet": "variant-alpha"},
               {"id": "K-19", "url": "https://trusted.example.bad.example/b", "snippet": "excluded-beta"}]
    def search(topic, task):
        events.append(("search", topic, task))
        return copy.deepcopy(records)
    def write(topic, task, approved):
        events.append(("write", topic, task, copy.deepcopy(approved)))
        return "draft-token-91"
    def edit(topic, task, draft, approved):
        events.append(("edit", topic, task, draft, copy.deepcopy(approved)))
        return "edited-token-38"
    return records, events, {"search": search, "write": write, "edit": edit}


def test_execute_plan(fn, verbose=True):
    def run(threshold=0.5, domains=None, empty=False):
        records, events, workers = pipeline_fixture()
        if empty:
            records.clear()
        plan = demo_plan("topic-q8")
        before = copy.deepcopy(plan)
        out = fn(plan, "topic-q8", {"trusted.example"} if domains is None else domains,
                 min_ratio=threshold, workers=workers)
        check(plan == before, "Do not modify the plan.")
        return records, events, plan, out

    def search():
        records, events, plan, out = run()
        check(events[0] == ("search", "topic-q8", plan[0].split(" ", 1)[1]), "Pass the supplied topic and search task.")
        check(out["records"] == records, "Retain this run's retrieved records.")

    def gate():
        for threshold, policy in [(0.75, {"trusted.example"}), (0.5, {"absent.example"})]:
            _, events, _, out = run(threshold, policy)
            check(out["status"] == "blocked" and out["report"] is None, "Use the supplied domain policy/threshold and block failure.")
            check([e[0] for e in events] == ["search"], "Never call writer/editor after failed validation.")

    def evidence():
        records, events, plan, out = run()
        check(events[1] == ("write", "topic-q8", plan[2].split(" ", 1)[1], [records[0]]), "Pass only current approved records to writer.")
        check(out["evaluation"]["approved_ids"] == ["K-72"], "Evaluate the actual retrieved records.")

    def handoff():
        records, events, plan, out = run()
        check(events[2] == ("edit", "topic-q8", plan[3].split(" ", 1)[1], "draft-token-91", [records[0]]), "Pass the writer's actual draft and approved records to editor.")
        check(out["report"] == "edited-token-38", "Return the editor's actual output.")

    def history():
        records, events, plan, out = run()
        check(out["status"] == "complete", "Mark a successful pipeline complete.")
        check([e[0] for e in events] == ["search", "write", "edit"], "Call each worker exactly once and in order.")
        check([h["agent"] for h in out["history"]] == ["search", "validate", "write", "edit"], "Record all four stages in order.")
        check([h["step"] for h in out["history"]] == plan, "Keep original plan steps in history.")
        check([h["output"] for h in out["history"]] == [records, out["evaluation"], "draft-token-91", "edited-token-38"], "Record actual stage outputs.")

    def empty():
        _, events, _, out = run(0, empty=True)
        check(out["status"] == "blocked" and len(out["history"]) == 2, "An empty retrieval must block even at threshold zero.")
        check(len(events) == 1, "No writing on empty evidence.")

    def bad_plan():
        _, events, workers = pipeline_fixture()
        try:
            fn(["[WRITE] skip validation"], "topic", {"trusted.example"}, workers=workers)
        except ValueError:
            check(not events, "Reject invalid plans before invoking workers.")
            return
        raise AssertionError("Keep the supplied plan validation.")
    return run_checks("Exercise 3", [("actual retrieval", 5, search), ("failed gate blocks workers", 5, gate),
        ("approved evidence reaches writer", 5, evidence), ("draft reaches editor", 5, handoff),
        ("ordered trace and outputs", 5, history), ("empty retrieval blocks", 5, empty),
        ("bad plan rejected before work", 5, bad_plan)], verbose)


def run_all_tests(plan_brief, evaluate_sources, execute_plan, verbose=True):
    results = [test_plan_brief(plan_brief, verbose), test_evaluate_sources(evaluate_sources, verbose),
               test_execute_plan(execute_plan, verbose)]
    earned = sum(r["earned"] for r in results)
    if verbose:
        print(f"TOTAL: {earned}/100")
    return {"earned": earned, "possible": 100, "exercises": results}
