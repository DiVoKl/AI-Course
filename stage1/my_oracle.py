"""my_oracle.py - reference solver for testing (uniform-cost search, no heuristic, no tricks).

oracle(world, start, goal, battery) -> minimal total time (driving + charging), or None if unreachable.
Shares no code with the team solution on purpose: an oracle that is wrong together with the solution finds nothing.
"""
import heapq


def oracle(world, start, goal, battery):
    cap, tc, chargers = world.capacity, world.charge_time, world.chargers
    dist = {(start, battery): 0}
    pq = [(0, start, battery)]

    def relax(s, t):
        if t < dist.get(s, float("inf")):
            dist[s] = t
            heapq.heappush(pq, (t, s[0], s[1]))

    while pq:
        t, u, b = heapq.heappop(pq)
        if t > dist[(u, b)]:
            continue                      # stale copy
        if u == goal:
            return t                      # first goal state popped is optimal (all costs > 0)
        for e in world.edges_from(u):     # no budget for the oracle, so no memo
            if b >= e.energy:
                relax((e.to, b - e.energy), t + e.time)
        if u in chargers and b < cap:
            relax((u, b + 1), t + tc)
    return None
