"""Grid maze router (A*, 8-direction, 2 layers) for the avionics panel."""
import heapq
import math
import numpy as np
from scipy import ndimage

import board as B

RES = 0.25
NX = int(round(B.W / RES)) + 1
NY = int(round(B.H / RES)) + 1
L = {"F": 0, "B": 1}
FREE, NONET = -1, -2

THR = (B.CLEAR + B.TRACE_W / 2) / RES + 0.5          # trace centre keep distance (cells)
THR_VIA = (B.CLEAR + B.VIA_D / 2) / RES + 0.5
LAYER_COST = (1.15, 1.0)    # no top pour on the 4-layer board
VIA_COST = 60.0             # in cells

yy, xx = np.mgrid[0:NY, 0:NX]
XS, YS = xx * RES, yy * RES


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return np.hypot(px - x1, py - y1)
    t = np.clip(((px - x1) * dx + (py - y1) * dy) / l2, 0, 1)
    return np.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def stamp_rect(arr, x0, y0, x1, y1, val, grow=0.0):
    m = (XS >= x0 - grow - RES * 0.5) & (XS <= x1 + grow + RES * 0.5) & (YS >= y0 - grow - RES * 0.5) & (YS <= y1 + grow + RES * 0.5)
    arr[m] = val


def stamp_capsule(arr, x1, y1, x2, y2, r, val):
    pad = r + RES
    ix0 = max(int((min(x1, x2) - pad) / RES), 0)
    ix1 = min(int((max(x1, x2) + pad) / RES) + 2, NX)
    iy0 = max(int((min(y1, y2) - pad) / RES), 0)
    iy1 = min(int((max(y1, y2) + pad) / RES) + 2, NY)
    sub = seg_dist(XS[iy0:iy1, ix0:ix1], YS[iy0:iy1, ix0:ix1], x1, y1, x2, y2)
    m = sub <= r + RES * 0.5
    arr[iy0:iy1, ix0:ix1][m] = val


