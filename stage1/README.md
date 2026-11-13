# Delivery robot - project part A (student package)

Files: campus.py (do not edit) - grader.py (run it) - reference.json (do not edit; keep it next to grader.py)
       break_it.py - team_template.py - oracle_template.py - faulty_solver.py
The full instructions are in the project document (Hebrew).

Quick start:
    cp team_template.py team07.py        # then edit team07.py   (Windows: copy team_template.py team07.py)
    python grader.py team07.py --seeds 1 2 3
    python grader.py team07.py --seeds 1007               # your personal campus (team 7)
    python grader.py team07.py --size hidden --seeds 77   # bigger campuses, like the grading ones
    python grader.py team07.py --seeds 42 --oracle my_oracle.py    # any other campus, optimum from YOUR oracle
    python break_it.py other_team.py --oracle my_oracle.py --tries 40

Write your own oracle (a simple, slow, correct solver) starting from oracle_template.py.

Requires Python 3.8+. No third-party packages.
Runs on Windows, macOS and Linux. On Windows you can write `py` instead of `python`.
