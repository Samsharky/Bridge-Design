import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent

try:
    import openseespy.opensees as ops  # type: ignore
    OPENSEES_STATUS = "system"
except Exception:
    try:
        import sys

        local_deps = ROOT / ".deps"
        if str(local_deps) not in sys.path:
            sys.path.insert(0, str(local_deps))
        import openseespy.opensees as ops  # type: ignore

        OPENSEES_STATUS = "local"
    except Exception:
        ops = None
        OPENSEES_STATUS = "unavailable"


def section_properties():
    return {
        "width": 20.5,
        "depth": 3.2,
        "top_plate": 0.026,
        "bottom_plate": 0.030,
        "web_plate": 0.022,
        "A": 1.02,
        "Iy": 5.10,
        "Iz": 42.5,
        "J": 1.95,
        "lane_count": 4,
        "lane_width": 3.5,
        "inside_shoulder": 1.0,
        "outside_shoulder": 2.25,
    }


def bridge_definition():
    side_span = 70.0
    main_span = 180.0
    total_length = side_span + main_span
    pylon_x = side_span

    deck_stations = [float(x) for x in range(0, int(total_length) + 1, 10)]
    deck_nodes = {}
    nodes = {}
    for tag, x in enumerate(deck_stations, start=1):
        deck_nodes[x] = tag
        nodes[tag] = np.array([x, 0.0, 0.0], dtype=float)

    half_width = section_properties()["width"] / 2.0
    cable_plane_y = half_width - 0.90

    lean_offsets = {
        "base": 0.0,
        "deck": 0.0,
        "mid": -5.5,
        "upper": -10.5,
        "apex": -15.0,
    }

    pylon_nodes = {
        "base_left": 1001,
        "base_right": 1002,
        "deck_left": 1003,
        "deck_right": 1004,
        "mid_left": 1005,
        "mid_right": 1006,
        "upper_left": 1007,
        "upper_right": 1008,
        "apex": 1009,
    }
    nodes[pylon_nodes["base_left"]] = np.array([pylon_x + lean_offsets["base"], -cable_plane_y, -24.0], dtype=float)
    nodes[pylon_nodes["base_right"]] = np.array([pylon_x + lean_offsets["base"], cable_plane_y, -24.0], dtype=float)
    nodes[pylon_nodes["deck_left"]] = np.array([pylon_x + lean_offsets["deck"], -cable_plane_y, 0.0], dtype=float)
    nodes[pylon_nodes["deck_right"]] = np.array([pylon_x + lean_offsets["deck"], cable_plane_y, 0.0], dtype=float)
    nodes[pylon_nodes["mid_left"]] = np.array([pylon_x + lean_offsets["mid"], -5.5, 24.0], dtype=float)
    nodes[pylon_nodes["mid_right"]] = np.array([pylon_x + lean_offsets["mid"], 5.5, 24.0], dtype=float)
    nodes[pylon_nodes["upper_left"]] = np.array([pylon_x + lean_offsets["upper"], -2.6, 46.0], dtype=float)
    nodes[pylon_nodes["upper_right"]] = np.array([pylon_x + lean_offsets["upper"], 2.6, 46.0], dtype=float)
    nodes[pylon_nodes["apex"]] = np.array([pylon_x + lean_offsets["apex"], 0.0, 72.0], dtype=float)

    elements = []
    tag = 1
    for x1, x2 in zip(deck_stations[:-1], deck_stations[1:]):
        elements.append((tag, deck_nodes[x1], deck_nodes[x2], "deck"))
        tag += 1

    for n1, n2, role in [
        (pylon_nodes["base_left"], pylon_nodes["deck_left"], "pylon_left"),
        (pylon_nodes["deck_left"], pylon_nodes["mid_left"], "pylon_left"),
        (pylon_nodes["mid_left"], pylon_nodes["upper_left"], "pylon_left"),
        (pylon_nodes["upper_left"], pylon_nodes["apex"], "pylon_left"),
        (pylon_nodes["base_right"], pylon_nodes["deck_right"], "pylon_right"),
        (pylon_nodes["deck_right"], pylon_nodes["mid_right"], "pylon_right"),
        (pylon_nodes["mid_right"], pylon_nodes["upper_right"], "pylon_right"),
        (pylon_nodes["upper_right"], pylon_nodes["apex"], "pylon_right"),
        (pylon_nodes["deck_left"], pylon_nodes["deck_right"], "pylon_cross"),
        (pylon_nodes["mid_left"], pylon_nodes["mid_right"], "pylon_cross"),
    ]:
        elements.append((tag, n1, n2, role))
        tag += 1

    stay_rows = [
        (50.0, pylon_nodes["mid_left"], pylon_nodes["mid_right"]),
        (30.0, pylon_nodes["upper_left"], pylon_nodes["upper_right"]),
        (10.0, pylon_nodes["apex"], pylon_nodes["apex"]),
        (90.0, pylon_nodes["mid_left"], pylon_nodes["mid_right"]),
        (110.0, pylon_nodes["upper_left"], pylon_nodes["upper_right"]),
        (130.0, pylon_nodes["apex"], pylon_nodes["apex"]),
        (150.0, pylon_nodes["apex"], pylon_nodes["apex"]),
        (170.0, pylon_nodes["apex"], pylon_nodes["apex"]),
        (190.0, pylon_nodes["apex"], pylon_nodes["apex"]),
        (210.0, pylon_nodes["apex"], pylon_nodes["apex"]),
        (230.0, pylon_nodes["apex"], pylon_nodes["apex"]),
    ]
    stay_anchors = []
    for x, left_tower_node, right_tower_node in stay_rows:
        stay_anchors.append({"x": x, "y": -cable_plane_y, "tower_node": left_tower_node, "side": "left"})
        stay_anchors.append({"x": x, "y": cable_plane_y, "tower_node": right_tower_node, "side": "right"})
        elements.append((tag, left_tower_node, deck_nodes[x], "stay_left"))
        tag += 1
        elements.append((tag, right_tower_node, deck_nodes[x], "stay_right"))
        tag += 1

    return {
        "nodes": nodes,
        "deck_nodes": deck_nodes,
        "elements": elements,
        "stay_anchors": stay_anchors,
        "side_span": side_span,
        "main_span": main_span,
        "total_length": total_length,
        "pylon_x": pylon_x,
        "pylon_nodes": pylon_nodes,
        "section": section_properties(),
        "cable_plane_y": cable_plane_y,
        "tower_lean_tip_offset": lean_offsets["apex"],
    }


