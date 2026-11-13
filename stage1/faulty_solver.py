"""faulty_solver.py - a solution WITH a hidden bug, for the bug-hunt exercise (see the project document).
Find a failing campus by TESTING first, explain the symptom, and only then locate the bug."""
import heapq
CONTRACT={"optimal":True}
_cache={}
def _rev_dijkstra(world,g,key):
    dist={g:0}; pq=[(0,g)]
    while pq:
        c,v=heapq.heappop(pq)
        if dist.get(v,1e18)<c: continue
        for e in world.edges_to(v):            # e.to = a building from which we can arrive at v
            nc=c+(e.time if key=="time" else e.energy)
            if nc<dist.get(e.to,1e18): dist[e.to]=nc; heapq.heappush(pq,(nc,e.to))
    return dist
def _prep(world,g):
    k=(id(world),g)
    if k not in _cache: _cache.clear(); _cache[k]=(_rev_dijkstra(world,g,"time"),_rev_dijkstra(world,g,"energy"))
    return _cache[k]
def heuristic(world,u,b,g):
    ht,he=_prep(world,g)
    return ht.get(u,1e18)+world.charge_time*max(0,he.get(u,1e18)-b//2)
def solve(world,s,g,b0):
    cap=world.capacity; tc=world.charge_time
    pq=[(heuristic(world,s,b0,g),0,s,b0)]; dist={(s,b0):0}; prev={}; closed=set()
    while pq:
        f,c,u,b=heapq.heappop(pq)
        if (u,b) in closed: continue
        closed.add((u,b))
        if u==g:
            plan=[]; st=(u,b)
            while st in prev: st,a=prev[st]; plan.append(a)
            return plan[::-1]
        for e in world.edges_from(u):
            if b>=e.energy:
                ns=(e.to,b-e.energy); nc=c+e.time
                if nc<dist.get(ns,1e18): dist[ns]=nc; prev[ns]=((u,b),("move",e.to)); heapq.heappush(pq,(nc+heuristic(world,e.to,ns[1],g),nc,e.to,ns[1]))
        if u in world.chargers and b<cap:
            ns=(u,b+1); nc=c+tc
            if nc<dist.get(ns,1e18): dist[ns]=nc; prev[ns]=((u,b),("charge",)); heapq.heappush(pq,(nc+heuristic(world,u,b+1,g),nc,u,b+1))
