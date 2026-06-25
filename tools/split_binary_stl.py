import argparse
import math
import pathlib
import struct
from collections import defaultdict, deque


def read_binary_stl(path):
    data = pathlib.Path(path).read_bytes()
    if len(data) < 84:
        raise ValueError("STL is too small")
    count = struct.unpack_from("<I", data, 80)[0]
    expected = 84 + count * 50
    if expected != len(data):
        raise ValueError(f"Expected {expected} bytes, got {len(data)}")

    triangles = []
    offset = 84
    for index in range(count):
        values = struct.unpack_from("<12fH", data, offset)
        normal = values[0:3]
        verts = [values[3:6], values[6:9], values[9:12]]
        triangles.append((index, normal, verts, values[12]))
        offset += 50
    return data[:80], triangles


def key(vertex, quant):
    return tuple(int(round(coord / quant)) for coord in vertex)


def component_stats(component, triangles):
    xs, ys, zs = [], [], []
    for tri_index in component:
        _, _, verts, _ = triangles[tri_index]
        for x, y, z in verts:
            xs.append(x)
            ys.append(y)
            zs.append(z)
    return {
        "triangles": len(component),
        "min": (min(xs), min(ys), min(zs)),
        "max": (max(xs), max(ys), max(zs)),
        "size": (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)),
        "center": (
            (min(xs) + max(xs)) / 2,
            (min(ys) + max(ys)) / 2,
            (min(zs) + max(zs)) / 2,
        ),
    }


def find_components(triangles, quant):
    vertex_to_tris = defaultdict(list)
    for tri_index, (_, _, verts, _) in enumerate(triangles):
        for vertex in verts:
            vertex_to_tris[key(vertex, quant)].append(tri_index)

    visited = [False] * len(triangles)
    components = []
    for start in range(len(triangles)):
        if visited[start]:
            continue
        visited[start] = True
        queue = deque([start])
        component = []
        while queue:
            tri_index = queue.popleft()
            component.append(tri_index)
            for vertex in triangles[tri_index][2]:
                for neighbor in vertex_to_tris[key(vertex, quant)]:
                    if not visited[neighbor]:
                        visited[neighbor] = True
                        queue.append(neighbor)
        components.append(component)
    return components


def write_binary_stl(path, header, triangles, component, translate=(0.0, 0.0, 0.0)):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out_header = header[:80].ljust(80, b" ")
    with path.open("wb") as stream:
        stream.write(out_header)
        stream.write(struct.pack("<I", len(component)))
        for tri_index in component:
            _, normal, verts, attr = triangles[tri_index]
            stream.write(struct.pack("<3f", *normal))
            for vertex in verts:
                stream.write(
                    struct.pack(
                        "<3f",
                        vertex[0] - translate[0],
                        vertex[1] - translate[1],
                        vertex[2] - translate[2],
                    )
                )
            stream.write(struct.pack("<H", attr))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--quant", type=float, default=0.001)
    parser.add_argument("--min-triangles", type=int, default=100)
    parser.add_argument("--out-dir")
    parser.add_argument("--select-ranks", nargs="*", type=int)
    parser.add_argument("--combined-output")
    parser.add_argument("--translate", nargs=3, type=float, default=(0.0, 0.0, 0.0))
    args = parser.parse_args()

    header, triangles = read_binary_stl(args.input)
    components = find_components(triangles, args.quant)
    rows = []
    for index, component in enumerate(components):
        stats = component_stats(component, triangles)
        rows.append((index, component, stats))

    rows.sort(key=lambda item: item[2]["triangles"], reverse=True)
    print(f"triangles={len(triangles)} components={len(rows)} quant={args.quant}")
    for rank, (index, component, stats) in enumerate(rows):
        if stats["triangles"] < args.min_triangles:
            continue
        min_xyz = " ".join(f"{v:.3f}" for v in stats["min"])
        max_xyz = " ".join(f"{v:.3f}" for v in stats["max"])
        size_xyz = " ".join(f"{v:.3f}" for v in stats["size"])
        center_xyz = " ".join(f"{v:.3f}" for v in stats["center"])
        print(
            f"rank={rank:03d} component={index:04d} tris={stats['triangles']:6d} "
            f"min=[{min_xyz}] max=[{max_xyz}] size=[{size_xyz}] center=[{center_xyz}]"
        )
        if args.out_dir:
            name = f"component_{rank:03d}_tris_{stats['triangles']}.stl"
            write_binary_stl(pathlib.Path(args.out_dir) / name, header, triangles, component)

    if args.select_ranks and args.combined_output:
        rank_to_component = {rank: component for rank, (_, component, _) in enumerate(rows)}
        combined = []
        for rank in args.select_ranks:
            combined.extend(rank_to_component[rank])
        write_binary_stl(args.combined_output, header, triangles, combined, args.translate)
        print(f"wrote {len(combined)} triangles to {args.combined_output}")


if __name__ == "__main__":
    main()