def run_opensees_model(data):
    if ops is None:
        raise RuntimeError("OpenSeesPy unavailable in this environment")

    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)

    for tag, xyz in data["nodes"].items():
        ops.node(tag, *xyz.tolist())

    pylon_base_left = data["pylon_nodes"]["base_left"]
    pylon_base_right = data["pylon_nodes"]["base_right"]
    deck_nodes = data["deck_nodes"]
    ops.fix(pylon_base_left, 1, 1, 1, 1, 1, 1)
    ops.fix(pylon_base_right, 1, 1, 1, 1, 1, 1)
    ops.fix(deck_nodes[0.0], 1, 1, 1, 0, 0, 0)
    ops.fix(deck_nodes[data["total_length"]], 0, 1, 1, 0, 0, 0)

    steel_e = 200e9
    steel_g = 79.3e9
    cable_e = 195e9
    sec = data["section"]

    ops.geomTransf("Linear", 1, 0.0, 0.0, 1.0)
    ops.geomTransf("Linear", 2, 0.0, 1.0, 0.0)
    ops.uniaxialMaterial("Elastic", 1, cable_e)

    for tag, ni, nj, role in data["elements"]:
        if role == "deck":
            ops.element(
                "elasticBeamColumn",
                tag,
                ni,
                nj,
                sec["A"],
                steel_e,
                steel_g,
                sec["J"],
                sec["Iy"],
                sec["Iz"],
                1,
            )
        elif role.startswith("pylon"):
            ops.element(
                "elasticBeamColumn",
                tag,
                ni,
                nj,
                1.80,
                steel_e,
                steel_g,
                3.50,
                22.0,
                18.0,
                2,
            )
        else:
            area = 0.0045 if data["nodes"][nj][0] < data["pylon_x"] else 0.0065
            ops.element("truss", tag, ni, nj, area, 1)

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)

    deck_stations = sorted(deck_nodes.keys())
    tributary = {}
    for i, x in enumerate(deck_stations):
        left = (x - deck_stations[i - 1]) / 2.0 if i > 0 else (deck_stations[i + 1] - x) / 2.0
        right = (deck_stations[i + 1] - x) / 2.0 if i < len(deck_stations) - 1 else (x - deck_stations[i - 1]) / 2.0
        tributary[x] = left + right

    dead_load_per_m = 260e3
    for x, node in deck_nodes.items():
        load = dead_load_per_m * tributary[x]
        if x in (0.0, data["total_length"]):
            load *= 0.85
        ops.load(node, 0.0, 0.0, -load, 0.0, 0.0, 0.0)

    ops.system("BandGeneral")
    ops.numberer("RCM")
    ops.constraints("Transformation")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")

    ok = ops.analyze(1)
    if ok != 0:
        raise RuntimeError(f"OpenSees analysis failed with code {ok}")

    disps = {}
    for tag in data["nodes"]:
        node_disp = ops.nodeDisp(tag)
        disps[tag] = np.array(node_disp[:3], dtype=float) if len(node_disp) >= 3 else np.zeros(3)
    return disps, "OpenSees"


