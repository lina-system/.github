import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import issue_labels as il

DONE = "## Done when\n\n- [ ] The checked behaviour.\n"


def body(context, done=DONE, summary="A change."):
    return f"## Summary\n\n{summary}\n\n{done}\n## Context\n\n{context}\n"


def issue(title, text, labels=(), state="open", sub=0):
    return {
        "number": 1,
        "title": title,
        "body": text,
        "state": state,
        "labels": [{"name": name} for name in labels],
        "sub_issues_summary": {"total": sub},
    }


JUDGE_CASES = [
    # (case, title, body, size, runner)
    ("lina#80 docs(design)", "docs(design): carry the Hermes operating patterns into the fork",
     body("- Depends on: none\n- Size: M\n- Runner: omo",
          done="## Done when\n\n- [ ] The note exists.\n- [ ] No dates, machine names or secrets; the grep is in the PR.\n"),
     "M", "omo"),
    ("lina#79 fix S", "fix(update): stop update from offering the official Hermes repository as upstream",
     body("- Depends on: none\n- Size: S\n- Runner: grok-cursor"), "S", "dsh"),
    ("lina#78 fix S", "fix(lina_helper): keep endpoint-based driver resolution during recovery",
     body("- Depends on: none\n- Size: S\n- Runner: grok-cursor"), "S", "dsh"),
    ("lina#77 fix S", "fix(workspace): load Desk instructions for nested task workspaces",
     body("- Depends on: none\n- Size: S\n- Runner: grok-cursor"), "S", "dsh"),
    ("lina-app#2 scaffold", "chore(repo): scaffold the web client with alpha versioning, CI and the generated API client",
     body("- Depends on: none. Size: M (a few days)."), "L", "omo"),
    ("lina#61 ci(merge) M", "ci(merge): enforce the delivery procedure with required checks and write it down",
     body("- Part of #26. Depends on: none. Size: M."), "M", "omo"),
    ("lina#9 build(deps) S", "build(deps): drop the extras of deleted features",
     body("- Part of #4. Depends on: #8. Size: S (about a day).",
          done="## Done when\n\n- `pyproject.toml` and `uv.lock` are trimmed, and the installed size is recorded.\n"),
     "S", "dsh"),
    ("Runner line with reason wins", "feat(home): x",
     body("- Size: S\n- Runner: omo — needs the phone build"), "S", "omo"),
    ("Runner line with hyphen reason", "feat(store): x",
     body("- Size: M\n- Runner: grok-cursor - schema is already decided"), "M", "grok-cursor"),
    ("research prefix", "research(os): pick the base image", body("- Size: S"), "S", "omo"),
    ("measurement in body", "test(memory): x", body("- Size: S", summary="Measure the cache hit rate."), "S", "omo"),
    ("size L", "feat(memory): x", body("- Size: L (a week or more)."), "L", "omo"),
    ("risky scope at S", "feat(install): x", body("- Size: S"), "S", "omo"),
    ("risky scope in a list", "fix(api, auth): x", body("- Size: S"), "S", "omo"),
    ("credentials in body", "fix(home): x", body("- Size: S", summary="Move the API keys into the keychain."), "S", "omo"),
    ("negated secrets is not risky", "fix(home): x", body("- Size: S", summary="Logs carry no secrets."), "S", "dsh"),
    ("far negation still counts as risky (lina#59)", "fix(memory): x",
     body("- Size: S", summary="The wizard does not catch this error, so setup aborts before credentials are set."),
     "S", "omo"),
    ("work devices (lina#37)", "chore(work): x",
     body("- Size: M", summary="Every work device is listed, and a real task completes on each."), "M", "omo"),
    ("no Done when", "fix(home): x", "## Summary\n\nA change.\n\n## Context\n\n- Size: S\n", "S", "omo"),
    ("empty Done when", "fix(home): x", body("- Size: S", done="## Done when\n\n- [ ]\n"), "S", "omo"),
    ("open question", "feat(home): x", body("- Size: M", summary="Open question: which card order."), "M", "omo"),
    ("docs only", "docs(readme): fix the install steps", body("- Size: S"), "S", "agy"),
    ("M code", "feat(home): x", body("- Size: M (a few days)."), "M", "grok-cursor"),
    ("no size", "feat(home): x", body("- Depends on: none"), None, None),
    ("empty Size and Runner fields", "feat(home): x", body("- Size:\n- Runner:"), None, None),
]


