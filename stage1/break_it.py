#!/usr/bin/env python3
"""
break_it.py - try to BREAK another team's solution (peer-breaking exercise).

It generates many campuses (different seeds and different generator parameters) and looks for one
on which the solution: returns an invalid plan, exceeds the call budget, misses its declared contract
(CONTRACT in the team file), or has a heuristic that overestimates.

  python break_it.py other_team_solution.py --oracle my_oracle.py --tries 40
The optimal cost on these random campuses comes from YOUR oracle (see oracle_template.py), so it must be correct.
Prints the first failing campus (seed + parameters) so the owner can reproduce it with grader.py.
"""
import argparse, itertools, json, random
import grader, campus

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("team_file")
    ap.add_argument("--oracle", required=True, help="your oracle file (see oracle_template.py)")
    ap.add_argument("--tries", type=int, default=40)
    ap.add_argument("--start-seed", type=int, default=5000)
    ap.add_argument("--queries", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=20)
    a = ap.parse_args()
    orc = getattr(grader.load_module(a.oracle), "oracle")
    rng = random.Random(a.start_seed)
    found = []
    for t in range(a.tries):
        seed = a.start_seed + t
        params = {"n": rng.choice([40, 60, 80, 110, 140]), "cap": rng.choice([30, 40, 50, 60, 80]),
                  "charger_frac": rng.choice([0.05, 0.08, 0.12, 0.2]), "one_way_frac": rng.choice([0.0, 0.15, 0.3]),
                  "wait_frac": rng.choice([0.0, 0.15, 0.4])}
        budget = int(grader.SIZES["hidden"]["budget"] * params["n"] / 110)   # bigger campus -> proportionally bigger budget
        rep = grader.grade(a.team_file, [seed], "hidden", a.queries, a.timeout, None, params, budget, quiet=True, oracle=orc)
        r = rep["seeds"][str(seed)]
        problems = []
        for i, q in enumerate(r["queries"]):
            if q["status"] != "returned" or not q.get("valid") or not q.get("meets_contract"):
                problems.append("query %d: %s %s" % (i, q["status"], q.get("message", "") or ("ratio %s" % q.get("ratio"))))
        hc = r.get("heuristic_check")
        if hc and hc.get("violations"):
            problems.append("heuristic overestimates in %d sampled states" % len(hc["violations"]))
        print("try %2d seed %d params %s -> %s" % (t, seed, params, "BROKEN" if problems else "ok"))
        if problems:
            found.append({"seed": seed, "params": params, "problems": problems})
            for pr in problems:
                print("     ", pr)
            break
    if not found:
        print("\nNo failure found in %d tries. Increase --tries or think about which campus property your opponent's design ignores." % a.tries)
    else:
        json.dump(found, open("break_report.json", "w"), indent=1)
        print("\nSaved break_report.json (give it to the owner of the solution).")

if __name__ == "__main__":
    main()