def approximate_displacements(data):
    disps = {}
    pylon_x = data["pylon_x"]
    total = data["total_length"]

    for tag, xyz in data["nodes"].items():
        x, _, z = xyz
        ux = 0.0
        uz = 0.0
        if z == 0.0 and 0.0 <= x <= total:
            if x <= pylon_x:
                xi = x / pylon_x
                uz = -0.035 * np.sin(np.pi * xi) ** 1.2
            else:
                xi = (x - pylon_x) / (total - pylon_x)
                uz = -0.085 * np.sin(np.pi * xi) ** 1.15
                ux = 0.008 * np.sin(np.pi * xi)
            if any(abs(anchor["x"] - x) < 1e-9 for anchor in data["stay_anchors"]):
                uz *= 0.72
        elif z > 0.0 and abs(x - (pylon_x - 5.5 * z / 24.0)) < 16.0:
            eta = z / 72.0
            ux = -0.020 * eta
            uz = -0.010 * eta
        disps[tag] = np.array([ux, 0.0, uz], dtype=float)

    return disps, "Approximate fallback"


def add_trace(traces, trace):
    traces.append(trace)


def outer_lane_rise(x, y, data):
    section = data["section"]
    lane_half_width = section["lane_count"] * section["lane_width"] / 2.0
    inner_lane_limit = section["lane_width"]
    if abs(y) <= inner_lane_limit:
        return 0.0
    if abs(y) > lane_half_width:
        return 0.0
    if x <= data["pylon_x"]:
        return 0.0
    xi = (x - data["pylon_x"]) / (data["total_length"] - data["pylon_x"])
    xi = max(0.0, min(1.0, xi))
    smooth_xi = xi * xi * (3.0 - 2.0 * xi)
    return 10.0 * smooth_xi


def deck_left_curve(x, data):
    if x <= data["pylon_x"]:
        return 0.0
    xi = (x - data["pylon_x"]) / (data["total_length"] - data["pylon_x"])
    xi = max(0.0, min(1.0, xi))
    smooth_xi = xi * xi * (3.0 - 2.0 * xi)
    return -18.0 * smooth_xi


def ramp_split_offset(x, data):
    if x <= data["pylon_x"]:
        return 0.0
    xi = (x - data["pylon_x"]) / (data["total_length"] - data["pylon_x"])
    xi = max(0.0, min(1.0, xi))
    smooth_xi = xi * xi * (3.0 - 2.0 * xi)
    return 4.8 * smooth_xi


def append_point(seq, point, allow_duplicate=False):
    if not seq or allow_duplicate or any(abs(seq[-1][i] - point[i]) > 1e-9 for i in range(3)):
        seq.append(point)