@pytest.mark.parametrize(("case", "title", "text", "size", "runner"), JUDGE_CASES, ids=[c[0] for c in JUDGE_CASES])
def test_judge(case, title, text, size, runner):
    judgment = il.judge(title, text)
    assert (judgment.size, judgment.runner) == (size, runner), judgment.reason


LABEL_CASES = [
    # (case, issue, add, remove, old_runners)
    ("wrong runner is replaced",
     issue("fix(update): x", body("- Size: S"), labels=["bug", "grok-cursor", "size/S", "ready"]),
     {"dsh"}, {"grok-cursor", "ready"}, ["grok-cursor"]),
    ("fresh issue gets labels without a comment",
     issue("fix(update): x", body("- Size: S")), {"bug", "size/S", "dsh"}, set(), []),
    ("size label follows the judgment",
     issue("chore(repo): scaffold the app", body("- Size: M"), labels=["maintenance", "size/M", "grok-cursor"]),
     {"size/L", "omo"}, {"size/M", "grok-cursor"}, ["grok-cursor"]),
    ("needs-routing drops the runner",
     issue("feat(home): x", body("- Depends on: none"), labels=["enhancement", "grok-cursor"]),
     {"needs-routing"}, {"grok-cursor"}, ["grok-cursor"]),
    ("routed later clears needs-routing",
     issue("feat(home): x", body("- Size: M"), labels=["enhancement", "needs-routing"]),
     {"size/M", "grok-cursor"}, {"needs-routing"}, []),
    ("matching labels change nothing",
     issue("fix(update): x", body("- Size: S"), labels=["bug", "size/S", "dsh"]), set(), set(), []),
    ("parent keeps no runner",
     issue("chore(parity): x", body("- Size: M"), labels=["maintenance", "dsh", "blocked"], sub=18),
     set(), {"dsh", "blocked"}, []),
    ("Roadmap is left alone", issue("Roadmap", "Order of work.", labels=[]), set(), set(), []),
    ("closed issue drops only retired and needs-routing",
     issue("fix(update): x", body("- Size: M"), labels=["dsh", "ready", "needs-routing"], state="closed"),
     set(), {"ready", "needs-routing"}, []),
    ("existing kind wins",
     issue("fix(update): x", body("- Size: S"), labels=["enhancement", "size/S", "dsh"]), set(), set(), []),
]


@pytest.mark.parametrize(("case", "item", "add", "remove", "old"), LABEL_CASES, ids=[c[0] for c in LABEL_CASES])
def test_plan_issue(case, item, add, remove, old):
    plan = il.plan_issue(item)
    assert (plan.add, plan.remove, plan.old_runners) == (add, remove, old)


def test_one_comment_is_created_then_edited():
    plan = il.plan_issue(issue("fix(update): x", body("- Size: S"), labels=["grok-cursor"]))
    action, text = il.plan_comment(None, plan)
    assert action == "create"
    assert il.MARKER in text and "`dsh`" in text and "Runner:" in text
    assert il.plan_comment({"id": 7, "body": text}, plan) == (None, None)
    later = il.plan_issue(issue("fix(update): x", body("- Size: M"), labels=["dsh"]))
    assert il.plan_comment({"id": 7, "body": text}, later)[0] == "update"
    unchanged = il.plan_issue(issue("fix(update): x", body("- Size: S"), labels=["dsh"]))
    assert il.plan_comment({"id": 7, "body": text}, unchanged) == (None, None)


def test_labels_file_matches_the_script():
    names = {label["name"] for label in yaml.safe_load((ROOT / "labels.yml").read_text(encoding="utf-8"))}
    assert set(il.RUNNERS) | {il.NEEDS_ROUTING} | set(il.SIZE_LABELS.values()) | il.KINDS <= names
    assert not names & set(il.RETIRED)


def test_definitions_create_update_and_keep_extra():
    wanted = [{"name": "needs-routing", "color": "e99695", "description": "a"},
              {"name": "omo", "color": "5319e7", "description": "b"},
              {"name": "Bug", "color": "d73a4a", "description": "c"}]
    current = [{"name": "omo", "color": "5319E7", "description": "b"},
               {"name": "bug", "color": "d73a4a", "description": "old"},
               {"name": "ready", "color": "0e8a16", "description": ""}]
    create, update, extra = il.plan_definitions(wanted, current)
    assert [c["name"] for c in create] == ["needs-routing"]
    assert [(u["old"], u["name"]) for u in update] == [("bug", "Bug")]
    assert extra == ["ready"]
