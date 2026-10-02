"""Small design-rule-aware grid router (2 layers) for the Vamora75 controller area.

* 0.05 mm grid, layers F.Cu / B.Cu, 8-connected moves + vias.
* Clearance is evaluated with Euclidean distance fields (scipy EDT) of other-net copper,
  drilled holes, the board edge and keepouts, so the result is exact to ~±0.035 mm;
  that rasterisation error is added as a safety margin.
* A* with an exact Euclidean heuristic (EDT of the target), turn and via costs.
Everything is in board-local millimetres (Y down).
"""
from __future__ import annotations

import heapq
import math

import numpy as np
from matplotlib.path import Path as MPath
from scipy.ndimage import distance_transform_edt
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

LAYERS = ("F.Cu", "B.Cu")
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


class Router:
    def __init__(self, x0, y0, x1, y1, res=0.05, board=None, edge_clear=0.4):
        self.res = res
        self.x0, self.y0 = x0, y0
        self.nx = int(math.ceil((x1 - x0) / res)) + 1
        self.ny = int(math.ceil((y1 - y0) / res)) + 1
        self.owner = {l: np.full((self.ny, self.nx), -1, np.int32) for l in LAYERS}
        self.holes = np.zeros((self.ny, self.nx), bool)
        self.hole_net = np.full((self.ny, self.nx), -1, np.int32)   # -1 NPTH / unknown
        self.no_track = {l: np.zeros((self.ny, self.nx), bool) for l in LAYERS}
        self.no_via = np.zeros((self.ny, self.nx), bool)
        self.outside = np.zeros((self.ny, self.nx), bool)
        self.netid, self.netname = {}, []
        self.tracks, self.vias = [], []
        self.ilayer = []          # (x, y, net) points that connect F.Cu and B.Cu (vias, plated holes)
        self.margin = res * 1.0
        self.edge_clear = edge_clear
        gx = self.x0 + np.arange(self.nx) * res
        gy = self.y0 + np.arange(self.ny) * res
        self.GX, self.GY = np.meshgrid(gx, gy)
        if board is not None:
            self.outside = ~self._mask(board)
        self._edge_d = distance_transform_edt(~self.outside) * res if self.outside.any() else np.full((self.ny, self.nx), 1e9)

    # ---------------------------------------------------------------- rasterisation
    def nid(self, net):
        if net not in self.netid:
            self.netid[net] = len(self.netname)
            self.netname.append(net)
        return self.netid[net]

    def _mask(self, geom):
        m = np.zeros((self.ny, self.nx), bool)
        polys = [geom] if isinstance(geom, Polygon) else list(getattr(geom, "geoms", []))
        for p in polys:
            if p.is_empty or not isinstance(p, Polygon):
                continue
            x0, y0, x1, y1 = p.bounds
            i0 = max(int((x0 - self.x0) / self.res) - 1, 0)
            i1 = min(int((x1 - self.x0) / self.res) + 2, self.nx)
            j0 = max(int((y0 - self.y0) / self.res) - 1, 0)
            j1 = min(int((y1 - self.y0) / self.res) + 2, self.ny)
            if i0 >= i1 or j0 >= j1:
                continue
            pts = np.c_[self.GX[j0:j1, i0:i1].ravel(), self.GY[j0:j1, i0:i1].ravel()]
            inside = MPath(np.asarray(p.exterior.coords)).contains_points(pts)
            for h in p.interiors:
                inside &= ~MPath(np.asarray(h.coords)).contains_points(pts)
            m[j0:j1, i0:i1] |= inside.reshape(j1 - j0, i1 - i0)
        return m

    def add_copper(self, geom, layers, net):
        m = self._mask(geom)
        k = self.nid(net) if net else -3          # -3 = copper with no net (e.g. NC pad)
        for l in layers:
            if l in self.owner:
                self.owner[l][m] = k

    def add_hole(self, geom, net=None):
        m = self._mask(geom)
        self.holes |= m
        if net:
            self.hole_net[m] = self.nid(net)

    def add_keepout(self, geom, layers, tracks=True, vias=True):
        m = self._mask(geom)
        for l in layers:
            if tracks and l in self.no_track:
                self.no_track[l] |= m
        if vias:
            self.no_via |= m

    # ---------------------------------------------------------------- helpers
    def cell(self, x, y):
        return int(round((y - self.y0) / self.res)), int(round((x - self.x0) / self.res))

    def xy(self, j, i):
        return self.x0 + i * self.res, self.y0 + j * self.res

    def _free(self, net, w, clr, hole_clr=0.25):
        k = self.netid.get(net, -99)
        other_holes = self.holes & (self.hole_net != k)
        hd = distance_transform_edt(~other_holes) * self.res if other_holes.any() else np.full((self.ny, self.nx), 1e9)
        free, dists = {}, {}
        for l in LAYERS:
            o = self.owner[l]
            obst = (o != -1) & (o != k)
            d = distance_transform_edt(~obst) * self.res
            dists[l] = d
            ok = (d >= w / 2 + clr + self.margin) & (hd >= w / 2 + hole_clr + self.margin) & \
                 (self._edge_d >= w / 2 + self.edge_clear + self.margin) & ~self.no_track[l]
            free[l] = ok
        return free, dists, hd

    # ---------------------------------------------------------------- A*
    def route(self, net, src, dst, w=0.2, clr=0.2, via_d=0.6, via_drill=0.3, layers=LAYERS,
              via_cost=1.6, turn_cost=0.15, clr_map=None, window=None, max_exp=4_000_000, prefer=None):
        """src/dst: list of (layer, shapely geom) regions belonging to `net` (start / goal).
        clr_map: optional (geom, clearance) relaxed-clearance zone (e.g. QFN fan-out).
        Returns list of (layer, [(x,y),...]) segments and list of via (x,y) or None."""
        free, dists, hd = self._free(net, w, clr)
        if clr_map is not None:
            zone = self._mask(clr_map[0])
            free2, _, _ = self._free(net, w, clr_map[1])
            for l in LAYERS:
                free[l] = np.where(zone, free2[l], free[l])
        via_r = via_d / 2
        hd_all = distance_transform_edt(~self.holes) * self.res if self.holes.any() else np.full((self.ny, self.nx), 1e9)
        via_ok = (dists["F.Cu"] >= via_r + clr + self.margin) & (dists["B.Cu"] >= via_r + clr + self.margin) & \
                 (hd >= via_r + 0.25 + self.margin) & (hd_all >= via_drill / 2 + 0.25 + self.margin) & \
                 (self._edge_d >= via_r + self.edge_clear + self.margin) & ~self.no_via
        lidx = {l: n for n, l in enumerate(LAYERS)}
        allowed = [l in layers for l in LAYERS]
        # start / goal masks
        S = np.zeros((2, self.ny, self.nx), bool)
        G = np.zeros((2, self.ny, self.nx), bool)
        def tomask(g):
            if isinstance(g, np.ndarray):
                return g
            return self._mask(g) if not isinstance(g, Point) else self._mask(g.buffer(self.res * 0.8))
        for l, g in src:
            m = tomask(g)
            S[lidx[l]] |= m
        comp = self.component(net, S)
        for n in range(2):
            S[n] |= comp[n]
            fs = S[n] & free[LAYERS[n]]
            if fs.any():
                S[n] = fs
        want_via = isinstance(dst, str) and dst == "via"
        if isinstance(dst, str) and dst == "net":
            dst = self.other_components(net, S)
            if not dst:
                return None
        if want_via:
            from scipy.ndimage import binary_dilation
            near = np.zeros((self.ny, self.nx), bool)
            for n in range(2):
                near |= S[n]
            k = int(math.ceil((via_r + 0.12) / self.res))
            yy, xx = np.ogrid[-k:k + 1, -k:k + 1]
            near = binary_dilation(near, structure=(xx * xx + yy * yy) <= k * k)
            for n in range(2):
                G[n] = via_ok & ~near & free[LAYERS[n]]
        else:
            for l, g in dst:
                m = tomask(g)
                mf = m & free[l]
                G[lidx[l]] |= mf if mf.any() else m
        if window is not None:
            wm = self._mask(window)
            for l in LAYERS:
                free[l] &= wm
        self.last_info = dict(start=int(S.sum()), start_free=int((S[0] & free[LAYERS[0]]).sum() + (S[1] & free[LAYERS[1]]).sum()),
                              goal=int(G.sum()))
        if not S.any() or not G.any():
            return None
        # heuristic: euclidean distance to goal (any layer)
        gl = G[0] | G[1]
        H = distance_transform_edt(~gl) * self.res
        FREE = np.stack([free[LAYERS[0]] | S[0] | G[0], free[LAYERS[1]] | S[1] | G[1]])
        for n in range(2):
            if not allowed[n]:
                FREE[n] = S[n] | G[n]
        nyx = self.ny * self.nx
        gcost = np.full(2 * nyx, np.inf, np.float32)
        parent = np.full(2 * nyx, -1, np.int64)
        pdir = np.full(2 * nyx, -1, np.int8)
        closed = np.zeros(2 * nyx, bool)
        heap = []
        for n in range(2):
            js, iis = np.nonzero(S[n] & FREE[n])
            for j, i in zip(js, iis):
                idx = n * nyx + j * self.nx + i
                gcost[idx] = 0
                heapq.heappush(heap, (H[j, i], 0.0, idx))
        res = self.res
        steps = [(di, dj, res * (1.4142 if di and dj else 1.0), d) for d, (di, dj) in enumerate(DIRS)]
        goal_idx = None
        exp = 0
        prefer_map = prefer
        while heap:
            f, gc, idx = heapq.heappop(heap)
            if closed[idx]:
                continue
            closed[idx] = True
            exp += 1
            if exp > max_exp:
                break
            n, rem = divmod(idx, nyx)
            j, i = divmod(rem, self.nx)
            if G[n, j, i]:
                goal_idx = idx
                break
            pd = pdir[idx]
            for di, dj, c, d in steps:
                ii, jj = i + di, j + dj
                if ii < 0 or jj < 0 or ii >= self.nx or jj >= self.ny or not FREE[n, jj, ii]:
                    continue
                nidx = n * nyx + jj * self.nx + ii
                if closed[nidx]:
                    continue
                cc = c
                if pd >= 0 and pd != d:
                    cc += turn_cost * (2 if (DIRS[pd][0] * di + DIRS[pd][1] * dj) <= 0 else 1)
                if prefer_map is not None:
                    cc *= prefer_map[n][jj, ii]
                ng = gc + cc
                if ng < gcost[nidx]:
                    gcost[nidx] = ng
                    parent[nidx] = idx
                    pdir[nidx] = d
                    heapq.heappush(heap, (ng + H[jj, ii], ng, nidx))
            # via
            if via_ok[j, i]:
                m = 1 - n
                if allowed[m] and FREE[m, j, i]:
                    nidx = m * nyx + j * self.nx + i
                    if not closed[nidx]:
                        ng = gc + via_cost
                        if ng < gcost[nidx]:
                            gcost[nidx] = ng
                            parent[nidx] = idx
                            pdir[nidx] = -1
                            heapq.heappush(heap, (ng + H[j, i], ng, nidx))
        self.last_info["expanded"] = exp
        if goal_idx is None:
            return None
        # backtrack
        cells = []
        idx = goal_idx
        while idx != -1:
            n, rem = divmod(idx, nyx)
            j, i = divmod(rem, self.nx)
            cells.append((n, j, i))
            idx = parent[idx]
        cells.reverse()
        out = self._commit(net, cells, w, via_d, via_drill)
        if want_via:
            n, j, i = cells[-1]
            v = self.xy(j, i)
            self.ilayer.append((v[0], v[1], net))
            self.vias.append(dict(net=net, at=v, d=via_d, drill=via_drill))
            self.add_copper(Point(v).buffer(via_d / 2, resolution=12), LAYERS, net)
            self.add_hole(Point(v).buffer(via_drill / 2, resolution=12), net)
            out[1].append(v)
        return out

    def _commit(self, net, cells, w, via_d, via_drill):
        segs, vias = [], []
        cur_layer, pts = cells[0][0], [self.xy(cells[0][1], cells[0][2])]
        last_dir = None
        for (n0, j0, i0), (n1, j1, i1) in zip(cells, cells[1:]):
            if n1 != n0:
                vias.append(self.xy(j0, i0))
                segs.append((LAYERS[cur_layer], pts))
                cur_layer, pts, last_dir = n1, [self.xy(j1, i1)], None
                continue
            d = (i1 - i0, j1 - j0)
            if d == last_dir:
                pts[-1] = self.xy(j1, i1)
            else:
                pts.append(self.xy(j1, i1))
            last_dir = d
        segs.append((LAYERS[cur_layer], pts))
        out = []
        for layer, p in segs:
            if len(p) >= 2:
                for a, b in zip(p, p[1:]):
                    self.tracks.append(dict(net=net, layer=layer, a=a, b=b, w=w))
                    self.add_copper(LineString([a, b]).buffer(w / 2, cap_style=1), [layer], net)
                out.append((layer, p))
        for v in vias:
            self.ilayer.append((v[0], v[1], net))
            self.vias.append(dict(net=net, at=v, d=via_d, drill=via_drill))
            self.add_copper(Point(v).buffer(via_d / 2, resolution=12), LAYERS, net)
            self.add_hole(Point(v).buffer(via_drill / 2, resolution=12), net)
        return out, vias

    # ---------------------------------------------------------------- direct (pre-planned) geometry
    def add_track(self, net, layer, pts, w):
        for a, b in zip(pts, pts[1:]):
            self.tracks.append(dict(net=net, layer=layer, a=tuple(a), b=tuple(b), w=w))
            self.add_copper(LineString([a, b]).buffer(w / 2, cap_style=1), [layer], net)

    def add_via(self, net, at, d=0.6, drill=0.3):
        self.vias.append(dict(net=net, at=tuple(at), d=d, drill=drill))
        self.ilayer.append((at[0], at[1], net))
        self.add_copper(Point(at).buffer(d / 2, resolution=12), LAYERS, net)
        self.add_hole(Point(at).buffer(drill / 2, resolution=12), net)

    def _labels(self, net):
        from scipy.ndimage import label
        k = self.netid.get(net)
        lab, cnt = [], []
        for n, l in enumerate(LAYERS):
            a, c = label(self.owner[l] == k, structure=np.ones((3, 3)))
            lab.append(a)
            cnt.append(c)
        parent = {}

        def f(x):
            while parent.setdefault(x, x) != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for x, y, nn in self.ilayer:
            if nn != net:
                continue
            j, i = self.cell(x, y)
            if 0 <= j < self.ny and 0 <= i < self.nx and lab[0][j, i] and lab[1][j, i]:
                parent[f((0, lab[0][j, i]))] = f((1, lab[1][j, i]))
        return lab, cnt, f

    def component(self, net, S):
        """Copper of `net` connected to the start cells (2 x ny x nx bool)."""
        out = np.zeros_like(S)
        if self.netid.get(net) is None:
            return out
        lab, cnt, f = self._labels(net)
        roots = set()
        for n in range(2):
            for v in np.unique(lab[n][S[n]]):
                if v:
                    roots.add(f((n, int(v))))
        for n in range(2):
            ids = [v for v in range(1, cnt[n] + 1) if f((n, v)) in roots]
            if ids:
                out[n] = np.isin(lab[n], ids)
        return out

    def other_components(self, net, S):
        """Copper of `net` that is NOT connected to the start cells S (2 x ny x nx)."""
        from scipy.ndimage import label
        k = self.netid.get(net)
        if k is None:
            return []
        lab, cnt = [], []
        for n, l in enumerate(LAYERS):
            a, c = label(self.owner[l] == k, structure=np.ones((3, 3)))
            lab.append(a)
            cnt.append(c)
        parent = {}

        def f(x):
            while parent.setdefault(x, x) != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for x, y, nn in self.ilayer:
            if nn != net:
                continue
            j, i = self.cell(x, y)
            if 0 <= j < self.ny and 0 <= i < self.nx and lab[0][j, i] and lab[1][j, i]:
                parent[f((0, lab[0][j, i]))] = f((1, lab[1][j, i]))
        src = set()
        for n in range(2):
            for v in np.unique(lab[n][S[n]]):
                if v:
                    src.add(f((n, int(v))))
        out = []
        for n, l in enumerate(LAYERS):
            ids = [v for v in range(1, cnt[n] + 1) if f((n, v)) not in src]
            if ids:
                out.append((l, np.isin(lab[n], ids)))
        return out

    def net_regions(self, net):
        """Copper regions of a net already on the board (for multi-terminal goals)."""
        k = self.netid.get(net)
        if k is None:
            return []
        out = []
        for l in LAYERS:
            m = self.owner[l] == k
            if m.any():
                out.append((l, m))
        return out
