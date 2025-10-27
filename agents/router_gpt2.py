# agents/router_gpt2.py
# Minimal deterministic router with RDP simplification.
from math import hypot

def _rdp(points, epsilon=2.0):
    if len(points) < 3:
        return points
    def perp_dist(p, a, b):
        if a == b:
            return hypot(p[0]-a[0], p[1]-a[1])
        x, y = p; x1,y1 = a; x2,y2 = b
        num = abs((y2-y1)*x - (x2-x1)*y + x2*y1 - y2*x1)
        den = ((y2-y1)**2 + (x2-x1)**2)**0.5
        return num/den
    dmax, idx = 0, 0
    for i in range(1, len(points)-1):
        d = perp_dist(points[i], points[0], points[-1])
        if d > dmax:
            idx, dmax = i, d
    if dmax > epsilon:
        res1 = _rdp(points[:idx+1], epsilon)
        res2 = _rdp(points[idx:], epsilon)
        return res1[:-1] + res2
    else:
        return [points[0], points[-1]]

def naive_path(a, b):
    # Straight line for now; placeholder for A*.
    return [a, b]

def route_circuit(source_port, target_ports, wire="14/2"):
    circuits = []
    cur_src = source_port
    for i, tgt in enumerate(target_ports, start=1):
        raw = naive_path((cur_src["x"],cur_src["y"]), (tgt["x"],tgt["y"]))
        simp = _rdp(raw, epsilon=1.0)
        path = [{"x":x, "y":y} for x,y in simp]
        circuits.append({"id": f"ckt_{i}", "wire": wire, "path": path})
        cur_src = tgt
    return circuits

def to_svg(markup, width=1200, height=800):
    # Very simple SVG writer for preview/export
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">']
    lines.append('<rect x="0" y="0" width="100%" height="100%" fill="white"/>')
    # draw circuits
    for c in markup.get("circuits", []):
        pts = " ".join([f'{p["x"]},{p["y"]}' for p in c["path"]])
        lines.append(f'<polyline points="{pts}" stroke="#ff6600" fill="none" stroke-width="2"/>')
    # draw symbols
    for s in markup.get("symbols", []):
        x = s["bbox"]["x"]; y = s["bbox"]["y"]
        w = max(4, s["bbox"].get("w", 12)); h = max(4, s["bbox"].get("h", 12))
        lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#556B2F" opacity="0.7"/>')
        lines.append(f'<text x="{x+w+4}" y="{y+12}" font-size="10" fill="#111">{s.get("label","")}</text>')
    lines.append("</svg>")
    return "\n".join(lines)
