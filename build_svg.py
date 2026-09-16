"""
Generates dark_mode.svg and light_mode.svg for the GitHub profile README.
Run this ONCE to lay out the card. After that, today.py only rewrites the
text of the dynamic stat elements (it never touches layout/positions).

Uses explicit textLength on every <text>/<tspan> so columns line up exactly
regardless of which monospace font the renderer actually has installed.
"""

FONT = "'Cascadia Code','Fira Code',Consolas,Menlo,'DejaVu Sans Mono','Courier New',monospace"
CHAR_W = 8.4       # px per monospace character at FONT_SIZE below
FONT_SIZE = 14
LINE_H = 19
PAD = 26
PHOTO_ASPECT = 0.82   # width / height of the ASCII-art box -- like a portrait ID photo slot

def load_ascii_art(path='ascii_art.txt'):
    """
    Loads the ASCII-art 'drop zone'. Paste art from any online generator
    straight into ascii_art.txt (plain-text output, not HTML/ANSI) and this
    will pick it up as-is -- any size, any shape. No other file needs to change.
    """
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')  # normalize line endings
    raw = raw.expandtabs(4)                               # tabs from some generators -> spaces
    lines = raw.split('\n')
    while lines and lines[0].strip() == '':                # drop leading blank lines
        lines.pop(0)
    while lines and lines[-1].strip() == '':                # drop trailing blank lines
        lines.pop()
    lines = [ln.rstrip() for ln in lines]                   # trailing whitespace only; keep leading spaces (alignment)
    if not lines:
        raise SystemExit('ascii_art.txt is empty -- paste your ASCII art in there first.')
    if len(lines) > 200 or max(len(l) for l in lines) > 250:
        print(f'Warning: art is {max(len(l) for l in lines)} cols x {len(lines)} rows -- '
              'that will make a very large card. Consider a smaller export from the generator.')
    return lines


ASCII_LINES = load_ascii_art()

USERNAME = "samyogsilwal61-svg"
INFO_HEADER = f"{USERNAME}@github"

STATIC_BLOCKS = [
    (None, [
        ("OS", "Windows 10, Parrot OS, Linux"),
        ("Host", "Computer Engineering Student @ Advance College"),
        ("IDE", "VS Code, Unity, Blender"),
    ]),
    (None, [
        ("Languages.Programming", "Python, C++, C#, C"),
        ("Languages.Web", "HTML, CSS"),
        ("Languages.Real", "English, Nepali"),
    ]),
    (None, [
        ("Hobbies", "Art, Traveling, Playing & Making Games"),
    ]),
    ("Contact", [
        ("Email", "samyogsilwa161@gmail.com"),
        ("LinkedIn", "samyog-silwal-700850332"),
        ("Reddit", "u/SIRS4G"),
        ("YouTube", "@SIRS4G-001"),
    ]),
]

# Reserve enough room for large formatted numbers so a real run never overflows
NUM_RESERVE = 11          # e.g. "999,999,999"
LOC_LINE_RESERVE = len("- Lines of Code on GitHub: ") + NUM_RESERVE + len(" ( ") + NUM_RESERVE + len("++, ") + NUM_RESERVE + len("-- )")


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def tl(text):
    """textLength attr forcing exact monospace width for a string of len(text) chars."""
    n = len(text)
    return f' textLength="{n * CHAR_W:.1f}" lengthAdjust="spacing"' if n > 1 else ''


