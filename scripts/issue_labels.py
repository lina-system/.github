#!/usr/bin/env python3
"""Judge size and runner for lina-system issues and keep their labels in line.

  issue_labels.py sync   [--repo OWNER/NAME] [--labels-file PATH] [--dry-run]
  issue_labels.py issues [--repo OWNER/NAME] [--issue N] [--dry-run]

The repository comes from --repo or GITHUB_REPOSITORY, the token from GITHUB_TOKEN.
This file is the only copy of the rules; lina, lina-app and lina-os call it through
.github/workflows/issue-labels.yml in lina-system/.github.

omo runs with one of two main models. omo-opus (Opus 5.5 medium) is the default: research,
planning, design comparison, documents and screen copy, work across areas or repositories,
and results people read. omo-astra (GPT-6 astra high) takes one narrow, deep task whose
answer a test can check; omo describes that profile as "Obsessive focus on one hard task"
and "NOT RECOMMENDED FOR WRITING OR EVERYDAY WORK". When unsure, omo-opus.

Runner, first rule that matches:
  1. A `Runner: <dsh|grok-cursor|agy|omo-opus|omo-astra> — <reason>` line. Without a reason it
     is ignored. The old `omo` is read as omo-opus.
  2. omo-opus: research work; device, real-data or measurement work; documentation only at
     size L; three or more title scopes; no checkable Done when; a design decision still
     open; a title scope in OPUS_SCOPES.
  3. omo-astra: a title scope in ASTRA_SCOPES; a migration (the title moves or migrates
     something into a new place); a fix with a reproduction (a failure rate like "failed in
     3 of 62 runs", or flaky); a fix or perf at size M or L with one title scope.
  4. omo-opus: the body is about security, credentials or personal data; size L.
  5. Documentation only, no design decision -> agy.
  6. S -> dsh, M -> grok-cursor.
  7. Otherwise -> needs-routing. lina-next writes Size: and Runner: lines and the next run labels it.

Size: S is 1-2 files, about 100 lines, one area; M is 3-8 files or a few hundred lines,
one area; L is larger, several areas, or a new subsystem or scaffold. The Size line is
used as written, except that scaffold work is always L.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

API = "https://api.github.com"
LABELS_FILE = Path(__file__).resolve().parent.parent / "labels.yml"
RUNNERS = ("dsh", "grok-cursor", "agy", "omo-opus", "omo-astra")
LEGACY_RUNNERS = {"omo": "omo-opus"}  # Still defined in labels.yml, never added; replaced when found.
SIZES = ("S", "M", "L")
SIZE_LABELS = {size: f"size/{size}" for size in SIZES}
NEEDS_ROUTING = "needs-routing"
RETIRED = ("ready", "blocked")  # GitHub's own issue dependencies replace these.
KIND_BY_TYPE = {
    "feat": "enhancement",
    "fix": "bug",
    "docs": "documentation",
    "research": "research",
    "chore": "maintenance",
    "refactor": "maintenance",
    "test": "maintenance",
    "ci": "maintenance",
    "build": "maintenance",
}
KINDS = set(KIND_BY_TYPE.values())
# After the GitHub Copilot coding agent guidance: keep sensitive, production-critical
# and cross-cutting work with the agent that can run and check it end to end.
# Risky areas that touch machines, settings and people go to omo-opus; those with a
# contract a test can hold go to omo-astra. A scope in neither is judged by the other rules.
OPUS_SCOPES = {"install", "config", "service", "release", "fleet", "secrets", "models"}
ASTRA_SCOPES = {"store", "migrate", "auth", "merge", "ci"}
MANY_SCOPES = 3
DESIGN_SCOPES = {"design", "architecture", "adr", "rfc"}
MARKER = "<!-- lina-labels:runner -->"

TITLE_RE = re.compile(r"^\s*([a-z]+)(?:\(([^)]*)\))?!?:", re.IGNORECASE)
SIZE_RE = re.compile(r"\bSize:[ \t]*([SML])\b")
RUNNER_RE = re.compile(
    r"\bRunner:[ \t]*(dsh|grok-cursor|agy|omo-opus|omo-astra|omo)[ \t]*(?:—|–|--?|:)[ \t]*(\S[^\n]*)",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
SCAFFOLD_RE = re.compile(r"\b(scaffold\w*|skeleton|new subsystem)\b|뼈대|새 하위 시스템", re.IGNORECASE)
MEASURE_RE = re.compile(
    r"\b(measur\w*|benchmark\w*|real data|live data|production data|"
    r"on (?:a|the) (?:real |physical )?device|physical device|real device|work devices?|"
    r"each device|every device|real task|inventory)\b|측정|실데이터|실기기",
    re.IGNORECASE,
)
SENSITIVE_RE = re.compile(
    r"\b(security|credentials?|secrets?|passwords?|private keys?|api keys?|"
    r"personal (?:data|information)|privacy|pii)\b|보안|자격 ?증명|개인 ?정보",
    re.IGNORECASE,
)
NEGATION_RE = re.compile(r"\b(no|not|never|without)\b", re.IGNORECASE)
NEGATION_WORDS = 4
CLAUSE_BREAK_RE = re.compile(r"\b(?:but|however|yet|although|though)\b", re.IGNORECASE)
OPEN_DESIGN_RE = re.compile(
    r"\b(tbd|open questions?|undecided|to be decided|decision needed)\b|미정|결정 필요",
    re.IGNORECASE,
)
MIGRATION_RE = re.compile(r"\bmigrat\w*|\bmov(?:e|es|ing)\b.+\binto\b|옮기", re.IGNORECASE)
REPRO_RE = re.compile(
    r"\b(?:flaky|flakiness|intermittent\w*|reproduc\w*|repro)\b|"
    r"\bfail(?:s|ed|ing)?\s+(?:in\s+)?\d+\s+(?:of|out of)\s+\d+|재현|간헐",
    re.IGNORECASE,
)
SENTENCE_RE = re.compile(r"[^.;!?\n]+")


@dataclass
class Judgment:
    size: str | None
    runner: str | None  # None means needs-routing.
    reason: str


@dataclass
class Plan:
    judgment: Judgment | None  # None for parents, the Roadmap and closed issues.
    add: set = field(default_factory=set)
    remove: set = field(default_factory=set)
    old_runners: list = field(default_factory=list)  # Runner labels replaced by the judgment.


def parse_title(title):
    """Return (type, scopes) from a Conventional Commit title; type is None without a prefix."""
    match = TITLE_RE.match(title or "")
    if not match:
        return None, set()
    scopes = {s.strip().lower() for s in re.split(r"[,/ ]+", match.group(2) or "") if s.strip()}
    return match.group(1).lower(), scopes


def parse_size(body):
    match = SIZE_RE.search(body or "")
    return match.group(1) if match else None


def parse_runner(body):
    """Return (runner, reason) from a Runner line that gives a reason, else None."""
    match = RUNNER_RE.search(body or "")
    if not match:
        return None
    runner = match.group(1).lower()
    return LEGACY_RUNNERS.get(runner, runner), match.group(2).strip()


def section(body, name):
    """Return the text under the heading `name`, or None when there is no such heading."""
    headings = list(HEADING_RE.finditer(body or ""))
    for i, heading in enumerate(headings):
        if heading.group(1).strip().lower() == name.lower():
            end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
            return body[heading.end():end]
    return None


def has_done_when(body):
    text = section(body, "Done when")
    if text is None:
        return False
    for line in text.splitlines():
        item = re.sub(r"^\s*(?:[-*+]|\d+\.)\s*(?:\[[ xX]\]\s*)?", "", line)
        if re.search(r"\w", item):
            return True
    return False


def mentions(pattern, text):
    """Return the first match of pattern that is not negated, else None.

    A match is negated when its sentence opens with no/not/never/without ("No dates or
    secrets") or one of those words stands at most NEGATION_WORDS words before it.
    """
    for sentence in SENTENCE_RE.findall(text or ""):
        for match in pattern.finditer(sentence):
            before = re.findall(r"[\w'-]+", sentence[:match.start()])
            opens = bool(before) and NEGATION_RE.fullmatch(before[0])
            # A negation stops at a contrast word: in "no secrets, but credentials ..." the second word counts.
            # A list stays under one negation: "No dates, machine names or secrets".
            clause = CLAUSE_BREAK_RE.split(sentence[:match.start()])[-1]
            near = any(NEGATION_RE.fullmatch(word) for word in re.findall(r"[\w'-]+", clause)[-NEGATION_WORDS:])
            if CLAUSE_BREAK_RE.search(sentence[:match.start()]) and not NEGATION_RE.search(clause):
                opens = False
            if not (opens or near):
                return match.group(0)
    return None


def judge_size(title, body):
    found = SCAFFOLD_RE.search(title or "") or SCAFFOLD_RE.search(section(body, "Summary") or "")
    if found:
        return "L", f"scaffold or new subsystem ({found.group(0)})"
    size = parse_size(body)
    return (size, f"Size: {size}") if size else (None, "no Size line")


def judge(title, body, labels=()):
    body = body or ""
    kind, scopes = parse_title(title)
    # A form can set the kind by label alone (the research form adds `research`, no title prefix).
    kind = kind or next((name for name in ("research", "qa") if name in labels), None)
    size, size_reason = judge_size(title, body)

    override = parse_runner(body)
    if override:
        return Judgment(size, override[0], f"Runner line: {override[1]}")
    opus, astra = "omo-opus", "omo-astra"
    if kind in ("research", "qa"):
        return Judgment(size, opus, f"{kind} work")
    measured = mentions(MEASURE_RE, f"{title}\n{body}")
    if measured:
        return Judgment(size, opus, f"device, real data or measurement ({measured})")
    if kind == "docs" and size == "L":
        return Judgment(size, opus, "documentation only, size L")
    if len(scopes) >= MANY_SCOPES:
        return Judgment(size, opus, f"{len(scopes)} areas ({', '.join(sorted(scopes))})")
    if not has_done_when(body):
        return Judgment(size, opus, "no checkable Done when")
    design = sorted(scopes & DESIGN_SCOPES)
    open_design = mentions(OPEN_DESIGN_RE, body)
    if design or open_design:
        return Judgment(size, opus, f"design decision open ({', '.join(design) or open_design})")
    risky = sorted(scopes & OPUS_SCOPES)
    if risky:
        return Judgment(size, opus, f"risky scope ({', '.join(risky)})")
    risky = sorted(scopes & ASTRA_SCOPES)
    if risky:
        return Judgment(size, astra, f"risky scope with a testable contract ({', '.join(risky)})")
    migration = MIGRATION_RE.search(title or "")
    if migration:
        return Judgment(size, astra, f"migration ({migration.group(0)})")
    repro = mentions(REPRO_RE, f"{title}\n{body}") if kind == "fix" else None
    if repro:
        return Judgment(size, astra, f"fix with a reproduction ({repro})")
    if kind in ("fix", "perf") and size in ("M", "L") and len(scopes) <= 1:
        return Judgment(size, astra, f"{kind} at size {size} in one area")
    sensitive = mentions(SENSITIVE_RE, body)
    if sensitive:
        return Judgment(size, opus, f"security, credentials or personal data ({sensitive})")
    if size == "L":
        return Judgment(size, opus, f"size L: {size_reason}")
    if kind == "docs":
        return Judgment(size, "agy", "documentation only")
    if size == "S":
        return Judgment(size, "dsh", "size S")
    if size == "M":
        return Judgment(size, "grok-cursor", "size M")
    return Judgment(size, None, f"needs routing: {size_reason}")


def is_parent_or_roadmap(issue):
    sub = issue.get("sub_issues_summary") or {}
    return sub.get("total", 0) > 0 or (issue.get("title") or "").strip().lower().startswith("roadmap")


def plan_issue(issue):
    labels = {label["name"] for label in issue.get("labels", [])}
    plan = Plan(judgment=None)
    plan.remove |= labels & set(RETIRED)
    if issue.get("state") == "closed":
        plan.remove |= labels & {NEEDS_ROUTING}
        return finish(plan, labels)

    kind = KIND_BY_TYPE.get(parse_title(issue.get("title"))[0] or "")
    if kind and not labels & KINDS:
        plan.add.add(kind)
    runner_labels = set(RUNNERS) | set(LEGACY_RUNNERS)
    if is_parent_or_roadmap(issue):
        plan.remove |= labels & (runner_labels | {NEEDS_ROUTING})
        return finish(plan, labels)

    judgment = judge(issue.get("title"), issue.get("body"), labels)
    plan.judgment = judgment
    if judgment.size:
        plan.add.add(SIZE_LABELS[judgment.size])
        plan.remove |= labels & (set(SIZE_LABELS.values()) - {SIZE_LABELS[judgment.size]})
    want = {judgment.runner} if judgment.runner else {NEEDS_ROUTING}
    plan.add |= want
    plan.remove |= labels & ((runner_labels | {NEEDS_ROUTING}) - want)
    current = sorted(labels & runner_labels)
    if current and set(current) != (want & set(RUNNERS)):
        plan.old_runners = current
    return finish(plan, labels)


def finish(plan, labels):
    plan.add -= labels
    plan.remove &= labels
    return plan


def comment_body(old_runners, judgment):
    old = ", ".join(f"`{name}`" for name in old_runners)
    if judgment.runner:
        head = f"Runner label set by the routing rules: `{judgment.runner}` (was {old})."
    else:
        head = f"Runner label removed (was {old}): the routing rules could not decide, so this issue is `{NEEDS_ROUTING}`."
    return (
        f"{MARKER}\n{head}\nReason: {judgment.reason}.\n\n"
        "To choose another runner, write `Runner: <dsh|grok-cursor|agy|omo-opus|omo-astra> — <reason>` in Context; "
        "a label changed by hand is put back on the next run. "
        "Rules: https://github.com/lina-system/.github/blob/main/scripts/issue_labels.py"
    )


def plan_comment(existing, plan):
    """Return ('create'|'update'|None, body); existing is the marked comment or None."""
    if not plan.old_runners or plan.judgment is None:
        return None, None
    body = comment_body(plan.old_runners, plan.judgment)
    if existing is None:
        return "create", body
    return ("update", body) if existing["body"] != body else (None, None)


def plan_definitions(wanted, current):
    """Return (create, update, extra) from the labels.yml entries and the repository's labels."""
    by_name = {label["name"].lower(): label for label in current}
    create, update = [], []
    for label in wanted:
        color = str(label["color"]).lower().lstrip("#")
        desc = label.get("description") or ""
        have = by_name.get(label["name"].lower())
        if have is None:
            create.append({"name": label["name"], "color": color, "description": desc})
        elif have["name"] != label["name"] or have["color"].lower() != color or (have.get("description") or "") != desc:
            update.append({"old": have["name"], "name": label["name"], "color": color, "description": desc})
    names = {label["name"].lower() for label in wanted}
    extra = sorted(label["name"] for label in current if label["name"].lower() not in names)
    return create, update, extra


class GitHub:
    def __init__(self, token, dry_run):
        self.token = token
        self.dry_run = dry_run

    def request(self, method, path, data=None):
        url = path if path.startswith("http") else API + path
        req = urllib.request.Request(url, method=method, data=json.dumps(data).encode() if data else None)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode()
            link = resp.headers.get("Link", "")
        nxt = re.search(r'<([^>]+)>;\s*rel="next"', link)
        return (json.loads(text) if text else None), (nxt.group(1) if nxt else None)

    def get_all(self, path):
        items, url = [], path
        while url:
            page, url = self.request("GET", url)
            items.extend(page)
        return items

    def write(self, method, path, data=None):
        if not self.dry_run:
            self.request(method, path, data)


def quote(name):
    return urllib.request.quote(name, safe="")


def summary(text):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text)


