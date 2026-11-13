"""oracle_template.py - your reference solver ("oracle") for testing.

Write a SIMPLE, SLOW, obviously-correct solver: no heuristic, no cleverness. It is only used to check
other solutions (yours and your opponents').

oracle(world, start, goal, battery) must return the MINIMAL total time (driving + charging) needed to get
from `start` to `goal` beginning with `battery` units, or None if the goal cannot be reached.
Use only the World API. The world given to the oracle has no call budget.

Used by:  python grader.py team07.py --seeds 42 --oracle my_oracle.py
          python break_it.py other_team.py --oracle my_oracle.py
"""


def oracle(world, start, goal, battery):
    raise NotImplementedError("write your uniform-cost search here")