def build_theme(theme, value_col, total_col_chars):
    if theme == 'dark':
        bg, border, fg = '#0d1117', '#30363d', '#c9d1d9'
        accent, label, value, dim = '#7ee787', '#79c0ff', '#e6edf3', '#6e7681'
        art_color = '#58a6ff'
        add_color, del_color = '#3fb950', '#f85149'
    else:
        bg, border, fg = '#ffffff', '#d0d7de', '#24292f'
        accent, label, value, dim = '#1a7f37', '#0969da', '#24292f', '#8c959f'
        art_color = '#57606a'
        add_color, del_color = '#1a7f37', '#cf222e'

    art_w = max(len(l) for l in ASCII_LINES)
    art_h = len(ASCII_LINES)

    # Build the right-hand column as a flat list of render instructions
    right = []
    right.append(('title', INFO_HEADER))
    right.append(('rule', None))
    for title, fields in STATIC_BLOCKS:
        if title:
            right.append(('blank', None))
            right.append(('subtitle', title))
        for lab, val in fields:
            right.append(('static', lab, val))
        right.append(('blank', None))
    right.append(('subtitle', 'GitHub Stats'))
    right.append(('stat_repos', None))
    right.append(('stat_commits', None))
    right.append(('stat_loc', None))

    gap = 40
    right_col_w = total_col_chars * CHAR_W
    right_col_h = len(right) * LINE_H

    # --- Photo box: the ASCII art is fit-contained into a fixed ID-card-style
    # box (portrait aspect, same height as the text column) instead of being
    # drawn at native character size. This is what keeps proportions sane no
    # matter how big or small the pasted art is.
    box_h = right_col_h
    box_w = box_h * PHOTO_ASPECT
    native_w = art_w * CHAR_W
    native_h = art_h * LINE_H
    art_scale = min(box_w / native_w, box_h / native_h) if native_w and native_h else 1.0
    off_x = (box_w - native_w * art_scale) / 2
    off_y = (box_h - native_h * art_scale) / 2

    width = PAD * 2 + box_w + gap + right_col_w
    height = PAD * 2 + right_col_h

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}" xml:space="preserve">')
    svg.append(f'<rect width="100%" height="100%" rx="10" fill="{bg}" stroke="{border}" stroke-width="1"/>')
    svg.append(f'<style>text{{font-family:{FONT};font-size:{FONT_SIZE}px;white-space:pre;}}</style>')

    # Photo box frame (the "ID card photo slot")
    svg.append(f'<rect x="{PAD}" y="{PAD}" width="{box_w:.1f}" height="{box_h:.1f}" rx="6" fill="none" stroke="{border}" stroke-width="1"/>')

    # ASCII art, scaled uniformly to fit inside the box, then centered
    art_tx = PAD + off_x
    art_ty = PAD + off_y
    svg.append(f'<g transform="translate({art_tx:.1f},{art_ty:.1f})"><g fill="{art_color}" transform="scale({art_scale:.4f})">')
    for i, line in enumerate(ASCII_LINES):
        y = FONT_SIZE + i * LINE_H
        svg.append(f'<text x="0" y="{y:.0f}">{esc(line)}</text>')
    svg.append('</g></g>')

    # Right info column
    right_x = PAD + box_w + gap
    y = PAD + FONT_SIZE
    for item in right:
        kind = item[0]
        if kind == 'title':
            txt = item[1]
            svg.append(f'<text x="{right_x}" y="{y:.0f}" fill="{accent}" font-weight="bold"{tl(txt)}>{esc(txt)}</text>')
        elif kind == 'rule':
            txt = '-' * total_col_chars
            svg.append(f'<text x="{right_x}" y="{y:.0f}" fill="{dim}"{tl(txt)}>{txt}</text>')
        elif kind == 'subtitle':
            head = f'{item[1]} '
            txt = head + '-' * max(1, total_col_chars - len(head))
            svg.append(f'<text x="{right_x}" y="{y:.0f}" fill="{accent}"{tl(txt)}>{esc(txt)}</text>')
        elif kind == 'blank':
            pass
        elif kind == 'static':
            _, lab, val = item
            prefix = f'- {lab}: '
            d = '.' * max(1, value_col - len(prefix))
            full_prefix = prefix + d + ' '
            svg.append(
                f'<text x="{right_x}" y="{y:.0f}">'
                f'<tspan fill="{label}"{tl(full_prefix)}>{esc(full_prefix)}</tspan>'
                f'<tspan fill="{value}"{tl(val)}>{esc(val)}</tspan>'
                f'</text>'
            )
        elif kind == 'stat_repos':
            prefix = '- Repos: '
            d1 = '.' * 5
            mid = ' (Contributed: '
            tail = ')  |  Stars: '
            d2 = '.' * 8
            svg.append(
                f'<text x="{right_x}" y="{y:.0f}">'
                f'<tspan fill="{label}"{tl(prefix)}>{esc(prefix)}</tspan>'
                f'<tspan id="repo_data_dots" fill="{dim}"{tl(d1)}>{d1}</tspan>'
                f'<tspan id="repo_data" fill="{value}">0</tspan>'
                f'<tspan fill="{label}"{tl(mid)}>{esc(mid)}</tspan>'
                f'<tspan id="contrib_data" fill="{value}">0</tspan>'
                f'<tspan fill="{label}"{tl(tail)}>{esc(tail)}</tspan>'
                f'<tspan id="star_data_dots" fill="{dim}"{tl(d2)}>{d2}</tspan>'
                f'<tspan id="star_data" fill="{value}">0</tspan>'
                f'</text>'
            )
        elif kind == 'stat_commits':
            prefix = '- Commits: '
            d1 = '.' * 5
            mid = '  |  Followers: '
            d2 = '.' * 8
            svg.append(
                f'<text x="{right_x}" y="{y:.0f}">'
                f'<tspan fill="{label}"{tl(prefix)}>{esc(prefix)}</tspan>'
                f'<tspan id="commit_data_dots" fill="{dim}"{tl(d1)}>{d1}</tspan>'
                f'<tspan id="commit_data" fill="{value}">0</tspan>'
                f'<tspan fill="{label}"{tl(mid)}>{esc(mid)}</tspan>'
                f'<tspan id="follower_data_dots" fill="{dim}"{tl(d2)}>{d2}</tspan>'
                f'<tspan id="follower_data" fill="{value}">0</tspan>'
                f'</text>'
            )
        elif kind == 'stat_loc':
            prefix = '- Lines of Code on GitHub: '
            mid1, mid2, mid3 = ' ( ', ', ', ' )'
            svg.append(
                f'<text x="{right_x}" y="{y:.0f}">'
                f'<tspan fill="{label}"{tl(prefix)}>{esc(prefix)}</tspan>'
                f'<tspan id="loc_data" fill="{value}">0</tspan>'
                f'<tspan fill="{label}"{tl(mid1)}>{esc(mid1)}</tspan>'
                f'<tspan id="loc_add" fill="{add_color}">0++</tspan>'
                f'<tspan fill="{label}"{tl(mid2)}>{esc(mid2)}</tspan>'
                f'<tspan id="loc_del" fill="{del_color}">0--</tspan>'
                f'<tspan fill="{label}"{tl(mid3)}>{esc(mid3)}</tspan>'
                f'</text>'
            )
        y += LINE_H

    svg.append('</svg>')
    return '\n'.join(svg)


def compute_layout():
    """Work out value_col (where all values start) and the total column width in chars."""
    prefixes = []
    values = []
    for _title, fields in STATIC_BLOCKS:
        for lab, val in fields:
            prefixes.append(f'- {lab}: ')
            values.append(val)
    value_col = max(len(p) for p in prefixes) + 3
    max_static_line = max(value_col + len(v) for v in values)
    total_col_chars = max(len(INFO_HEADER), max_static_line, LOC_LINE_RESERVE, len('Contact ') + 10, len('GitHub Stats ') + 10)
    return value_col, total_col_chars


if __name__ == '__main__':
    value_col, total_col_chars = compute_layout()
    with open('dark_mode.svg', 'w') as f:
        f.write(build_theme('dark', value_col, total_col_chars))
    with open('light_mode.svg', 'w') as f:
        f.write(build_theme('light', value_col, total_col_chars))
    print('Built dark_mode.svg and light_mode.svg', 'value_col=', value_col, 'total_col_chars=', total_col_chars)
