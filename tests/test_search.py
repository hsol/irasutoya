#!/usr/bin/env python3
"""Regression tests for the query fan-out. Each case is a bug this skill once had.

    python3 tests/test_search.py

Hits the live site, so it needs network and takes ~15s.
"""
import os
import subprocess
import sys

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "irasutoya.py")


def run(*args):
    r = subprocess.run([sys.executable, SCRIPT, *args],
                       capture_output=True, text=True, timeout=60)
    return r.stdout


CASES = [
    # (why it exists, args, predicate over stdout)
    ("particles: リンゴを食べる returns nothing, リンゴ 食べる does",
     ["find", "リンゴを食べる"], lambda o: "ringo_taberu.png" in o.splitlines()[1]),

    ("kanji/katakana: the title says 猿, the query says サル",
     ["find", "サル バナナ"], lambda o: "eto_saru_banana2.png" in o.splitlines()[1]),

    ("verb tails: 持ったサル has to reduce to サル",
     ["find", "バナナを持ったサル"], lambda o: "eto_saru_banana2.png" in o.splitlines()[1]),

    ("kanji/katakana again, this time for an object",
     ["find", "眼鏡をかけた女性"], lambda o: "megane" in o.splitlines()[1]),

    ("substring demotion: サル must not surface アンドリューサルクス",
     ["find", "サル"], lambda o: "kodai_andrewsarchus" not in o.splitlines()[1]),

    ("short words: の in のり is not a particle",
     ["find", "のり"], lambda o: "tried: のり" in o and " り " not in o.split("(")[0]),

    ("label filter keeps only matching results",
     ["find", "会議", "--label", "医療"],
     lambda o: all("医療" in l for l in o.splitlines()[1:] if l.startswith((" 1", " 2")))),

    ("browse walks a whole label",
     ["browse", "干支", "3"], lambda o: o.startswith("label: 干支") and "(3 hits)" in o),

    ("random returns what was asked for",
     ["random", "3"], lambda o: "(3 hits)" in o),

    ("the site's label list is scraped, not hardcoded",
     ["labels"], lambda o: int(o.split()[0]) > 200),

    ("usage instead of a crash when called with nothing",
     [], lambda o: o.startswith("irasutoya.py")),
]


def main():
    failed = 0
    for why, args, ok in CASES:
        try:
            out = run(*args)
            passed = bool(out.strip()) and ok(out)
        except Exception as e:                                   # noqa: BLE001
            out, passed = f"{type(e).__name__}: {e}", False
        print(("PASS  " if passed else "FAIL  ") + why)
        if not passed:
            failed += 1
            print("      args:", args)
            print("      " + "\n      ".join(out.splitlines()[:3]))
    print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
