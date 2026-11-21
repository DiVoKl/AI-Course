"""faulty_solver_fixed.py - faulty_solver.py with the four bugs from the bug-hunt report fixed.
  bug 1 heuristic used b//2 (overestimates)                  -> uses b
  bug 2 world.edges_from(u) called on every state expansion  -> memoised, one call per building
        (and edges_to is shared between the two reverse sweeps)
  bug 3 cache keyed by id(world) (ids are reused)            -> keyed by the world object itself
  bug 4 solve fell off the end and returned None             -> returns []
Everything else is kept as in the original so the diff stays readable."""
import heapq
CONTRACT={"optimal":True}
_cache={}
def _edges_to(world,v):
    inn=_cache["inn"]
    if v not in inn: inn[v]=world.edges_to(v)                      # bug 2: one edges_to call per building
    return inn[v]
def _rev_dijkstra(world,g,key):
    dist={g:0}; pq=[(0,g)]
    while pq:
        c,v=heapq.heappop(pq)
        if dist.get(v,1e18)<c: continue
        for e in _edges_to(world,v):            # e.to = a building from which we can arrive at v
            nc=c+(e.time if key=="time" else e.energy)
            if nc<dist.get(e.to,1e18): dist[e.to]=nc; heapq.heappush(pq,(nc,e.to))
    return dist
def _prep(world,g):
    if _cache.get("world") is not world:                           # bug 3: compare the object, not id(world)
        _cache.clear(); _cache["world"]=world; _cache["inn"]={}; _cache["out"]={}
    if _cache.get("goal")!=g:
        _cache["goal"]=g; _cache["h"]=(_rev_dijkstra(world,g,"time"),_rev_dijkstra(world,g,"energy"))
    return _cache["h"]
def heuristic(world,u,b,g):
    ht,he=_prep(world,g)
    return ht.get(u,1e18)+world.charge_time*max(0,he.get(u,1e18)-b)   # bug 1: b, not b//2
def solve(world,s,g,b0):
    if s==g: return []
    cap=world.capacity; tc=world.charge_time
    pq=[(heuristic(world,s,b0,g),0,s,b0)]; dist={(s,b0):0}; prev={}; closed=set()
    out=_cache["out"]
    while pq:
        f,c,u,b=heapq.heappop(pq)
        if (u,b) in closed: continue
        closed.add((u,b))
        if u==g:
            plan=[]; st=(u,b)
            while st in prev: st,a=prev[st]; plan.append(a)
            return plan[::-1]
        if u not in out: out[u]=world.edges_from(u)                # bug 2: one edges_from call per building
        for e in out[u]:
            if b>=e.energy:
                ns=(e.to,b-e.energy); nc=c+e.time
                if nc<dist.get(ns,1e18): dist[ns]=nc; prev[ns]=((u,b),("move",e.to)); heapq.heappush(pq,(nc+heuristic(world,e.to,ns[1],g),nc,e.to,ns[1]))
        if u in world.chargers and b<cap:
            ns=(u,b+1); nc=c+tc
            if nc<dist.get(ns,1e18): dist[ns]=nc; prev[ns]=((u,b),("charge",)); heapq.heappush(pq,(nc+heuristic(world,u,b+1,g),nc,u,b+1))
    return []                                                      # bug 4: never return None
