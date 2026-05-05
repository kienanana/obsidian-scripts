#!/usr/bin/env python3
import sys
import re
import json
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from datetime import datetime

VAULT = Path.home() / "Documents" / "VAULT"
LEARNINGS = VAULT / "Personal" / "Learnings"

GRAPHQL_QUERY = """
query getProblem($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    title
    questionFrontendId
    difficulty
    topicTags { name slug }
  }
}
"""

TOPIC_TAG_MAP = {
    "array":                "cs/arrays",
    "hash-table":           "cs/hashing",
    "linked-list":          "cs/linked-lists",
    "string":               "cs/strings",
    "stack":                "cs/stacks",
    "queue":                "cs/queues",
    "heap-priority-queue":  "cs/heaps",
    "matrix":               "cs/matrices",
    "trie":                 "cs/tries",
    "tree":                 "cs/trees",
    "binary-tree":          "cs/trees",
    "binary-search-tree":   "cs/trees",
    "n-ary-tree":           "cs/trees",
    "segment-tree":         "cs/trees",
    "binary-indexed-tree":  "cs/trees",
    "graph":                "cs/graphs",
    "depth-first-search":   "cs/graphs",
    "breadth-first-search": "cs/graphs",
    "topological-sort":     "cs/graphs",
    "shortest-path":        "cs/graphs",
    "union-find":           "cs/union-find",
    "dynamic-programming":  "cs/dp",
    "memoization":          "cs/dp",
    "binary-search":        "cs/binary-search",
    "sorting":              "cs/sorting",
    "backtracking":         "cs/backtracking",
    "greedy":               "cs/greedy",
    "divide-and-conquer":   "cs/divide-and-conquer",
    "recursion":            "cs/recursion",
    "two-pointers":         "cs/two-pointers",
    "sliding-window":       "cs/sliding-window",
    "prefix-sum":           "cs/arrays",
    "bit-manipulation":     "cs/bit-manipulation",
    "monotonic-stack":      "cs/stacks",
    "monotonic-queue":      "cs/queues",
    "math":                 "cs/math",
    "number-theory":        "cs/math",
    "counting":             "cs/math",
    "geometry":             "cs/math",
    "game-theory":          "cs/math",
    "simulation":           "cs/simulation",
    "randomized":           "cs/math",
}

DIFFICULTY_TAG_MAP = {
    "Easy":   "leetcode/easy",
    "Medium": "leetcode/medium",
    "Hard":   "leetcode/hard",
}


def slug_from_url(url: str) -> str:
    m = re.search(r"leetcode\.com/problems/([^/?#\s]+)", url)
    if not m:
        print(f"error: cannot extract problem slug from: {url}", file=sys.stderr)
        sys.exit(1)
    return m.group(1).rstrip("/")


def fetch_problem(slug: str) -> dict:
    payload = json.dumps({
        "query": GRAPHQL_QUERY,
        "variables": {"titleSlug": slug},
    }).encode()
    req = urllib.request.Request(
        "https://leetcode.com/graphql",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
    except urllib.error.URLError as e:
        print(f"error: network request failed — {e}", file=sys.stderr)
        sys.exit(1)

    if "errors" in body:
        print(f"error: LeetCode API returned errors: {body['errors']}", file=sys.stderr)
        sys.exit(1)

    question = body.get("data", {}).get("question")
    if not question:
        print(f"error: problem '{slug}' not found on LeetCode", file=sys.stderr)
        sys.exit(1)

    return question


def build_tags(topic_tags: list, difficulty: str) -> list[str]:
    seen = set()
    tags = []
    for t in topic_tags:
        mapped = TOPIC_TAG_MAP.get(t["slug"], f"cs/{t['slug']}")
        if mapped not in seen:
            seen.add(mapped)
            tags.append(mapped)
    tags.append(DIFFICULTY_TAG_MAP.get(difficulty, f"leetcode/{difficulty.lower()}"))
    return tags


def get_solution_code() -> str:
    try:
        clipboard = subprocess.check_output(["pbpaste"], text=True)
    except Exception:
        clipboard = ""

    if clipboard.strip():
        first_line = clipboard.strip().splitlines()[0]
        answer = input(f'Use clipboard as solution? (first line: "{first_line}") [Y/n]: ').strip().lower()
        if answer in ("", "y", "yes"):
            return clipboard.strip()

    print("Paste your solution, then press Ctrl+D when done:")
    lines = []
    try:
        for line in sys.stdin:
            lines.append(line)
    except EOFError:
        pass
    return "".join(lines).strip()


def build_note(
    title: str,
    problem_number: str,
    tags: list[str],
    source_url: str,
    language: str,
    solution_code: str,
    personal_note: str,
) -> str:
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    updated_str = now.strftime("%Y-%m-%d %H:%M:%S")
    tags_yaml = "\n".join(f"  - {t}" for t in tags)

    body = f"[[Leetcode]] #{problem_number}"
    if personal_note:
        body += f"\n- {personal_note}"
    body += f"\n\n```{language}\n{solution_code}\n```"

    return (
        f"---\n"
        f"class:\n"
        f"tags:\n"
        f"{tags_yaml}\n"
        f"source: {source_url}\n"
        f"related:\n"
        f"author:\n"
        f"date: {date_str}\n"
        f"updated: {updated_str}\n"
        f"aliases:\n"
        f"---\n"
        f"{body}\n"
    )


def clean_url(url: str) -> str:
    # Normalise to the canonical description URL
    m = re.match(r"(https://leetcode\.com/problems/[^/?#]+)", url)
    return m.group(1) + "/description/" if m else url


def main():
    if len(sys.argv) < 2:
        print("usage: leet.py <leetcode-problem-url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    slug = slug_from_url(url)

    print("Fetching problem data...")
    problem = fetch_problem(slug)

    title = problem["title"]
    difficulty = problem["difficulty"]
    problem_number = problem["questionFrontendId"]
    tags = build_tags(problem["topicTags"], difficulty)

    print(f"  Title:      {title}")
    print(f"  Difficulty: {difficulty}")
    print(f"  Tags:       {', '.join(tags)}")
    print()

    lang_input = input("Language for code block [java]: ").strip()
    language = lang_input if lang_input else "java"

    print()
    solution_code = get_solution_code()

    print()
    personal_note = input("Personal note (optional, press Enter to skip): ").strip()

    safe_title = re.sub(r'[/:*?"<>|\\]', "", title)
    out_path = LEARNINGS / f"{safe_title}.md"

    if out_path.exists():
        answer = input(f"\n{out_path.name} already exists. Overwrite? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    note = build_note(
        title=title,
        problem_number=problem_number,
        tags=tags,
        source_url=clean_url(url),
        language=language,
        solution_code=solution_code,
        personal_note=personal_note,
    )

    LEARNINGS.mkdir(parents=True, exist_ok=True)
    out_path.write_text(note, encoding="utf-8")
    print(f"\nWriting note to: Personal/Learnings/{safe_title}.md")
    print("Done.")


if __name__ == "__main__":
    main()
