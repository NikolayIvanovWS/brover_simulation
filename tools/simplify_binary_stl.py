import argparse
import pathlib
import struct


def read_stl(path):
    data = pathlib.Path(path).read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    expected = 84 + count * 50
    if expected != len(data):
        raise ValueError(f"Expected {expected} bytes, got {len(data)}")

    triangles = []
    offset = 84
    for _ in range(count):
        values = struct.unpack_from("<12fH", data, offset)
        triangles.append([values[3:6], values[6:9], values[9:12]])
        offset += 50
    return data[:80], triangles


def quantize(vertex, grid):
    return tuple(round(coord / grid) * grid for coord in vertex)


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def normalize(vector):
    length = sum(coord * coord for coord in vector) ** 0.5
    if length == 0:
        return None
    return tuple(coord / length for coord in vector)


def normal_for(triangle):
    a, b, c = triangle
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    return normalize(cross(ab, ac))


def simplify(triangles, grid):
    simplified = []
    seen = set()

    for triangle in triangles:
        snapped = [quantize(vertex, grid) for vertex in triangle]
        if len(set(snapped)) < 3:
            continue

        normal = normal_for(snapped)
        if normal is None:
            continue

        key = tuple(sorted(snapped))
        if key in seen:
            continue
        seen.add(key)
        simplified.append((normal, snapped))

    return simplified


def write_stl(path, header, triangles):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(header[:80].ljust(80, b" "))
        stream.write(struct.pack("<I", len(triangles)))
        for normal, vertices in triangles:
            stream.write(struct.pack("<3f", *normal))
            for vertex in vertices:
                stream.write(struct.pack("<3f", *vertex))
            stream.write(struct.pack("<H", 0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--grid", type=float, default=1.0)
    args = parser.parse_args()

    header, triangles = read_stl(args.input)
    simplified = simplify(triangles, args.grid)
    write_stl(args.output, header, simplified)
    print(
        f"{pathlib.Path(args.input).name}: "
        f"{len(triangles)} -> {len(simplified)} triangles, grid={args.grid}"
    )


if __name__ == "__main__":
    main()
