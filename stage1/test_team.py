#!/usr/bin/env python3
"""test_team.py - unit tests (U1-U20) on tiny hand-computed worlds, standard library only.

  python test_team.py team_solution.py                    # default heuristic mode of the file
  python test_team.py team_solution.py --mode relaxed     # force HEURISTIC_MODE (design B)
  python test_team.py faulty_solver.py                    # the same tests are used for peer breaking
"""
import importlib.util, math, random, sys, unittest
import campus
from campus import Edge
from my_oracle import oracle

SOL = None          # the module under test, loaded in main()
INF = float("inf")


# ---------------------------------------------------------------- fake world + independent simulator
class FakeWorld:
    """Same interface as campus.make_world; every edges_from / edges_to call is counted."""

    def __init__(self, pos, roads, chargers, capacity=10, charge_time=6, speed=2.0, mepm=1 / 25, budget=10 ** 9):
        self.nodes = tuple(sorted(pos))
        self.pos = dict(pos)
        self.chargers = frozenset(chargers)
        self.capacity, self.charge_time, self.speed_max, self.min_energy_per_meter = capacity, charge_time, speed, mepm
        self.budget = budget
        self._used = 0
        self._out = {u: [] for u in pos}
        self._inn = {u: [] for u in pos}
        for (u, v, length, time, energy) in roads:
            # fixtures must obey the declared bounds, otherwise the heuristic tests are meaningless
            assert length >= math.dist(pos[u], pos[v]) - 1e-9, (u, v)
            assert time >= length / speed - 1e-9, (u, v)
            assert energy >= length * mepm - 1e-9, (u, v)
            self._out[u].append(Edge(v, length, time, energy))
            self._inn[v].append(Edge(u, length, time, energy))

    def _count(self):
        self._used += 1
        if self._used > self.budget:
            raise campus.BudgetExceeded("call budget (%d) exceeded" % self.budget)

    def edges_from(self, u):
        self._count(); return tuple(self._out[u])

    def edges_to(self, v):
        self._count(); return tuple(self._inn[v])

    def calls_used(self):
        return self._used


def simulate(w, s, g, b, plan):
    """Independent plan checker (mirrors campus.validate_plan, no calls counted). Returns (ok, time)."""
    u, t = s, 0
    for a in plan:
        a = tuple(a)
        if len(a) == 2 and a[0] == "move":
            e = next((x for x in w._out[u] if x.to == a[1]), None)
            if e is None or b < e.energy:
                return False, None
            u, b, t = e.to, b - e.energy, t + e.time
        elif a == ("charge",):
            if u not in w.chargers or b >= w.capacity:
                return False, None
            b, t = b + 1, t + w.charge_time
        else:
            return False, None
    return (u == g), (t if u == g else None)


def line_world(**kw):
    # A(0, charger) <-> B(1) <-> C(2); every road 100 m, 60 s, 4 units, both directions
    pos = {0: (0, 0), 1: (100, 0), 2: (200, 0)}
    roads = []
    for u, v in ((0, 1), (1, 2)):
        roads += [(u, v, 100, 60, 4), (v, u, 100, 60, 4)]
    return FakeWorld(pos, roads, {0}, **kw)


def tradeoff_world(**kw):
    # A(0, charger) -> B(1) direct: 100 m, 50 s, 8 units (uphill); via C(2): two roads of 50 m, 30 s, 2 units
    pos = {0: (0, 0), 1: (100, 0), 2: (50, 0)}
    roads = [(0, 1, 100, 50, 8), (0, 2, 50, 30, 2), (2, 1, 50, 30, 2), (1, 0, 100, 50, 4)]
    return FakeWorld(pos, roads, {0}, **kw)


def capacity_world(**kw):
    # A(0, charger) -> M(1, charger) -> G(2); each leg 150 m, 80 s, 6 units; capacity 8
    kw.setdefault("capacity", 8)
    pos = {0: (0, 0), 1: (150, 0), 2: (300, 0)}
    roads = [(0, 1, 150, 80, 6), (1, 2, 150, 80, 6)]
    return FakeWorld(pos, roads, {0, 1}, **kw)


