"""
Converts a photo into a block of ASCII/character art sized for embedding
in the profile README SVG, matching the neofetch-style look.

Usage: python3 img_to_ascii.py <input_image> <output_txt> [width]
"""
import sys
from PIL import Image

# Characters ordered from darkest/densest to lightest, like the reference art
CHARS = "@%#*+=-:. "

def image_to_ascii(path, width=42):
    img = Image.open(path).convert("RGBA")

    # Composite onto white background (flatten transparency) then grayscale
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    img = Image.alpha_composite(bg, img).convert("L")
    w, h = img.size

    # Monospace chars are taller than wide, so compress vertical sampling
    aspect_correction = 0.5
    cell_w = w / width
    new_h = int((h / w) * width * aspect_correction)
    cell_h = h / new_h

    px = img.load()
    avgs = []
    for row in range(new_h):
        y0, y1 = int(row * cell_h), int((row + 1) * cell_h)
        row_avgs = []
        for col in range(width):
            x0, x1 = int(col * cell_w), int((col + 1) * cell_w)
            total, s = 0, 0
            for yy in range(y0, max(y1, y0 + 1)):
                for xx in range(x0, max(x1, x0 + 1)):
                    total += 1
                    s += px[xx, yy]
            row_avgs.append(s / total if total else 255)
        avgs.append(row_avgs)

    # Histogram-equalize the block averages so the full character ramp gets
    # used regardless of how light/dark the specific source photo is -- this
    # is what makes fine facial detail show up instead of washing out to gray.
    flat = sorted(v for row in avgs for v in row)
    n = len(flat)

    def percentile_rank(v):
        # position of v within the sorted distribution, 0 (darkest) -> 1 (lightest).
        # Uses the *right* insertion point so that ties at the (very common)
        # background value correctly land at rank ~1.0 instead of the middle.
        lo, hi = 0, n
        while lo < hi:
            mid = (lo + hi) // 2
            if flat[mid] <= v:
                lo = mid + 1
            else:
                hi = mid
        return (lo - 1) / max(1, n - 1)

    lines = []
    for row_avgs in avgs:
        line = []
        for v in row_avgs:
            rank = percentile_rank(v)
            idx = int(rank * (len(CHARS) - 1))
            line.append(CHARS[idx])
        lines.append("".join(line))

    return "\n".join(lines)

if __name__ == "__main__":
    inp = sys.argv[1]
    outp = sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 42
    art = image_to_ascii(inp, width)
    with open(outp, "w") as f:
        f.write(art)
    print(art)
