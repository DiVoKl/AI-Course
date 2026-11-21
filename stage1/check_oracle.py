#!/usr/bin/env python3
"""check_oracle.py - Q1: verify my_oracle against every optimum and heuristic-check value in reference.json.
Allowed to use campus/grader directly: it is a test, not the solution.
  python check_oracle.py
"""
import json, os, sys, time
import campus, grader
from my_oracle import oracle

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ref = json.load(open(os.path.join(HERE, "reference.json")))
    t0 = time.time()
    nq = ns = bad = 0
    for key, e in ref["entries"].items():
        size, seed = key.split(":")
        d, _ = grader.build(int(seed), size)
        w = campus.make_world(d, 10 ** 9)
        for q, opt in zip(e["queries"], e["opt"]):
            got = oracle(w, *q)
            nq += 1
            if got != opt:
                bad += 1
                print("MISMATCH %s query %s: oracle %s, reference %s" % (key, q, got, opt))
        goal = e["heur_goal"]
        for u, b, true in e["heur_states"]:
            got = 0 if u == goal else oracle(w, u, goal, b)
            ns += 1
            if got != true:
                bad += 1
                print("MISMATCH %s state (%s, %s): oracle %s, reference %s" % (key, u, b, got, true))
    print("%d campuses, %d queries, %d heuristic states, %d mismatches, %.1fs"
          % (len(ref["entries"]), nq, ns, bad, time.time() - t0))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
