#!/usr/bin/env python3
"""Validate a magic-questionnaire JSON config.

Checks structure, content rules (label + hint + reaction on every option, a
"why" on every step, contact data only at the end, a single education block)
and proves every route is reachable by enumerating answer combinations.

Usage:
    python validate_questionnaire.py path/to/questionnaire.json [--max-combos 200000]

Exit code 0 = no errors (warnings may be printed), 1 = errors, 2 = bad input.
Standard library only.
"""

import argparse
import itertools
import json
import random
import sys
from collections import Counter

OPS = {"gte": lambda a, b: a >= b, "lte": lambda a, b: a <= b, "eq": lambda a, b: a == b}


def matches(when, scores):
    for dim, conds in when.items():
        value = scores.get(dim, 0)
        for op, target in conds.items():
            if op not in OPS or not OPS[op](value, target):
                return False
    return True


def pick(entries, scores):
    for entry in entries:
        if not entry.get("default") and matches(entry.get("when", {}), scores):
            return entry
    for entry in entries:
        if entry.get("default"):
            return entry
    return None


def resolve(config, chosen_options):
    """chosen_options: list of option dicts in step order."""
    scores = Counter()
    forced = None
    for option in chosen_options:
        for dim, pts in option.get("score", {}).items():
            scores[dim] += pts
        if forced is None and option.get("route"):
            forced = option["route"]
    if forced:
        return forced, scores
    route = pick(config.get("routes", []), scores)
    return (route["id"] if route else None), scores


def validate(config, max_combos):
    errors, warnings = [], []
    steps = config.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["config has no steps"], warnings

    for key in ("id", "routes"):
        if key not in config:
            errors.append(f"missing top-level '{key}'")

    route_ids = [r.get("id") for r in config.get("routes", [])]
    if len(set(route_ids)) != len(route_ids):
        errors.append("duplicate route ids")
    defaults = [r for r in config.get("routes", []) if r.get("default")]
    if len(defaults) != 1:
        errors.append(f"exactly one default route required, found {len(defaults)}")
    for r in config.get("routes", []):
        for key in ("title", "body", "cta"):
            if not r.get(key):
                errors.append(f"route '{r.get('id')}' missing '{key}'")
    if len(route_ids) < 2:
        warnings.append("only one route: the questionnaire qualifies nobody")

    step_ids = set()
    single_steps = []
    educate_steps = set()
    text_steps = 0
    for index, step in enumerate(steps):
        sid = step.get("id")
        where = f"step[{index}] '{sid}'"
        if not sid:
            errors.append(f"step[{index}] missing id")
        elif sid in step_ids:
            errors.append(f"{where}: duplicate step id")
        step_ids.add(sid)
        stype = step.get("type", "single")
        if not step.get("title"):
            errors.append(f"{where}: missing title")
        if not step.get("why"):
            warnings.append(f"{where}: missing 'why' subtitle")

        if stype == "contact":
            if index < len(steps) - 1:
                errors.append(f"{where}: contact step must be the last step")
            continue
        if stype == "text":
            text_steps += 1
            if index == 0:
                errors.append(f"{where}: free text must not be the first question")
            continue
        if stype != "single":
            errors.append(f"{where}: unknown type '{stype}'")
            continue

        options = step.get("options", [])
        if not 2 <= len(options) <= 4:
            warnings.append(f"{where}: {len(options)} options (2-4 recommended)")
        option_ids = set()
        for option in options:
            oid = option.get("id")
            owhere = f"{where} option '{oid}'"
            if not oid or oid in option_ids:
                errors.append(f"{owhere}: missing or duplicate id")
            option_ids.add(oid)
            for key in ("label", "hint", "reaction"):
                if not option.get(key):
                    errors.append(f"{owhere}: missing '{key}'")
            if option.get("route") and option["route"] not in route_ids:
                errors.append(f"{owhere}: unknown route '{option['route']}'")
            if option.get("educate"):
                educate_steps.add(sid)
            if len(option.get("reaction", "")) > 140:
                warnings.append(f"{owhere}: reaction longer than 140 chars")
        single_steps.append(step)

    if text_steps > 1:
        warnings.append(f"{text_steps} free-text steps (1 recommended)")
    if len(educate_steps) > 1:
        errors.append(f"education block triggered on several steps {sorted(educate_steps)}; use one")
    if educate_steps and not config.get("education", {}).get("problem"):
        errors.append("options set 'educate' but config.education is missing")
    if not 3 <= len(steps) <= 8:
        warnings.append(f"{len(steps)} steps (4-6 recommended)")

    # Reachability
    option_lists = [step.get("options", []) for step in single_steps]
    total = 1
    for opts in option_lists:
        total *= max(len(opts), 1)
    if total <= max_combos:
        combos = itertools.product(*option_lists)
        sampled = False
    else:
        rng = random.Random(0)
        combos = ([rng.choice(opts) for opts in option_lists] for _ in range(max_combos))
        sampled = True
    counts = Counter()
    for combo in combos:
        route, _ = resolve(config, list(combo))
        counts[route] += 1
    explored = sum(counts.values())
    for rid in route_ids:
        if counts[rid] == 0:
            errors.append(f"route '{rid}' is unreachable")
    for rid, n in counts.items():
        if explored and n / explored > 0.8 and len(route_ids) > 1:
            warnings.append(f"route '{rid}' takes {n / explored:.0%} of combinations: is it qualifying anyone?")

    return errors, warnings, counts, explored, sampled


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path")
    parser.add_argument("--max-combos", type=int, default=200000)
    args = parser.parse_args()
    try:
        with open(args.path, encoding="utf-8") as fh:
            config = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read config: {exc}", file=sys.stderr)
        return 2

    result = validate(config, args.max_combos)
    if len(result) == 2:
        errors, warnings = result
        counts, explored, sampled = Counter(), 0, False
    else:
        errors, warnings, counts, explored, sampled = result

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    if explored:
        label = "sampled" if sampled else "all"
        print(f"\nRoute distribution ({label} {explored} combinations):")
        for rid, n in counts.most_common():
            print(f"  {rid:<20} {n:>8}  {n / explored:6.1%}")
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