def make_html(data, disps, analysis_mode, output_html):
    max_disp = max(np.linalg.norm(v) for v in disps.values())
    scale = 120.0 if max_disp == 0.0 else min(220.0, 4.0 / max_disp)

    traces = []
    width = data["section"]["width"]
    depth = data["section"]["depth"]
    half_width = width / 2.0
    lane_width = data["section"]["lane_width"]
    lane_offsets = [-1.5 * lane_width, -0.5 * lane_width, 0.5 * lane_width, 1.5 * lane_width]
    lane_names = ["Outer Lane L", "Inner Lane L", "Inner Lane R", "Outer Lane R"]

    deck_stations = sorted(data["deck_nodes"].keys())
    full_left_top = []
    full_right_top = []
    full_left_bottom = []
    full_right_bottom = []
    d_full_left_top = []
    d_full_right_top = []
    d_full_left_bottom = []
    d_full_right_bottom = []
    main_left_top = []
    main_right_top = []
    main_left_bottom = []
    main_right_bottom = []
    d_main_left_top = []
    d_main_right_top = []
    d_main_left_bottom = []
    d_main_right_bottom = []
    ramp_left_outer_top = []
    ramp_left_inner_top = []
    ramp_left_outer_bottom = []
    ramp_left_inner_bottom = []
    d_ramp_left_outer_top = []
    d_ramp_left_inner_top = []
    d_ramp_left_outer_bottom = []
    d_ramp_left_inner_bottom = []
    ramp_right_outer_top = []
    ramp_right_inner_top = []
    ramp_right_outer_bottom = []
    ramp_right_inner_bottom = []
    d_ramp_right_outer_top = []
    d_ramp_right_inner_top = []
    d_ramp_right_outer_bottom = []
    d_ramp_right_inner_bottom = []
    lane_lines = {name: [] for name in lane_names}
    d_lane_lines = {name: [] for name in lane_names}
    divider_left = []
    divider_right = []
    d_divider_left = []
    d_divider_right = []

    for x in deck_stations:
        tag = data["deck_nodes"][x]
        c = data["nodes"][tag]
        d = disps[tag] * scale
        center_shift = deck_left_curve(c[0], data)
        split = ramp_split_offset(c[0], data)
        left_rise = outer_lane_rise(c[0], -half_width, data)
        right_rise = outer_lane_rise(c[0], half_width, data)
        if c[0] <= data["pylon_x"]:
            full_left_top.append([c[0], center_shift - half_width, c[2]])
            full_right_top.append([c[0], center_shift + half_width, c[2]])
            full_left_bottom.append([c[0], center_shift - half_width * 0.55, c[2] - depth])
            full_right_bottom.append([c[0], center_shift + half_width * 0.55, c[2] - depth])

            d_full_left_top.append([c[0] + d[0], center_shift - half_width, c[2] + d[2]])
            d_full_right_top.append([c[0] + d[0], center_shift + half_width, c[2] + d[2]])
            d_full_left_bottom.append([c[0] + d[0], center_shift - half_width * 0.55, c[2] - depth + d[2]])
            d_full_right_bottom.append([c[0] + d[0], center_shift + half_width * 0.55, c[2] - depth + d[2]])
        else:
            main_left_top.append([c[0], center_shift - lane_width, c[2]])
            main_right_top.append([c[0], center_shift + lane_width, c[2]])
            main_left_bottom.append([c[0], center_shift - lane_width * 0.55, c[2] - depth])
            main_right_bottom.append([c[0], center_shift + lane_width * 0.55, c[2] - depth])

            d_main_left_top.append([c[0] + d[0], center_shift - lane_width, c[2] + d[2]])
            d_main_right_top.append([c[0] + d[0], center_shift + lane_width, c[2] + d[2]])
            d_main_left_bottom.append([c[0] + d[0], center_shift - lane_width * 0.55, c[2] - depth + d[2]])
            d_main_right_bottom.append([c[0] + d[0], center_shift + lane_width * 0.55, c[2] - depth + d[2]])

            ramp_left_outer_y = center_shift - half_width - split
            ramp_left_inner_y = center_shift - lane_width - split * 0.35
            ramp_right_outer_y = center_shift + half_width - split
            ramp_right_inner_y = center_shift + lane_width - split * 0.35
            ramp_bottom_outer_factor = 0.62
            ramp_bottom_inner_factor = 0.80

            ramp_left_outer_top.append([c[0], ramp_left_outer_y, c[2] + left_rise])
            ramp_left_inner_top.append([c[0], ramp_left_inner_y, c[2] + outer_lane_rise(c[0], -1.5 * lane_width, data)])
            ramp_left_outer_bottom.append([c[0], center_shift - half_width * ramp_bottom_outer_factor - split, c[2] - depth + left_rise])
            ramp_left_inner_bottom.append([c[0], center_shift - lane_width * ramp_bottom_inner_factor - split * 0.35, c[2] - depth + outer_lane_rise(c[0], -1.5 * lane_width, data)])

            d_ramp_left_outer_top.append([c[0] + d[0], ramp_left_outer_y, c[2] + left_rise + d[2]])
            d_ramp_left_inner_top.append([c[0] + d[0], ramp_left_inner_y, c[2] + outer_lane_rise(c[0], -1.5 * lane_width, data) + d[2]])
            d_ramp_left_outer_bottom.append([c[0] + d[0], center_shift - half_width * ramp_bottom_outer_factor - split, c[2] - depth + left_rise + d[2]])
            d_ramp_left_inner_bottom.append([c[0] + d[0], center_shift - lane_width * ramp_bottom_inner_factor - split * 0.35, c[2] - depth + outer_lane_rise(c[0], -1.5 * lane_width, data) + d[2]])

            ramp_right_outer_top.append([c[0], ramp_right_outer_y, c[2] + right_rise])
            ramp_right_inner_top.append([c[0], ramp_right_inner_y, c[2] + outer_lane_rise(c[0], 1.5 * lane_width, data)])
            ramp_right_outer_bottom.append([c[0], center_shift + half_width * ramp_bottom_outer_factor - split, c[2] - depth + right_rise])
            ramp_right_inner_bottom.append([c[0], center_shift + lane_width * ramp_bottom_inner_factor - split * 0.35, c[2] - depth + outer_lane_rise(c[0], 1.5 * lane_width, data)])

            d_ramp_right_outer_top.append([c[0] + d[0], ramp_right_outer_y, c[2] + right_rise + d[2]])
            d_ramp_right_inner_top.append([c[0] + d[0], ramp_right_inner_y, c[2] + outer_lane_rise(c[0], 1.5 * lane_width, data) + d[2]])
            d_ramp_right_outer_bottom.append([c[0] + d[0], center_shift + half_width * ramp_bottom_outer_factor - split, c[2] - depth + right_rise + d[2]])
            d_ramp_right_inner_bottom.append([c[0] + d[0], center_shift + lane_width * ramp_bottom_inner_factor - split * 0.35, c[2] - depth + outer_lane_rise(c[0], 1.5 * lane_width, data) + d[2]])

        for lane_name, lane_y in zip(lane_names, lane_offsets):
            lane_rise = outer_lane_rise(c[0], lane_y, data)
            lane_lines[lane_name].append([c[0], center_shift + lane_y, c[2] + lane_rise + 0.03])
            d_lane_lines[lane_name].append([c[0] + d[0], center_shift + lane_y, c[2] + lane_rise + d[2] + 0.03])

        divider_top = 0.65
        divider_left_y = center_shift - lane_width - split * 0.18
        divider_right_y = center_shift + lane_width - split * 0.18
        divider_left_rise = outer_lane_rise(c[0], -1.5 * lane_width, data)
        divider_right_rise = outer_lane_rise(c[0], 1.5 * lane_width, data)
        divider_left.append([c[0], divider_left_y, c[2] + divider_left_rise + divider_top])
        divider_right.append([c[0], divider_right_y, c[2] + divider_right_rise + divider_top])
        d_divider_left.append([c[0] + d[0], divider_left_y, c[2] + divider_left_rise + divider_top + d[2]])
        d_divider_right.append([c[0] + d[0], divider_right_y, c[2] + divider_right_rise + divider_top + d[2]])

    # Smooth the connection at the pylon by starting the split geometry from the pylon station.
    pylon_x = data["pylon_x"]
    pylon_tag = data["deck_nodes"][pylon_x]
    pylon_coord = data["nodes"][pylon_tag]
    pylon_disp = disps[pylon_tag] * scale
    center_shift = deck_left_curve(pylon_x, data)
    split = ramp_split_offset(pylon_x, data)

    transition_main_left_top = [pylon_x, center_shift - lane_width, pylon_coord[2]]
    transition_main_right_top = [pylon_x, center_shift + lane_width, pylon_coord[2]]
    transition_main_left_bottom = [pylon_x, center_shift - lane_width * 0.55, pylon_coord[2] - depth]
    transition_main_right_bottom = [pylon_x, center_shift + lane_width * 0.55, pylon_coord[2] - depth]

    main_left_top.insert(0, transition_main_left_top)
    main_right_top.insert(0, transition_main_right_top)
    main_left_bottom.insert(0, transition_main_left_bottom)
    main_right_bottom.insert(0, transition_main_right_bottom)
    d_main_left_top.insert(0, [pylon_x + pylon_disp[0], center_shift - lane_width, pylon_coord[2] + pylon_disp[2]])
    d_main_right_top.insert(0, [pylon_x + pylon_disp[0], center_shift + lane_width, pylon_coord[2] + pylon_disp[2]])
    d_main_left_bottom.insert(0, [pylon_x + pylon_disp[0], center_shift - lane_width * 0.55, pylon_coord[2] - depth + pylon_disp[2]])
    d_main_right_bottom.insert(0, [pylon_x + pylon_disp[0], center_shift + lane_width * 0.55, pylon_coord[2] - depth + pylon_disp[2]])

    for side in ("left", "right"):
        side_sign = -1.0 if side == "left" else 1.0
        outer_top = ramp_left_outer_top if side == "left" else ramp_right_outer_top
        inner_top = ramp_left_inner_top if side == "left" else ramp_right_inner_top
        outer_bottom = ramp_left_outer_bottom if side == "left" else ramp_right_outer_bottom
        inner_bottom = ramp_left_inner_bottom if side == "left" else ramp_right_inner_bottom
        d_outer_top = d_ramp_left_outer_top if side == "left" else d_ramp_right_outer_top
        d_inner_top = d_ramp_left_inner_top if side == "left" else d_ramp_right_inner_top
        d_outer_bottom = d_ramp_left_outer_bottom if side == "left" else d_ramp_right_outer_bottom
        d_inner_bottom = d_ramp_left_inner_bottom if side == "left" else d_ramp_right_inner_bottom

        outer_y = center_shift + side_sign * half_width - split
        inner_y = center_shift + side_sign * lane_width - split * 0.35
        outer_bottom_y = center_shift + side_sign * half_width * 0.62 - split
        inner_bottom_y = center_shift + side_sign * lane_width * 0.80 - split * 0.35

        outer_top.insert(0, [pylon_x, outer_y, pylon_coord[2]])
        inner_top.insert(0, [pylon_x, inner_y, pylon_coord[2]])
        outer_bottom.insert(0, [pylon_x, outer_bottom_y, pylon_coord[2] - depth])
        inner_bottom.insert(0, [pylon_x, inner_bottom_y, pylon_coord[2] - depth])
        d_outer_top.insert(0, [pylon_x + pylon_disp[0], outer_y, pylon_coord[2] + pylon_disp[2]])
        d_inner_top.insert(0, [pylon_x + pylon_disp[0], inner_y, pylon_coord[2] + pylon_disp[2]])
        d_outer_bottom.insert(0, [pylon_x + pylon_disp[0], outer_bottom_y, pylon_coord[2] - depth + pylon_disp[2]])
        d_inner_bottom.insert(0, [pylon_x + pylon_disp[0], inner_bottom_y, pylon_coord[2] - depth + pylon_disp[2]])

    # Extend upper ramps beyond the bridge end as 90-degree left-turning merge ramps.
    end_x = data["total_length"]
    arc_angles = [np.pi / 8.0, np.pi / 4.0, 3.0 * np.pi / 8.0, np.pi / 2.0]
    turn_radius = 34.0
    for side in ("left", "right"):
        side_sign = -1.0 if side == "left" else 1.0
        outer_top = ramp_left_outer_top if side == "left" else ramp_right_outer_top
        inner_top = ramp_left_inner_top if side == "left" else ramp_right_inner_top
        outer_bottom = ramp_left_outer_bottom if side == "left" else ramp_right_outer_bottom
        inner_bottom = ramp_left_inner_bottom if side == "left" else ramp_right_inner_bottom
        d_outer_top = d_ramp_left_outer_top if side == "left" else d_ramp_right_outer_top
        d_inner_top = d_ramp_left_inner_top if side == "left" else d_ramp_right_inner_top
        d_outer_bottom = d_ramp_left_outer_bottom if side == "left" else d_ramp_right_outer_bottom
        d_inner_bottom = d_ramp_left_inner_bottom if side == "left" else d_ramp_right_inner_bottom
        lane_key = "Outer Lane L" if side == "left" else "Outer Lane R"
        d_lane_key = lane_key

        base_center = deck_left_curve(end_x, data)
        base_split = ramp_split_offset(end_x, data)
        for i, theta in enumerate(arc_angles, start=1):
            x = end_x + turn_radius * np.sin(theta)
            y_center = base_center + turn_radius * (1.0 - np.cos(theta))
            split = base_split + 0.6 * i
            extra_rise = 10.0 + 1.0 * i
            outer_y = y_center + side_sign * half_width - split
            inner_y = y_center + side_sign * lane_width - split * 0.35
            outer_bottom_y = y_center + side_sign * half_width * 0.62 - split
            inner_bottom_y = y_center + side_sign * lane_width * 0.80 - split * 0.35

            append_point(outer_top, [x, outer_y, extra_rise])
            append_point(inner_top, [x, inner_y, extra_rise])
            append_point(outer_bottom, [x, outer_bottom_y, extra_rise - depth])
            append_point(inner_bottom, [x, inner_bottom_y, extra_rise - depth])
            append_point(d_outer_top, [x, outer_y, extra_rise])
            append_point(d_inner_top, [x, inner_y, extra_rise])
            append_point(d_outer_bottom, [x, outer_bottom_y, extra_rise - depth])
            append_point(d_inner_bottom, [x, inner_bottom_y, extra_rise - depth])
            append_point(lane_lines[lane_key], [x, y_center + side_sign * 1.5 * lane_width - split * 0.55, extra_rise + 0.03])
            append_point(d_lane_lines[d_lane_key], [x, y_center + side_sign * 1.5 * lane_width - split * 0.55, extra_rise + 0.03])

    def line_trace(points, color, width_px, name=None, dash=None, showlegend=False):
        return {
            "type": "scatter3d",
            "mode": "lines",
            "x": [p[0] for p in points],
            "y": [p[1] for p in points],
            "z": [p[2] for p in points],
            "line": {"color": color, "width": width_px, "dash": dash},
            "name": name,
            "showlegend": showlegend,
            "hoverinfo": "skip",
        }

    if full_left_top:
        add_trace(traces, line_trace(full_left_top, "#1f4e79", 8, "Approach deck", showlegend=True))
        add_trace(traces, line_trace(full_right_top, "#1f4e79", 8))
        add_trace(traces, line_trace(full_left_bottom, "#3b82a0", 6))
        add_trace(traces, line_trace(full_right_bottom, "#3b82a0", 6))
        add_trace(traces, line_trace(d_full_left_top, "#dc2626", 5, f"Deformed x{scale:.0f}", "dash", True))
        add_trace(traces, line_trace(d_full_right_top, "#dc2626", 5, dash="dash"))
        add_trace(traces, line_trace(d_full_left_bottom, "#f87171", 4, dash="dash"))
        add_trace(traces, line_trace(d_full_right_bottom, "#f87171", 4, dash="dash"))

    if main_left_top:
        add_trace(traces, line_trace(main_left_top, "#0f766e", 8, "Main bridge deck", showlegend=True))
        add_trace(traces, line_trace(main_right_top, "#0f766e", 8))
        add_trace(traces, line_trace(main_left_bottom, "#14b8a6", 6))
        add_trace(traces, line_trace(main_right_bottom, "#14b8a6", 6))
        add_trace(traces, line_trace(d_main_left_top, "#ef4444", 4, dash="dash"))
        add_trace(traces, line_trace(d_main_right_top, "#ef4444", 4, dash="dash"))

    if ramp_left_outer_top:
        add_trace(traces, line_trace(ramp_left_outer_top, "#b45309", 7, "Split ramps", showlegend=True))
        add_trace(traces, line_trace(ramp_left_inner_top, "#b45309", 7))
        add_trace(traces, line_trace(ramp_left_outer_bottom, "#f59e0b", 5))
        add_trace(traces, line_trace(ramp_left_inner_bottom, "#f59e0b", 5))
        add_trace(traces, line_trace(d_ramp_left_outer_top, "#fb7185", 3, dash="dash"))
        add_trace(traces, line_trace(d_ramp_left_inner_top, "#fb7185", 3, dash="dash"))

    if ramp_right_outer_top:
        add_trace(traces, line_trace(ramp_right_outer_top, "#92400e", 7))
        add_trace(traces, line_trace(ramp_right_inner_top, "#92400e", 7))
        add_trace(traces, line_trace(ramp_right_outer_bottom, "#f59e0b", 5))
        add_trace(traces, line_trace(ramp_right_inner_bottom, "#f59e0b", 5))
        add_trace(traces, line_trace(d_ramp_right_outer_top, "#fb7185", 3, dash="dash"))
        add_trace(traces, line_trace(d_ramp_right_inner_top, "#fb7185", 3, dash="dash"))

    lane_colors = {
        "Outer Lane L": "#f59e0b",
        "Inner Lane L": "#111827",
        "Inner Lane R": "#111827",
        "Outer Lane R": "#f59e0b",
    }
    lane_legend = set()
    for lane_name in lane_names:
        add_trace(
            traces,
            line_trace(
                lane_lines[lane_name],
                lane_colors[lane_name],
                4,
                lane_name if lane_name not in lane_legend else None,
                showlegend=lane_name not in lane_legend,
            ),
        )
        lane_legend.add(lane_name)
        add_trace(traces, line_trace(d_lane_lines[lane_name], "#ef4444", 2, dash="dot"))

    add_trace(traces, line_trace(divider_left, "#475569", 7, "Lane separators", showlegend=True))
    add_trace(traces, line_trace(divider_right, "#475569", 7))
    add_trace(traces, line_trace(d_divider_left, "#94a3b8", 3, dash="dot"))
    add_trace(traces, line_trace(d_divider_right, "#94a3b8", 3, dash="dot"))

    approach_count = len(full_left_top)
    for i in range(approach_count):
        for a, b in [
            (full_left_top[i], full_right_top[i]),
            (full_left_bottom[i], full_right_bottom[i]),
            (full_left_top[i], full_left_bottom[i]),
            (full_right_top[i], full_right_bottom[i]),
        ]:
            add_trace(traces, line_trace([a, b], "#64748b", 3))

    post_count = len(main_left_top)
    for i in range(post_count):
        for a, b in [
            (main_left_top[i], main_right_top[i]),
            (main_left_bottom[i], main_right_bottom[i]),
            (main_left_top[i], main_left_bottom[i]),
            (main_right_top[i], main_right_bottom[i]),
            (ramp_left_outer_top[i], ramp_left_inner_top[i]),
            (ramp_left_outer_bottom[i], ramp_left_inner_bottom[i]),
            (ramp_left_outer_top[i], ramp_left_outer_bottom[i]),
            (ramp_left_inner_top[i], ramp_left_inner_bottom[i]),
            (ramp_right_outer_top[i], ramp_right_inner_top[i]),
            (ramp_right_outer_bottom[i], ramp_right_inner_bottom[i]),
            (ramp_right_outer_top[i], ramp_right_outer_bottom[i]),
            (ramp_right_inner_top[i], ramp_right_inner_bottom[i]),
        ]:
            add_trace(traces, line_trace([a, b], "#64748b", 3))

    pylon_legend = False
    stay_legend = False
    for _, ni, nj, role in data["elements"]:
        p1 = data["nodes"][ni]
        p2 = data["nodes"][nj]
        if role.startswith("pylon"):
            add_trace(
                traces,
                line_trace(
                    [p1.tolist(), p2.tolist()],
                    "#4b5563",
                    9,
                    "Leaning A-shaped pylon" if not pylon_legend else None,
                    showlegend=not pylon_legend,
                ),
            )
            pylon_legend = True
        elif role.startswith("stay"):
            stay_y = -data["cable_plane_y"] if role.endswith("left") else data["cable_plane_y"]
            deck_end = np.array([p2[0], deck_left_curve(p2[0], data) + stay_y, p2[2] + outer_lane_rise(p2[0], stay_y, data)], dtype=float)
            add_trace(
                traces,
                line_trace(
                    [p1.tolist(), deck_end.tolist()],
                    "#6d28d9",
                    4,
                    "Outer stay cables" if not stay_legend else None,
                    showlegend=not stay_legend,
                ),
            )
            stay_legend = True
            dp1 = (p1 + disps[ni] * scale).tolist()
            deck_disp = disps[nj] * scale
            dp2 = [
                p2[0] + deck_disp[0],
                deck_left_curve(p2[0], data) + stay_y,
                p2[2] + outer_lane_rise(p2[0], stay_y, data) + deck_disp[2],
            ]
            add_trace(traces, line_trace([dp1, dp2], "#c084fc", 2, dash="dot"))

    def surface_trace(a_points, b_points, color):
        return {
            "type": "surface",
            "x": [[lt[0], rt[0]] for lt, rt in zip(a_points, b_points)],
            "y": [[lt[1], rt[1]] for lt, rt in zip(a_points, b_points)],
            "z": [[lt[2], rt[2]] for lt, rt in zip(a_points, b_points)],
            "showscale": False,
            "opacity": 0.35,
            "colorscale": [[0.0, color], [1.0, color]],
            "hoverinfo": "skip",
            "name": "Deck plate",
        }

    if full_left_top:
        add_trace(traces, surface_trace(full_left_top, full_right_top, "#8ecae6"))
    if main_left_top:
        add_trace(traces, surface_trace(main_left_top, main_right_top, "#6ee7b7"))
    if ramp_left_outer_top:
        add_trace(traces, surface_trace(ramp_left_outer_top, ramp_left_inner_top, "#fdba74"))
    if ramp_right_outer_top:
        add_trace(traces, surface_trace(ramp_right_inner_top, ramp_right_outer_top, "#fdba74"))

    layout = {
        "title": f"Asymmetric Cable-Stayed Bridge - {analysis_mode} 3D View",
        "scene": {
            "xaxis": {"title": "Bridge length (m)"},
            "yaxis": {"title": "Deck width (m)"},
            "zaxis": {"title": "Elevation (m)"},
            "aspectmode": "manual",
            "aspectratio": {"x": 3.7, "y": 1.0, "z": 1.2},
            "camera": {"eye": {"x": 1.7, "y": 1.5, "z": 0.9}},
        },
        "template": "plotly_white",
        "margin": {"l": 0, "r": 0, "t": 60, "b": 0},
        "legend": {"x": 0.02, "y": 0.98},
        "annotations": [
            {
                "text": (
                    f"Spans: 70 m + 180 m | Four lanes | Steel box girder: {data['section']['width']:.1f} m wide x {data['section']['depth']:.1f} m deep | "
                    f"Outer cable planes with leaning A-pylon | Outer lanes split into separate ramps, rise +10 m, and extend as 90-degree left-turn merge ramps | "
                    f"Stays: {len(data['stay_anchors'])} | Analysis: {analysis_mode}"
                ),
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "x": 0.01,
                "y": 1.05,
                "font": {"size": 12},
            }
        ],
    }

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Asymmetric Cable-Stayed Bridge</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body style="margin:0; background:#ffffff; font-family:Arial, sans-serif;">
  <div id="plot" style="width:100vw; height:100vh;"></div>
  <script>
    const data = {json.dumps(traces)};
    const layout = {json.dumps(layout)};
    Plotly.newPlot('plot', data, layout, {{responsive: true, displaylogo: false}});
  </script>