def run(make, s, g, b, **kw):
    w = make(**kw)
    plan = SOL.solve(w, s, g, b)
    ok, cost = simulate(make(**kw), s, g, b, plan)
    return plan, ok, cost, w


# ---------------------------------------------------------------- tests
class Tests(unittest.TestCase):
    def test_U01_start_is_goal(self):
        plan, ok, cost, w = run(line_world, 1, 1, 0)
        self.assertEqual(list(plan), [])
        self.assertEqual(w.calls_used(), 0)

    def test_U02_one_road(self):
        plan, ok, cost, _ = run(line_world, 0, 1, 5)
        self.assertEqual([tuple(a) for a in plan], [("move", 1)])
        self.assertTrue(ok); self.assertEqual(cost, 60)

    def test_U03_battery_exactly_energy(self):
        _, ok, cost, _ = run(line_world, 0, 1, 4)
        self.assertTrue(ok); self.assertEqual(cost, 60)

    def test_U04_exact_charging(self):
        plan, ok, cost, _ = run(line_world, 0, 2, 2)
        self.assertTrue(ok); self.assertEqual(cost, 156)
        self.assertEqual(sum(1 for a in plan if tuple(a) == ("charge",)), 6)

    def test_U05_empty_battery_at_charger(self):
        _, ok, cost, _ = run(line_world, 0, 1, 0)
        self.assertTrue(ok); self.assertEqual(cost, 84)

    def test_U06_no_charger_on_the_way(self):
        self.assertIsNone(oracle(line_world(), 2, 0, 3))
        plan = SOL.solve(line_world(), 2, 0, 3)
        self.assertIsNotNone(plan, "solve must return a list, never None")
        self.assertFalse(simulate(line_world(), 2, 0, 3, plan)[0])

    def test_U07_one_way_road(self):
        mk = lambda **kw: FakeWorld({0: (0, 0), 1: (100, 0)}, [(0, 1, 100, 60, 4)], {0}, **kw)
        self.assertIsNone(oracle(mk(), 1, 0, 5))
        plan = SOL.solve(mk(), 1, 0, 5)
        self.assertIsNotNone(plan, "solve must return a list, never None")
        self.assertFalse(simulate(mk(), 1, 0, 5, plan)[0])

    def test_U08_time_vs_energy(self):
        _, ok, cost, _ = run(tradeoff_world, 0, 1, 4)
        self.assertTrue(ok); self.assertEqual(cost, 60)     # direct would be 4 charges * 6 + 50 = 74
        _, ok, cost, _ = run(tradeoff_world, 0, 1, 8)
        self.assertTrue(ok); self.assertEqual(cost, 50)     # enough battery: the fast uphill road wins

    def test_U09_charge_time_read_from_world(self):
        _, ok, cost, _ = run(tradeoff_world, 0, 1, 4, charge_time=1)
        self.assertTrue(ok); self.assertEqual(cost, 54)

    def test_U10_capacity_forces_midway_charge(self):
        _, ok, cost, _ = run(capacity_world, 0, 2, 0)
        self.assertTrue(ok); self.assertEqual(cost, 232)

    def test_U11_simulator_rejects_bad_charging(self):
        self.assertFalse(simulate(line_world(), 1, 1, 0, [("charge",)])[0])        # no charger
        self.assertFalse(simulate(line_world(), 0, 0, 10, [("charge",)])[0])       # battery full
        self.assertTrue(simulate(line_world(), 0, 0, 9, [("charge",)])[0])

    def test_U12_plan_format(self):
        plan = SOL.solve(line_world(), 0, 2, 2)
        self.assertIsInstance(plan, (list, tuple))
        for a in plan:
            a = tuple(a)
            self.assertTrue((len(a) == 2 and a[0] == "move") or a == ("charge",), a)

    def test_U13_deterministic(self):
        self.assertEqual(list(map(tuple, SOL.solve(tradeoff_world(), 0, 1, 4))),
                         list(map(tuple, SOL.solve(tradeoff_world(), 0, 1, 4))))

    def test_U14_h_zero_at_goal(self):
        for mk in (line_world, tradeoff_world, capacity_world):
            w = mk()
            for b in range(w.capacity + 1):
                self.assertEqual(SOL.heuristic(w, 1, b, 1), 0)

    def test_U15_h_not_increasing_in_battery(self):
        for mk, goal in ((line_world, 2), (tradeoff_world, 1), (capacity_world, 2)):
            w = mk()
            for u in w.nodes:
                hs = [SOL.heuristic(w, u, b, goal) for b in range(w.capacity + 1)]
                for x, y in zip(hs, hs[1:]):
                    self.assertGreaterEqual(x + 1e-9, y, (mk.__name__, u, hs))

    def test_U16_admissible_and_consistent(self):
        for mk, goal in ((line_world, 1), (line_world, 2), (tradeoff_world, 1), (capacity_world, 2)):
            w = mk()
            for u in w.nodes:
                for b in range(w.capacity + 1):
                    h = SOL.heuristic(w, u, b, goal)
                    true = oracle(mk(), u, goal, b)
                    true = INF if true is None else true
                    self.assertLessEqual(h, true + 1e-9, (mk.__name__, u, b))
                    if h == INF:
                        continue
                    for e in w._out[u]:
                        if b >= e.energy:
                            self.assertLessEqual(h, e.time + SOL.heuristic(w, e.to, b - e.energy, goal) + 1e-9)
                    if u in w.chargers and b < w.capacity:
                        self.assertLessEqual(h, w.charge_time + SOL.heuristic(w, u, b + 1, goal) + 1e-9)

    def test_U17_at_most_one_call_per_building(self):
        _, ok, _, w = run(tradeoff_world, 0, 1, 0)
        self.assertTrue(ok)
        self.assertLessEqual(w.calls_used(), len(w.nodes))

    def test_U18_budget_equal_to_n(self):
        _, ok, cost, _ = run(line_world, 0, 2, 2, budget=3)        # raises BudgetExceeded on failure
        self.assertTrue(ok); self.assertEqual(cost, 156)

    def test_U19_two_worlds_in_one_process(self):
        # catches caches keyed by id(world): a freed world's id is often reused by the next one
        for _ in range(20):
            w = tradeoff_world()
            SOL.solve(w, 0, 1, 4)
            del w
            _, ok, cost, _ = run(tradeoff_world, 0, 1, 4, charge_time=1)
            self.assertTrue(ok); self.assertEqual(cost, 54)

    def test_U20_small_real_campus_vs_oracle(self):
        for seed in (11, 12, 13):
            d = campus.generate_data(seed, n=40, cap=40, charger_frac=0.1)
            rng = random.Random(seed)
            for _ in range(4):
                s, g = rng.sample(range(d.n), 2)
                b = rng.randint(4, 20)
                opt = oracle(campus.make_world(d, 10 ** 9), s, g, b)
                plan = SOL.solve(campus.make_world(d, 10 ** 9), s, g, b)
                ok, cost, _ = campus.validate_plan(d, s, g, b, [tuple(a) for a in plan])
                if opt is None:
                    self.assertFalse(ok)
                else:
                    self.assertTrue(ok, (seed, s, g, b)); self.assertEqual(cost, opt, (seed, s, g, b))


def main():
    global SOL
    args = sys.argv[1:]
    mode = None
    if "--mode" in args:
        i = args.index("--mode"); mode = args[i + 1]; del args[i:i + 2]
    path = args[0] if args else "team_solution.py"
    spec = importlib.util.spec_from_file_location("team_solution", path)
    SOL = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(SOL)
    if mode:
        SOL.HEURISTIC_MODE = mode
    print("testing %s (mode: %s)" % (path, getattr(SOL, "HEURISTIC_MODE", "n/a")))
    unittest.main(argv=[sys.argv[0], "-v"] + args[1:], verbosity=2)


if __name__ == "__main__":
    main()
