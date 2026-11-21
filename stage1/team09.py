"""
team09.py - delivery robot, stage 1 (team 9).

A* over states (building, battery). Cost = total time (driving + charging).
  - HEURISTIC_MODE = "geometric" (design A, default): straight-line relaxation, costs 0 calls;
    edges_from is memoised, so each building costs at most one call  ->  calls_used() <= n.
  - HEURISTIC_MODE = "relaxed" (design B): three reverse Dijkstras on the real graph built from
    edges_to only (exactly one call per building that can reach the goal), forward graph rebuilt from them.
Both heuristics are admissible and consistent (proofs in the design document).
"""
import heapq
import math

CONTRACT = {"optimal": True}
HEURISTIC_MODE = "geometric"          # "geometric" (design A) | "relaxed" (design B)
INF = float("inf")
EPS = 1e-9                            # guards CEIL against float error, e.g. 100 * 0.07 = 7.000000000000001

# Module-level memo. The grader runs each query in a fresh process, so it starts empty per query.
# It is keyed by the world OBJECT (not id(world)): ids are reused after a world is freed.
_MEMO = {"world": None}


def _ensure_world(world):
    if _MEMO["world"] is not world:
        _MEMO.clear()
        _MEMO.update(world=world, out={}, inn={}, goal=None, HT={}, HE={}, HC={}, OUT={})


# ---------------------------------------------------------------- access layer (the only place calls happen)
def _edges_from(world, u):
    _ensure_world(world)
    out = _MEMO["out"]
    if u not in out:
        out[u] = world.edges_from(u)              # 1 call, never repeated for u
    return out[u]


def _edges_to(world, v):
    _ensure_world(world)
    inn = _MEMO["inn"]
    if v not in inn:
        inn[v] = world.edges_to(v)                # Edge(to=u, ...) means a road u -> v
    return inn[v]


def _neighbours(world, u, goal):
    if HEURISTIC_MODE == "geometric":
        return _edges_from(world, u)
    _prepare(world, goal)
    return _MEMO["OUT"].get(u, ())


# ---------------------------------------------------------------- heuristic A: geometric, 0 calls
def _h_geometric(world, u, b, goal):
    if u == goal:
        return 0
    d = math.dist(world.pos[u], world.pos[goal])
    t_drive = d / world.speed_max
    e_need = math.ceil(d * world.min_energy_per_meter - EPS)
    return t_drive + world.charge_time * max(0, e_need - b)


# ---------------------------------------------------------------- heuristic B: relaxations on the real graph
def _reverse_dijkstra(world, goal, weight):
    dist = {goal: 0}
    pq = [(0, goal)]
    while pq:
        c, v = heapq.heappop(pq)
        if c > dist[v]:
            continue
        for e in _edges_to(world, v):             # e.to is the source building of the road
            nc = c + weight(e)
            if nc < dist.get(e.to, INF):
                dist[e.to] = nc
                heapq.heappush(pq, (nc, e.to))
    return dist


def _prepare(world, goal):
    _ensure_world(world)
    if _MEMO["goal"] == goal:
        return
    tc = world.charge_time
    _MEMO["HT"] = _reverse_dijkstra(world, goal, lambda e: e.time)
    _MEMO["HE"] = _reverse_dijkstra(world, goal, lambda e: e.energy)
    _MEMO["HC"] = _reverse_dijkstra(world, goal, lambda e: e.time + tc * e.energy)
    out = {}
    for v, edges in _MEMO["inn"].items():         # rebuild the forward graph, zero extra calls
        for e in edges:
            out.setdefault(e.to, []).append(type(e)(v, e.length, e.time, e.energy))
    _MEMO["OUT"] = out
    _MEMO["goal"] = goal


def _h_relaxed(world, u, b, goal):
    if u == goal:
        return 0
    _prepare(world, goal)
    ht = _MEMO["HT"]
    if u not in ht:
        return INF                                # goal unreachable even ignoring the battery
    tc = world.charge_time
    return max(ht[u] + tc * max(0, _MEMO["HE"][u] - b), _MEMO["HC"][u] - tc * b)


def heuristic(world, building, battery, goal):
    if HEURISTIC_MODE == "geometric":
        return _h_geometric(world, building, battery, goal)
    return _h_relaxed(world, building, battery, goal)


# ---------------------------------------------------------------- A*
def _successors(world, u, b, goal):
    for e in _neighbours(world, u, goal):
        if b >= e.energy:
            yield e.to, b - e.energy, e.time, ("move", e.to)
    if u in world.chargers and b < world.capacity:
        yield u, b + 1, world.charge_time, ("charge",)


def _dominated(closed_list, b, c):
    # an already-closed state at the same building with >= battery AND <= time can replay any continuation
    for b2, c2 in closed_list:
        if b2 >= b and c2 <= c:
            return True
    return False


def _reconstruct(parent, s):
    plan = []
    while s in parent:
        s, action = parent[s]
        plan.append(action)
    plan.reverse()
    return plan


def solve(world, start, goal, battery):
    if start == goal:                             # before any API call
        return []
    h0 = heuristic(world, start, battery, goal)
    if h0 == INF:
        return []                                 # never return None
    g = {(start, battery): 0}
    parent = {}
    closed_at = {}
    pq = [(h0, 0, -battery, start, battery)]      # ties: smaller g, then more battery
    while pq:
        _f, c, _nb, u, b = heapq.heappop(pq)
        if c > g[(u, b)]:
            continue                              # stale entry
        if u == goal:
            return _reconstruct(parent, (u, b))   # consistent h: first goal popped is optimal
        lst = closed_at.setdefault(u, [])
        if _dominated(lst, b, c):
            continue
        lst.append((b, c))
        for v, nb, cost, action in _successors(world, u, b, goal):
            nc = c + cost
            if nc < g.get((v, nb), INF):
                h = heuristic(world, v, nb, goal)
                if h == INF:
                    continue                      # dead end
                g[(v, nb)] = nc
                parent[(v, nb)] = ((u, b), action)
                heapq.heappush(pq, (nc + h, nc, -nb, v, nb))
    return []                                     # goal unreachable