</body>
</html>
"""
    output_html.write_text(html, encoding="utf-8")
    return scale, max_disp


def main():
    data = bridge_definition()
    if ops is not None:
        try:
            disps, analysis_mode = run_opensees_model(data)
        except Exception:
            disps, analysis_mode = approximate_displacements(data)
    else:
        disps, analysis_mode = approximate_displacements(data)

    output_html = ROOT / "bridge_3d.html"
    scale, max_disp = make_html(data, disps, analysis_mode, output_html)

    deck_disps = [disps[tag][2] for tag in data["deck_nodes"].values()]
    sec = data["section"]
    print("Asymmetric cable-stayed bridge model prepared.")
    print(f"Requested spans: side {data['side_span']:.1f} m + main {data['main_span']:.1f} m")
    print(
        f"Steel box girder: {sec['width']:.1f} m wide x {sec['depth']:.1f} m deep "
        f"for {sec['lane_count']} traffic lanes"
    )
    print("Lane profile: center two lanes stay level, outer two lanes split into separate ramps and rise 10.0 m after the pylon")
    print("Alignment: all four lanes curve left after the pylon, with separators between the center deck and outer ramps")
    print("Ramp extension: upper side ramps continue beyond the bridge end and make a 90-degree left turn")
    print(f"Pylon lean: tower tip shifted {data['tower_lean_tip_offset']:.1f} m toward the main span")
    print(
        f"Plate thicknesses (top / bottom / web): "
        f"{sec['top_plate']*1000:.0f} / {sec['bottom_plate']*1000:.0f} / {sec['web_plate']*1000:.0f} mm"
    )
    print(f"Stay cables: {len(data['stay_anchors'])} total, arranged in two outer cable planes")
    print(f"Analysis mode used: {analysis_mode}")
    print(f"Max displacement magnitude: {max_disp:.6e} m")
    print(f"Deck vertical displacement range: {min(deck_disps):.6e} to {max(deck_disps):.6e} m")
    print(f"Deformed shape scale factor in HTML: {scale:.1f}")
    print(f"3D view written to: {output_html}")


if __name__ == "__main__":
    main()
