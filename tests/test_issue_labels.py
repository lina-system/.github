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
     "M", "omo-opus"),
    ("lina#79 fix S", "fix(update): stop update from offering the official Hermes repository as upstream",
     body("- Depends on: none\n- Size: S\n- Runner: grok-cursor"), "S", "dsh"),
    ("lina#78 fix S", "fix(lina_helper): keep endpoint-based driver resolution during recovery",
     body("- Depends on: none\n- Size: S\n- Runner: grok-cursor"), "S", "dsh"),
    ("lina#77 fix S", "fix(workspace): load Desk instructions for nested task workspaces",
     body("- Depends on: none\n- Size: S\n- Runner: grok-cursor"), "S", "dsh"),
    ("lina-app#2 scaffold", "chore(repo): scaffold the web client with alpha versioning, CI and the generated API client",
     body("- Depends on: none. Size: M (a few days)."), "L", "omo-opus"),
    ("lina#61 ci(merge) M", "ci(merge): enforce the delivery procedure with required checks and write it down",
     body("- Part of #26. Depends on: none. Size: M."), "M", "omo-astra"),
    ("lina#9 build(deps) S", "build(deps): drop the extras of deleted features",
     body("- Part of #4. Depends on: #8. Size: S (about a day).",
          done="## Done when\n\n- `pyproject.toml` and `uv.lock` are trimmed, and the installed size is recorded.\n"),
     "S", "dsh"),
    ("Runner line with reason wins", "feat(home): x",
     body("- Size: S\n- Runner: omo — needs the phone build"), "S", "omo-opus"),
    ("Runner line with hyphen reason", "feat(store): x",
     body("- Size: M\n- Runner: grok-cursor - schema is already decided"), "M", "grok-cursor"),
    ("research prefix", "research(os): pick the base image", body("- Size: S"), "S", "omo-opus"),
    ("measurement in body", "test(memory): x", body("- Size: S", summary="Measure the cache hit rate."), "S", "omo-opus"),
    ("size L", "feat(memory): x", body("- Size: L (a week or more)."), "L", "omo-opus"),
    ("risky scope at S", "feat(install): x", body("- Size: S"), "S", "omo-opus"),
    ("risky scope in a list", "fix(api, auth): x", body("- Size: S"), "S", "omo-astra"),
    ("credentials in body", "fix(home): x", body("- Size: S", summary="Move the API keys into the keychain."), "S", "omo-opus"),
    ("negated secrets is not risky", "fix(home): x", body("- Size: S", summary="Logs carry no secrets."), "S", "dsh"),
    ("a negated list stays negated", "fix(home): x",
     body("- Size: S", summary="No dates, machine names or secrets in the output."), "S", "dsh"),
    ("a later keyword after a negated one still counts", "fix(home): x",
     body("- Size: S", summary="Logs contain no secrets, but credentials must be rotated."), "S", "omo-opus"),
    ("far negation still counts as risky (lina#59)", "fix(memory): x",
     body("- Size: S", summary="The wizard does not catch this error, so setup aborts before credentials are set."),
     "S", "omo-opus"),
    ("work devices (lina#37)", "chore(work): x",
     body("- Size: M", summary="Every work device is listed, and a real task completes on each."), "M", "omo-opus"),
    ("no Done when", "fix(home): x", "## Summary\n\nA change.\n\n## Context\n\n- Size: S\n", "S", "omo-opus"),
    ("empty Done when", "fix(home): x", body("- Size: S", done="## Done when\n\n- [ ]\n"), "S", "omo-opus"),
    ("open question", "feat(home): x", body("- Size: M", summary="Open question: which card order."), "M", "omo-opus"),
    ("docs only", "docs(readme): fix the install steps", body("- Size: S"), "S", "agy"),
    ("M code", "feat(home): x", body("- Size: M (a few days)."), "M", "grok-cursor"),
    ("no size", "feat(home): x", body("- Depends on: none"), None, None),
    ("empty Size and Runner fields", "feat(home): x", body("- Size:\n- Runner:"), None, None),
]


