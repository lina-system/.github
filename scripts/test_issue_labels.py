import unittest

import issue_labels as il

REPO = "lina-system/lina"


def issue(number, title="no prefix", body="", labels=(), state="open", sub=0):
    return {
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "labels": [{"name": name} for name in labels],
        "sub_issues_summary": {"total": sub, "completed": 0},
    }


def closed_in(*closed):
    return lambda repo, number: (repo, number) in closed


class DependsTest(unittest.TestCase):
    def test_agent_context_line(self):
        body = "## Context\n\n- Part of #26. Depends on: #31, #7. Size: M (a few days).\n"
        self.assertEqual(il.parse_depends(body, REPO), [(REPO, 31), (REPO, 7)])

    def test_issue_form_context(self):
        body = "### Context\n\n- Depends on: #2, lina#39\n- Size: S\n- Runner: dsh\n"
        self.assertEqual(il.parse_depends(body, "lina-system/lina-app"),
                         [("lina-system/lina-app", 2), ("lina-system/lina", 39)])

    def test_none_and_missing(self):
        self.assertEqual(il.parse_depends("- Depends on: none. Size: S (about a day).", REPO), [])
        self.assertIsNone(il.parse_depends("## Context\n\n- Part of #26.", REPO))
        self.assertIsNone(il.parse_depends("- Depends on the core client API (lina#39).", REPO))

    def test_all_closed_is_ready(self):
        add, remove, _ = il.plan_issue(issue(36, body="Depends on: #30, #35.", labels=["omo", "blocked"]),
                                       REPO, closed_in((REPO, 30), (REPO, 35)))
        self.assertEqual((add, remove), ({"ready"}, {"blocked"}))

    def test_one_open_is_blocked(self):
        add, remove, _ = il.plan_issue(issue(36, body="Depends on: #30, #35.", labels=["omo", "ready"]),
                                       REPO, closed_in((REPO, 30)))
        self.assertEqual((add, remove), ({"blocked"}, {"ready"}))

    def test_none_is_ready_and_no_line_is_untouched(self):
        add, _, _ = il.plan_issue(issue(27, body="Depends on: none.", labels=["omo"]), REPO, closed_in())
        self.assertEqual(add, {"ready"})
        add, remove, _ = il.plan_issue(issue(49, body="## Context\n\n- See #1.", labels=["omo"]), REPO, closed_in())
        self.assertEqual((add, remove), (set(), set()))

    def test_closed_issue_drops_state(self):
        add, remove, runners = il.plan_issue(
            issue(28, body="Depends on: #27.", labels=["omo", "ready"], state="closed"), REPO, closed_in())
        self.assertEqual((add, remove, runners), (set(), {"ready"}, None))

    def test_dependent_recomputed_after_close(self):
        dependent = issue(37, body="Depends on: #34, #36.", labels=["omo", "blocked"])
        before = il.plan_issue(dependent, REPO, closed_in((REPO, 34)))
        after = il.plan_issue(dependent, REPO, closed_in((REPO, 34), (REPO, 36)))
        self.assertEqual(before[:2], (set(), set()))
        self.assertEqual(after[:2], ({"ready"}, {"blocked"}))


class RunnerTest(unittest.TestCase):
    def test_two_runners_warn(self):
        _, _, runners = il.plan_issue(issue(9, labels=["dsh", "omo"]), REPO, closed_in())
        self.assertEqual(runners, ["dsh", "omo"])
        self.assertEqual(il.plan_comment(None, runners), ("create", il.warning_body(runners)))

    def test_same_comment_is_edited_not_added(self):
        existing = {"id": 1, "body": il.warning_body(["dsh", "omo"])}
        self.assertEqual(il.plan_comment(existing, ["dsh", "omo"]), (None, None))
        self.assertEqual(il.plan_comment(existing, ["agy", "dsh", "omo"]),
                         ("update", il.warning_body(["agy", "dsh", "omo"])))
        self.assertEqual(il.plan_comment(existing, []), ("update", il.cleared_body()))
        self.assertEqual(il.plan_comment(None, []), (None, None))

    def test_parent_and_roadmap_are_exempt(self):
        parent = issue(26, title="chore(parity): x", labels=["dsh", "omo"], sub=15)
        roadmap = issue(1, title="Roadmap", body="Runner: omo", labels=["dsh", "omo"])
        for item in (parent, roadmap):
            add, _, runners = il.plan_issue(item, REPO, closed_in())
            self.assertIsNone(runners)
            self.assertFalse(add & set(il.RUNNERS))

    def test_runner_line_fills_missing_label_only(self):
        add, _, runners = il.plan_issue(issue(50, body="- Runner: grok-cursor"), REPO, closed_in())
        self.assertIn("grok-cursor", add)
        self.assertEqual(runners, [])
        add, _, _ = il.plan_issue(issue(50, body="- Runner: grok-cursor", labels=["omo"]), REPO, closed_in())
        self.assertNotIn("grok-cursor", add)
        self.assertIsNone(il.parse_runner("- Runner:\n- Size: M"))


class KindTest(unittest.TestCase):
    def test_prefixes(self):
        cases = {
            "feat(memory): x": "enhancement",
            "fix: x": "bug",
            "docs(os): x": "documentation",
            "research(os): x": "research",
            "chore(prune): x": "maintenance",
            "refactor(core)!: x": "maintenance",
            "test(memory): x": "maintenance",
            "ci(upstream): x": "maintenance",
            "build(deps): x": "maintenance",
            "qa(m0): x": None,
            "Roadmap": None,
            "feature: x": None,
        }
        for title, kind in cases.items():
            self.assertEqual(il.kind_for_title(title), kind, title)

    def test_existing_kind_wins(self):
        add, _, _ = il.plan_issue(issue(3, title="fix(x): y", labels=["enhancement"]), REPO, closed_in())
        self.assertNotIn("bug", add)

    def test_size_from_context(self):
        add, _, _ = il.plan_issue(issue(3, body="Size: L (a week or more)."), REPO, closed_in())
        self.assertIn("size/L", add)
        self.assertIsNone(il.parse_size("- Size:\n- Runner: omo"))


class DefinitionsTest(unittest.TestCase):
    def test_create_update_and_keep_extra(self):
        wanted = [{"name": "ready", "color": "0e8a16", "description": "a"},
                  {"name": "omo", "color": "5319e7", "description": "b"},
                  {"name": "Bug", "color": "d73a4a", "description": "c"}]
        current = [{"name": "omo", "color": "5319E7", "description": "b"},
                   {"name": "bug", "color": "d73a4a", "description": "old"},
                   {"name": "cloud", "color": "8250df", "description": ""}]
        create, update, extra = il.plan_definitions(wanted, current)
        self.assertEqual([c["name"] for c in create], ["ready"])
        self.assertEqual([(u["old"], u["name"]) for u in update], [("bug", "Bug")])
        self.assertEqual(extra, ["cloud"])


if __name__ == "__main__":
    unittest.main()
