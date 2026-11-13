"""
team_solution.py - the file you submit (rename it, e.g. team07.py).

You must provide:
  CONTRACT   - what you promise about your solution (see the project document):
               {"optimal": True}          the returned plan always has the minimal total time
               {"factor": 1.2}            the returned plan is at most 1.2 times the minimal total time
  solve(world, start, goal, battery)   - returns a plan: a list of actions
               ("move", building)   drive along a road to the neighbouring building
               ("charge",)          charge 1 battery unit at the current building (it must have a charger)
  heuristic(world, building, battery, goal)   - OPTIONAL but recommended: the lower bound your search
               uses for the remaining time. If CONTRACT is optimal, the grader checks that it never overestimates.

The world object (see the document for details):
  world.nodes, world.pos[b] = (x, y) in meters, world.chargers (set), world.capacity (battery units),
  world.speed_max (m/s), world.charge_time (seconds per battery unit), world.min_energy_per_meter
  world.edges_from(b) -> tuple of Edge(to, length, time, energy)      [counts as 1 call]
  world.edges_to(b)   -> tuple of Edge(to=<a building you can come FROM>, length, time, energy)   [counts as 1 call]
  world.calls_used(), world.budget

RULES: only use the world through these functions. Every edges_from / edges_to call is counted, including
calls made while you compute a heuristic. Exceeding the budget fails the query.
"""

CONTRACT = {"optimal": True}


def heuristic(world, building, battery, goal):
    raise NotImplementedError


def solve(world, start, goal, battery):
    raise NotImplementedError
