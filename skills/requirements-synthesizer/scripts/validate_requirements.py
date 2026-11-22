#!/usr/bin/env python3
"""Check a requirements.json before it is turned into a PDF.

Errors (exit code 1) are things that would break the document or its traceability.
Warnings are quality smells a reviewer would flag; fix them or consciously accept them.

Usage: python validate_requirements.py requirements.json
"""
import json
import re
import sys

TYPES = {"functional", "non_functional", "business_rule", "data", "interface"}
PRIORITIES = {"Must", "Should", "Could", "Won't"}
VAGUE = ["fast", "quick", "quickly", "user-friendly", "user friendly", "easy", "easily", "simple",
         "intuitive", "flexible", "robust", "scalable", "efficient", "efficiently", "modern",
         "seamless", "as soon as possible", "asap", "minimal", "optimal", "adequate", "reasonable",
         "etc", "and/or", "as appropriate", "if possible", "tbd"]
SRC_RE = re.compile(r"^(S\d+)\b")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(d):
    errors, warnings = [], []
    err, warn = errors.append, warnings.append

    if not d.get("meta", {}).get("title"):
        err("meta.title is missing")
    reqs = d.get("requirements", [])
    if not reqs:
        err("requirements[] is empty")

    src_ids = {s["id"] for s in d.get("sources", []) if "id" in s}
    st_ids = {s["id"] for s in d.get("stakeholders", []) if "id" in s}
    if not src_ids:
        err("sources[] is empty - every requirement needs traceable sources")
    if not st_ids:
        err("stakeholders[] is empty")

    seen = set()
    for r in reqs:
        rid = r.get("id", "(no id)")
        if rid in seen:
            err(f"{rid}: duplicate id")
        seen.add(rid)
        if r.get("type") not in TYPES:
            err(f"{rid}: type must be one of {sorted(TYPES)}")
        stmt = (r.get("statement") or "").strip()
        if not stmt:
            err(f"{rid}: statement is empty")
            continue
        if r.get("priority") not in PRIORITIES:
            err(f"{rid}: priority must be one of {sorted(PRIORITIES)}")
        if not r.get("sources"):
            err(f"{rid}: no sources (cite as 'S1 @ locator')")
        for s in r.get("sources", []):
            m = SRC_RE.match(s)
            if not m or m.group(1) not in src_ids:
                err(f"{rid}: source '{s}' does not match a sources[] id")
        for s in r.get("stakeholders", []):
            if s not in st_ids:
                err(f"{rid}: unknown stakeholder id '{s}'")
        if not r.get("stakeholders"):
            warn(f"{rid}: no stakeholders recorded")
        if not r.get("acceptance_criteria"):
            warn(f"{rid}: no acceptance criteria")
        if not re.search(r"\b(shall|must)\b", stmt, re.I):
            warn(f"{rid}: statement lacks 'shall' - write it as an obligation")
        if len(stmt.split()) > 60:
            warn(f"{rid}: statement is {len(stmt.split())} words - probably compound, split it")
        low = " " + stmt.lower() + " "
        hits = [w for w in VAGUE if re.search(rf"\b{re.escape(w)}\b", low)]
        if hits:
            warn(f"{rid}: vague wording {hits} - quantify or move the number to an open question")
        if r.get("priority_basis") not in ("stated", "proposed"):
            warn(f"{rid}: priority_basis should be 'stated' or 'proposed'")

    ids = {r.get("id") for r in reqs}
    obj_ids = {o.get("id") for o in d.get("objectives", [])}
    for r in reqs:
        for o in r.get("objectives", []):
            if o not in obj_ids:
                err(f"{r.get('id')}: unknown objective id '{o}'")
    for c in d.get("conflicts", []):
        for rid in c.get("requirements", []):
            if rid not in ids:
                err(f"{c.get('id')}: references unknown requirement '{rid}'")
        if not c.get("positions"):
            warn(f"{c.get('id')}: conflict has no positions recorded")
    for q in d.get("open_questions", []):
        for rid in q.get("related", []):
            if rid not in ids:
                warn(f"{q.get('id')}: related id '{rid}' not found")

    used_st = {s for r in reqs for s in r.get("stakeholders", [])}
    for sid in sorted(st_ids - used_st):
        warn(f"stakeholder {sid} has no requirements - missing voice, or not a real stakeholder?")
    used_src = {SRC_RE.match(s).group(1) for r in reqs for s in r.get("sources", []) if SRC_RE.match(s)}
    for sid in sorted(src_ids - used_src):
        warn(f"source {sid} is never cited - was it fully read?")
    if not d.get("open_questions"):
        warn("open_questions[] is empty - real inputs almost always leave gaps; re-check")
    if not any(r.get("type") == "non_functional" for r in reqs):
        warn("no non-functional requirements - check the NFR checklist in references/")
    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    errors, warnings = validate(load(sys.argv[1]))
    for e in errors:
        print("ERROR  ", e)
    for w in warnings:
        print("WARNING", w)
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