@pytest.mark.parametrize(("case", "title", "text", "size", "runner"), JUDGE_CASES, ids=[c[0] for c in JUDGE_CASES])
def test_judge(case, title, text, size, runner):
    judgment = il.judge(title, text)
    assert (judgment.size, judgment.runner) == (size, runner), judgment.reason


# One row per rule of the omo split, in rule order, then the real issues it was decided on (2026-11-02).
OMO_CASES = [
    # (case, title, body, size, runner)
    ("Runner line omo-opus", "fix(store): x", body("- Size: M\n- Runner: omo-opus — the owner reads the result"),
     "M", "omo-opus"),
    ("Runner line omo-astra", "feat(home): x", body("- Size: S\n- Runner: omo-astra — one hard parser"), "S", "omo-astra"),
    ("Runner line old omo reads as omo-opus", "fix(store): x", body("- Size: M\n- Runner: omo — needs a person"),
     "M", "omo-opus"),
    ("Runner line omo-astra without a reason is ignored", "fix(home): x", body("- Size: S\n- Runner: omo-astra"),
     "S", "dsh"),
    ("Runner line omo-opus without a reason is ignored", "fix(home): x", body("- Size: S\n- Runner: omo-opus"),
     "S", "dsh"),
    ("Runner line with an unknown omo name is ignored", "fix(home): x", body("- Size: S\n- Runner: omo-x - y"),
     "S", "dsh"),
    ("opus: research", "research(store): x", body("- Size: M"), "M", "omo-opus"),
    ("opus: measurement beats a store scope", "fix(store): x", body("- Size: M", summary="Benchmark the writes."),
     "M", "omo-opus"),
    ("opus: docs only at L", "docs(guide): x", body("- Size: L"), "L", "omo-opus"),
    ("opus: three areas", "fix(store, auth, home): x", body("- Size: M"), "M", "omo-opus"),
    ("opus: no Done when beats a store scope", "fix(store): x", "## Summary\n\nA change.\n\n## Context\n\n- Size: M\n",
     "M", "omo-opus"),
    ("opus: open design beats a store scope", "feat(store): x", body("- Size: M", summary="The schema is TBD."),
     "M", "omo-opus"),
    ("opus: design scope", "feat(architecture): x", body("- Size: M"), "M", "omo-opus"),
    ("opus: config scope", "fix(config): x", body("- Size: M"), "M", "omo-opus"),
    ("opus: an opus and an astra scope", "fix(release, ci): x", body("- Size: S"), "S", "omo-opus"),
    ("opus: models scope", "feat(models): x", body("- Size: S"), "S", "omo-opus"),
    ("astra: store scope at S", "feat(store): x", body("- Size: S"), "S", "omo-astra"),
    ("astra: migrate scope", "chore(migrate): x", body("- Size: M"), "M", "omo-astra"),
    ("astra: migration in the title", "refactor(memory): migrate the notes table", body("- Size: M"), "M", "omo-astra"),
    ("astra: fix with a flaky test at S", "fix(test): x", body("- Size: S", summary="The test is flaky on CI."),
     "S", "omo-astra"),
    ("fix with no reproduction at S stays dsh", "fix(test): x", body("- Size: S", summary="It is not flaky."), "S", "dsh"),
    ("astra: fix at M in one area", "fix(home): x", body("- Size: M"), "M", "omo-astra"),
    ("astra: perf at L in one area", "perf(memory): x", body("- Size: L"), "L", "omo-astra"),
    ("fix at M in two areas stays grok-cursor", "fix(home, api): x", body("- Size: M"), "M", "grok-cursor"),
    ("feat at M stays grok-cursor", "feat(home): x", body("- Size: M"), "M", "grok-cursor"),
    ("opus: security after the astra rules", "feat(home): x", body("- Size: M", summary="Store the API keys safely."),
     "M", "omo-opus"),
    ("opus: other work at L", "chore(repo): x", body("- Size: L"), "L", "omo-opus"),
    ("lina#12 store", "feat(store): keep each message once in memory.messages and have the core read and write it",
     body("- Part of #3. Depends on: #11, #8. Size: L (a week or more).",
          summary="Agent turns move from each agent's SQLite file to `memory.messages`, the one copy every engine reads.",
          done="## Done when\n\n- Each agent's `state.db` keeps only operational state.\n- The state tests pass on the new store.\n"),
     "L", "omo-astra"),
    ("lina#36 work ledger move", "feat(work): move the work ledger into lina work and add lina work run",
     body("- Part of #26. Depends on: #30, #35. Size: L (a week or more).",
          summary="The work record moves into the core as it is, and handing work to omo becomes `lina work run`.",
          done="## Done when\n\n- `lina work json` matches today's output on a copied ledger.\n"),
     "L", "omo-astra"),
    ("lina#35 worker design", "feat(worker): add lina worker with omo as the default runner and pluggable others",
     body("- Part of #26. Depends on: #34. Size: L (a week or more).",
          summary="Coding agents plug in through a small runner contract.",
          done="## Done when\n\n- `lina worker` runs as `ai.lina.worker` (`lina-worker` on Linux) on each work device.\n"),
     "L", "omo-opus"),
    ("lina#67 skills trim", "chore(skills): trim the bundled skills to what the agents use and keep the self-improvement loop",
     body("- Size: M", summary="Cut the bundled `skills/` down to what the owner's eight agents use.\n\n"
          "### Self-improvement in use today (measured on the owner's agents, 2026-11-02)"),
     "M", "omo-opus"),
    ("lina#95 flaky test fix", "fix(test): stop the compound background spawn test capturing another thread's Popen",
     body("Sprint: M0 S1\nSize: S",
          summary="The test failed `assert 2 == 1`. It failed in 3 of 62 lina CI runs today.",
          done="## Done when\n\n- [ ] The cause is found and fixed, with no retry, flaky marker or longer timeout\n"),
     "S", "omo-astra"),
    ("lina#27 inventory", "chore(inventory): take a read-only inventory of today's setup and a manifest of the frozen sources",
     body("- Part of #26. Depends on: none. Size: S (about a day).",
          summary="Before anything moves, record what runs today and freeze checksums of the sources LINA starts from.",
          done="## Done when\n\n- Checksums of every untouched source are written to a manifest.\n"),
     "S", "omo-opus"),
]


