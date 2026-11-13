#!/usr/bin/env python3
"""
grader.py - runs a team's solution on generated campuses and checks it.

Examples:
  python grader.py team_solution.py --seeds 1 2 3                  # public campuses
  python grader.py team_solution.py --seeds 1007                   # your personal campus (team 7)
  python grader.py team_solution.py --size hidden --seeds 77 78    # larger campuses, similar to the grading ones
  python grader.py team_solution.py --seeds 1 2 --predictions predictions.json
  python grader.py team_solution.py --seeds 42 --oracle my_oracle.py   # any seed, optimum from YOUR oracle

The optimal costs for the published campuses are read from reference.json (keep it next to this file).
Writes results to results_<team>.json (kept for grading; contains no personal data).
"""
import argparse, importlib.util, json, math, multiprocessing as mp, os, random, sys, time
import campus

HERE = os.path.dirname(os.path.abspath(__file__))

SIZES = {
    "public": dict(n=60, cap=60, charger_frac=0.12, budget=1500),
    "hidden": dict(n=110, cap=50, charger_frac=0.08, budget=1200),
}


def load_module(path):
    spec = importlib.util.spec_from_file_location("team_solution", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(seed, size, change=None, params=None):
    p = dict(SIZES[size]); p.update(params or {})
    budget = p.pop("budget")
    d = campus.generate_data(seed, **p)
    return d, budget


# ---------------------------------------------------------------- reference data
class NoReference(Exception):
    pass


def gen_queries(d, k, seed, optimum):
    """The k test queries of a campus: random far-apart pairs, only solvable ones (optimum(q) < inf)."""
    rng = random.Random(seed * 7919 + 13)
    qs = []
    while len(qs) < k:
        s, g = rng.sample(range(d.n), 2)
        if math.dist(d.pos[s], d.pos[g]) >= 400:
            q = (s, g, rng.randint(max(4, d.cap // 8), d.cap // 2))
            if optimum(q) < float("inf"):
                qs.append(q)
    return qs


def _inf(x):
    return float("inf") if x is None else x


def reference_from_file(seed, size, params, k):
    path = os.path.join(HERE, "reference.json")
    if not os.path.exists(path):
        raise NoReference("reference.json is missing - it must be in the same folder as grader.py")
    ref = json.load(open(path))
    e = ref["entries"].get("%s:%s" % (size, seed))
    if e is None or params:
        raise NoReference("no reference data for campus seed %s (size %s). Reference data exists for seeds %s. "
                          "For any other campus run with --oracle your_oracle.py. If your team number is not covered, "
                          "ask the instructor for an updated reference.json" % (seed, size, ref["seeds_text"]))
    k = min(k, len(e["queries"]))
    return dict(queries=[tuple(q) for q in e["queries"][:k]], opt=[_inf(x) for x in e["opt"][:k]],
                goal=e["heur_goal"], states=[(u, b, _inf(t)) for u, b, t in e["heur_states"]])


def reference_from_oracle(oracle, seed, size, params, k, samples=60):
    d, _ = build(seed, size, None, params)
    world = campus.make_world(d, 10 ** 9)
    cache = {}
    def optimum(q):
        if q not in cache:
            r = oracle(world, *q)
            cache[q] = float("inf") if r is None else float(r)
        return cache[q]
    qs = gen_queries(d, k, seed, optimum)
    goal = qs[0][1]
    rng = random.Random(seed + 5)
    states = [(rng.randrange(d.n), rng.randint(0, d.cap)) for _ in range(samples)]
    return dict(queries=qs, opt=[optimum(q) for q in qs], goal=goal,
                states=[(u, b, optimum((u, goal, b)) if u != goal else 0) for u, b in states])


# ---------------------------------------------------------------- sandboxed runs
def _blocked(*a, **k):
    raise RuntimeError("forbidden: use only the World API (world.edges_from / world.edges_to ...)")


def _lock_campus():
    """Inside the sandboxed solver process, remove every way to reach the raw campus data."""
    for name in ("generate_data", "validate_plan", "make_world"):
        setattr(campus, name, _blocked)


def _worker(path, seed, size, change, params, query, budget, conn):
    t0 = time.process_time()
    try:
        d, b0 = build(seed, size, change, params)
        world = campus.make_world(d, budget)
        _lock_campus()
        mod = load_module(path)
        plan = mod.solve(world, query[0], query[1], query[2])
        conn.send({"status": "returned", "plan": [list(a) for a in plan], "calls": world.calls_used(),
                   "secs": time.process_time() - t0})
    except campus.BudgetExceeded:
        conn.send({"status": "over_budget", "calls": budget + 1, "secs": time.process_time() - t0})
    except Exception as ex:  # noqa
        conn.send({"status": "error", "error": "%s: %s" % (type(ex).__name__, ex), "secs": time.process_time() - t0})


def run_query(path, seed, size, change, params, query, budget, timeout):
    parent, child = mp.Pipe(duplex=False)
    pr = mp.Process(target=_worker, args=(path, seed, size, change, params, query, budget, child))
    pr.start()
    if parent.poll(timeout):
        res = parent.recv()
    else:
        res = {"status": "timeout", "secs": timeout}
    pr.join(1)
    if pr.is_alive():
        pr.terminate()
    return res


def _heur_worker(path, seed, size, change, params, goal, states, conn):
    try:
        d, _ = build(seed, size, change, params)
        world = campus.make_world(d, 10 ** 9)
        _lock_campus()
        mod = load_module(path)
        bad = []
        for (u, b, true) in states:
            h = mod.heuristic(world, u, b, goal)
            if h > true + 1e-9:
                bad.append({"node": u, "battery": b, "goal": goal, "h": h, "true": true})
        conn.send({"checked": len(states), "violations": bad})
    except Exception as ex:  # noqa
        conn.send({"error": "%s: %s" % (type(ex).__name__, ex)})


def check_heuristic(path, seed, size, change, params, goal, states, timeout=60):
    parent, child = mp.Pipe(duplex=False)
    pr = mp.Process(target=_heur_worker, args=(path, seed, size, change, params, goal, states, child))
    pr.start()
    res = parent.recv() if parent.poll(timeout) else {"error": "timeout"}
    pr.join(1)
    if pr.is_alive():
        pr.terminate()
    return res


# ---------------------------------------------------------------- grading
def grade(path, seeds, size="public", queries=5, timeout=20, change=None, params=None, budget=None, quiet=False,
          oracle=None):
    mod = load_module(path)
    contract = getattr(mod, "CONTRACT", {"optimal": True})
    factor = 1.0 if contract.get("optimal", False) else float(contract.get("factor", 1.0))
    report = {"team_file": os.path.basename(path), "size": size, "change": change, "contract_factor": factor,
              "seeds": {}, "has_heuristic": hasattr(mod, "heuristic")}
    for seed in seeds:
        d, bud = build(seed, size, change, params)
        bud = budget or bud
        try:
            if oracle is None:
                ref = reference_from_file(seed, size, params, queries)
            else:
                ref = reference_from_oracle(oracle, seed, size, params, queries)
        except NoReference as ex:
            report["seeds"][str(seed)] = {"skipped": str(ex)}
            if not quiet:
                print("\n=== campus seed %s: SKIPPED - %s" % (seed, ex))
            continue
        if not quiet and len(ref["queries"]) < queries:
            print("\n(note: only %d reference queries are available for seed %s)" % (len(ref["queries"]), seed))
        rows = []
        for i, q in enumerate(ref["queries"]):
            res = run_query(path, seed, size, change, params, q, bud, timeout)
            row = {"query": list(q), "status": res["status"], "calls": res.get("calls"), "secs": round(res["secs"], 2)}
            opt = ref["opt"][i]
            row["optimal_cost"] = opt
            if res["status"] == "returned":
                ok, cost, msg = campus.validate_plan(d, q[0], q[1], q[2], [tuple(a) for a in res["plan"]])
                row["valid"] = ok; row["message"] = msg
                if ok:
                    row["cost"] = cost; row["ratio"] = round(cost / opt, 4)
                    row["meets_contract"] = cost <= factor * opt + 1e-9
            elif res["status"] == "error":
                row["message"] = res["error"]
            rows.append(row)
        passed = sum(1 for r in rows if r.get("meets_contract"))
        calls = [r["calls"] for r in rows if r.get("calls") is not None and r["status"] == "returned"]
        report["seeds"][str(seed)] = {"budget": bud, "queries": rows, "passed": passed, "total": len(rows),
                                      "mean_calls": round(sum(calls) / len(calls)) if calls else None}
        if hasattr(mod, "heuristic") and factor == 1.0:
            report["seeds"][str(seed)]["heuristic_check"] = check_heuristic(path, seed, size, change, params,
                                                                          ref["goal"], ref["states"])
        if not quiet:
            print_seed(seed, report["seeds"][str(seed)])
    return report


def print_seed(seed, r):
    print("\n=== campus seed %s   (call budget per query: %d)" % (seed, r["budget"]))
    for i, q in enumerate(r["queries"]):
        extra = q.get("message", "")
        if q["status"] == "returned" and q.get("valid"):
            extra = "cost %s vs optimal %s (x%.3f) %s" % (q["cost"], q["optimal_cost"], q["ratio"], "OK" if q["meets_contract"] else "MISSES CONTRACT")
        print("  query %d: %-11s calls=%-6s time=%5.2fs  %s" % (i, q["status"], q.get("calls"), q["secs"], extra))
    print("  passed %d/%d, mean calls %s" % (r["passed"], r["total"], r["mean_calls"]))
    hc = r.get("heuristic_check")
    if hc:
        if "error" in hc:
            print("  heuristic check: ERROR %s" % hc["error"])
        elif hc["violations"]:
            v = hc["violations"][0]
            print("  heuristic check: %d of %d sampled states OVERESTIMATE (e.g. node %s battery %s: h=%.1f > true %.1f)" % (len(hc["violations"]), hc["checked"], v["node"], v["battery"], v["h"], v["true"]))
        else:
            print("  heuristic check: no overestimates in %d sampled states" % hc["checked"])


def prediction_report(report, pred_path):
    pred = json.load(open(pred_path))
    print("\n=== predictions vs measurements (mean calls per query)")
    for seed, r in report["seeds"].items():
        if seed in pred and r.get("mean_calls"):
            ratio = r["mean_calls"] / float(pred[seed])
            print("  seed %s: predicted %s, measured %s  (measured/predicted = %.2f) %s" % (seed, pred[seed], r["mean_calls"], ratio, "within a factor of 2" if 0.5 <= ratio <= 2 else "OFF by more than 2x - explain in the report"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("team_file")
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--size", choices=list(SIZES), default="public")
    ap.add_argument("--queries", type=int, default=5)
    ap.add_argument("--timeout", type=float, default=20)
    ap.add_argument("--budget", type=int, default=None)
    ap.add_argument("--predictions", default=None)
    ap.add_argument("--oracle", default=None, help="your own oracle file: use it instead of reference.json (any seed)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    orc = getattr(load_module(a.oracle), "oracle") if a.oracle else None
    rep = grade(a.team_file, a.seeds, a.size, a.queries, a.timeout, None, None, a.budget, oracle=orc)
    if a.predictions:
        prediction_report(rep, a.predictions)
    out = a.out or "results_%s.json" % os.path.splitext(os.path.basename(a.team_file))[0]
    json.dump(rep, open(out, "w"), indent=1)
    print("\nresults written to", out)