class Router:
    def __init__(self, pads, netnames):
        self.pads = pads
        self.netid = {n: i for i, n in enumerate(netnames)}
        self.owner = np.full((2, NY, NX), FREE, dtype=np.int16)
        self.segments = []   # (x1,y1,x2,y2,layer,net)
        self.vias = []       # (x,y,net)
        # board edge
        edge = (XS < B.EDGE_CLEAR) | (XS > B.W - B.EDGE_CLEAR) | (YS < B.EDGE_CLEAR) | (YS > B.H - B.EDGE_CLEAR)
        self.owner[:, edge] = NONET
        for layers, kind, p in B.keepouts():
            for ly in layers:
                if kind == "circle":
                    stamp_capsule(self.owner[L[ly]], p[0], p[1], p[0], p[1], p[2], NONET)
                else:
                    m = (XS >= p[0]) & (XS <= p[2]) & (YS >= p[1]) & (YS <= p[3])
                    self.owner[L[ly]][m] = NONET
        for pad in pads:
            v = self.netid[pad.net] if pad.net else NONET
            x1, y1, x2, y2, r = pad.capsule()
            for ly in pad.layers:
                if pad.shape == "rect":
                    stamp_rect(self.owner[L[ly]], *pad.rect(), v)
                else:
                    stamp_capsule(self.owner[L[ly]], x1, y1, x2, y2, r, v)

    def add_segment(self, x1, y1, x2, y2, ly, net, w=None):
        w = w or B.TRACE_W
        self.segments.append((x1, y1, x2, y2, ly, net, w))
        stamp_capsule(self.owner[L[ly]], x1, y1, x2, y2, w / 2, self.netid[net])

    def add_via(self, x, y, net, d=None, drill=None):
        d, drill = d or B.VIA_D, drill or B.VIA_DRILL
        self.vias.append((x, y, net, d, drill))
        for ly in (0, 1):
            stamp_capsule(self.owner[ly], x, y, x, y, d / 2, self.netid[net])

    def pad_cells(self, pad):
        if pad.shape == "rect":
            x0, y0, x1, y1 = pad.rect()
            cells = []
            for iy in range(max(int(y0 / RES), 0), min(int(y1 / RES) + 2, NY)):
                for ix in range(max(int(x0 / RES), 0), min(int(x1 / RES) + 2, NX)):
                    if x0 + 0.05 <= ix * RES <= x1 - 0.05 and y0 + 0.05 <= iy * RES <= y1 - 0.05:
                        cells.append((iy, ix))
            if not cells:
                cells.append((int(round(pad.y / RES)), int(round(pad.x / RES))))
            return cells
        x1, y1, x2, y2, r = pad.capsule()
        ix0, ix1 = int((min(x1, x2) - r) / RES) - 1, int((max(x1, x2) + r) / RES) + 2
        iy0, iy1 = int((min(y1, y2) - r) / RES) - 1, int((max(y1, y2) + r) / RES) + 2
        cells = []
        for iy in range(max(iy0, 0), min(iy1, NY)):
            for ix in range(max(ix0, 0), min(ix1, NX)):
                d = seg_dist(ix * RES, iy * RES, x1, y1, x2, y2)
                if d <= max(r - 0.2, 0.0):
                    cells.append((iy, ix))
        if not cells:
            cells.append((int(round(pad.y / RES)), int(round(pad.x / RES))))
        return cells

    def route(self, net, pa, pb=None, goal_mask=None):
        nid = self.netid[net]
        feas = []
        dist = []
        for ly in (0, 1):
            obst = (self.owner[ly] != FREE) & (self.owner[ly] != nid)
            d = ndimage.distance_transform_edt(~obst)
            dist.append(d)
            feas.append(d >= THR)
        via_ok = (dist[0] >= THR_VIA) & (dist[1] >= THR_VIA)
        # own pads are always enterable
        start, goal = set(), set()
        for (iy, ix) in self.pad_cells(pa):
            for ly in pa.layers:
                start.add((L[ly], iy, ix))
        if pb is not None:
            for (iy, ix) in self.pad_cells(pb):
                for ly in pb.layers:
                    goal.add((L[ly], iy, ix))
            gx, gy = pb.x / RES, pb.y / RES

            def h(iy, ix):
                dx, dy = abs(ix - gx), abs(iy - gy)
                return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)
        else:
            for l in (0, 1):
                ys, xs = np.nonzero(goal_mask[l])
                goal.update((l, int(a), int(b)) for a, b in zip(ys, xs))
            hd = ndimage.distance_transform_edt(~(goal_mask[0] | goal_mask[1]))

            def h(iy, ix):
                return hd[iy, ix]
        for (l, iy, ix) in start | goal:
            feas[l][iy, ix] = True

        g = np.full((2, NY, NX), np.inf, dtype=np.float32)
        parent = {}
        heap = []
        for s in start:
            g[s] = 0
            heapq.heappush(heap, (h(s[1], s[2]), 0.0, s))
            parent[s] = None
        dirs = [(-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1),
                (-1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)), (1, 1, math.sqrt(2))]
        found = None
        while heap:
            f, gc, node = heapq.heappop(heap)
            if gc > g[node]:
                continue
            if node in goal:
                found = node
                break
            l, iy, ix = node
            for dy, dx, c in dirs:
                ny_, nx_ = iy + dy, ix + dx
                if 0 <= ny_ < NY and 0 <= nx_ < NX and feas[l][ny_, nx_]:
                    if dx and dy and not (feas[l][iy, nx_] and feas[l][ny_, ix]):
                        continue
                    ng = gc + c * LAYER_COST[l]
                    nn = (l, ny_, nx_)
                    if ng < g[nn]:
                        g[nn] = ng
                        parent[nn] = node
                        heapq.heappush(heap, (ng + h(ny_, nx_), ng, nn))
            if via_ok[iy, ix]:
                nn = (1 - l, iy, ix)
                ng = gc + VIA_COST
                if ng < g[nn]:
                    g[nn] = ng
                    parent[nn] = node
                    heapq.heappush(heap, (ng + h(iy, ix), ng, nn))
        if not found:
            return False
        path = []
        n = found
        while n is not None:
            path.append(n)
            n = parent[n]
        path.reverse()
        self._commit(net, path, pa, pb)
        return True

    def _commit(self, net, path, pa, pb):
        self.last_path = path
        # split into runs per layer
        runs, cur = [], [path[0]]
        for n in path[1:]:
            if n[0] != cur[-1][0]:
                runs.append(cur)
                cur = [n]
            else:
                cur.append(n)
        runs.append(cur)
        for i in range(len(runs) - 1):
            _, iy, ix = runs[i][-1]
            self.add_via(ix * RES, iy * RES, net)
        for ri, run in enumerate(runs):
            ly = "F" if run[0][0] == 0 else "B"
            pts = [(n[2] * RES, n[1] * RES) for n in run]
            if ri == 0:
                pts[0] = (pa.x, pa.y)
            if ri == len(runs) - 1 and pb is not None:
                pts[-1] = (pb.x, pb.y)
            # simplify collinear
            simp = [pts[0]]
            for j in range(1, len(pts) - 1):
                ax, ay = simp[-1]
                bx, by = pts[j]
                cx, cy = pts[j + 1]
                if abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) > 1e-9:
                    simp.append(pts[j])
            simp.append(pts[-1])
            for j in range(len(simp) - 1):
                (x1, y1), (x2, y2) = simp[j], simp[j + 1]
                if (x1, y1) != (x2, y2):
                    self.add_segment(x1, y1, x2, y2, ly, net)


    def route_tree(self, net, pads, seed=None):
        """Connect all pads of a net: grow a tree from pads[0]."""
        tree = np.zeros((2, NY, NX), bool)
        if seed is not None:                      # pre-routed bus: every pad is routed onto it
            tree |= seed
            for p in pads:
                if not self.route(net, p, goal_mask=tree):
                    return False
                for n in self.last_path:
                    tree[n[0], n[1], n[2]] = True
            return True

        def add_pad(p):
            x1, y1, x2, y2, r = p.capsule()
            for ly in p.layers:
                tmp = np.zeros((NY, NX), np.int8)
                stamp_capsule(tmp, x1, y1, x2, y2, max(r - 0.25, 0.1), 1)
                tree[L[ly]] |= tmp.astype(bool)

        add_pad(pads[0])
        todo = list(pads[1:])
        done = [pads[0]]
        while todo:
            todo.sort(key=lambda p: min(math.hypot(p.x - q.x, p.y - q.y) for q in done))
            p = todo.pop(0)
            if not self.route(net, p, goal_mask=tree):
                return False
            for n in self.last_path:
                tree[n[0], n[1], n[2]] = True
            add_pad(p)
            done.append(p)
        return True