@pytest.mark.parametrize(("case", "title", "text", "size", "runner"), OMO_CASES, ids=[c[0] for c in OMO_CASES])
def test_judge_omo_split(case, title, text, size, runner):
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
     {"size/L", "omo-opus"}, {"size/M", "grok-cursor"}, ["grok-cursor"]),
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
    ("old omo label is replaced by omo-opus",
     issue("research(os): x", body("- Size: S"), labels=["research", "size/S", "omo"]),
     {"omo-opus"}, {"omo"}, ["omo"]),
    ("old omo label is replaced by omo-astra",
     issue("feat(store): x", body("- Size: L"), labels=["enhancement", "size/L", "omo"]),
     {"omo-astra"}, {"omo"}, ["omo"]),
    ("parent drops the old omo label",
     issue("feat(store): x", body("- Size: L"), labels=["enhancement", "omo"], sub=3), set(), {"omo"}, []),
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
    assert set(il.RUNNERS) | set(il.LEGACY_RUNNERS) | {il.NEEDS_ROUTING} | set(il.SIZE_LABELS.values()) | il.KINDS <= names
    assert "omo" not in il.RUNNERS
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


def test_research_label_without_title_prefix_goes_to_omo_opus():
    text = body("- Size: S")
    assert il.judge("Compare two parsers", text).runner == "dsh"
    assert il.judge("Compare two parsers", text, {"research"}).runner == "omo-opus"
    plan = il.plan_issue(issue("Compare two parsers", text, labels=("research",)))
    assert "omo-opus" in plan.add and "dsh" not in plan.add