def run_sync(gh, repo, labels_file):
    import yaml

    wanted = yaml.safe_load(Path(labels_file).read_text(encoding="utf-8"))
    current = gh.get_all(f"/repos/{repo}/labels?per_page=100")
    create, update, extra = plan_definitions(wanted, current)
    for label in create:
        print(f"create {label['name']}")
        gh.write("POST", f"/repos/{repo}/labels", label)
    for label in update:
        print(f"update {label['old']} -> {label['name']}")
        gh.write("PATCH", f"/repos/{repo}/labels/{quote(label['old'])}",
                 {"new_name": label["name"], "color": label["color"], "description": label["description"]})
    print("not in labels.yml (kept): " + (", ".join(extra) or "none"))
    summary(f"## Labels\n\nCreated {len(create)}, updated {len(update)}.\n\n"
            f"Not in labels.yml (kept): {', '.join(extra) or 'none'}\n\n")


def cell(names):
    return ", ".join(sorted(names)) or "-"


def run_issues(gh, repo, only):
    if only:
        issues = [gh.request("GET", f"/repos/{repo}/issues/{only}")[0]]
    else:
        issues = gh.get_all(f"/repos/{repo}/issues?state=open&per_page=100")
    issues = [i for i in issues if "pull_request" not in i]
    rows = ["| Issue | Labels now | Labels after | Reason |", "| --- | --- | --- | --- |"]
    for issue in sorted(issues, key=lambda i: i["number"]):
        number = issue["number"]
        plan = plan_issue(issue)
        labels = {label["name"] for label in issue.get("labels", [])}
        after = (labels | plan.add) - plan.remove
        reason = plan.judgment.reason if plan.judgment else ("closed" if issue.get("state") == "closed" else "parent or Roadmap")
        mark = "" if after == labels else " (changed)"
        rows.append(f"| {repo.split('/')[1]}#{number}{mark} | {cell(labels)} | {cell(after)} | {reason} |")
        if plan.add:
            print(f"#{number} add {cell(plan.add)}")
            gh.write("POST", f"/repos/{repo}/issues/{number}/labels", {"labels": sorted(plan.add)})
        for name in sorted(plan.remove):
            print(f"#{number} remove {name}")
            gh.write("DELETE", f"/repos/{repo}/issues/{number}/labels/{quote(name)}")
        if not plan.old_runners:
            continue
        comments = gh.get_all(f"/repos/{repo}/issues/{number}/comments?per_page=100")
        existing = next((c for c in comments if MARKER in (c.get("body") or "")), None)
        action, body = plan_comment(existing, plan)
        if action == "create":
            print(f"#{number} comment runner {cell(plan.old_runners)} -> {plan.judgment.runner or NEEDS_ROUTING}")
            gh.write("POST", f"/repos/{repo}/issues/{number}/comments", {"body": body})
        elif action == "update":
            print(f"#{number} update runner comment")
            gh.write("PATCH", f"/repos/{repo}/issues/comments/{existing['id']}", {"body": body})
    table = "\n".join(rows) + "\n"
    if gh.dry_run:
        print(table)
    summary(f"## Issues{' (dry run)' if gh.dry_run else ''}\n\n{table}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["sync", "issues"])
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--labels-file", default=str(LABELS_FILE))
    parser.add_argument("--issue", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not args.repo:
        parser.error("--repo or GITHUB_REPOSITORY is required")
    gh = GitHub(os.environ.get("GITHUB_TOKEN"), args.dry_run)
    if args.mode == "sync":
        run_sync(gh, args.repo, args.labels_file)
    else:
        run_issues(gh, args.repo, args.issue)


if __name__ == "__main__":
    sys.exit(main())
