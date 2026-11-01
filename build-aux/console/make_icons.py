"""Generate controller button prompt SVGs for High Tide console mode."""
import sys
from pathlib import Path

out = Path(sys.argv[1])

DARK = "#2e2e32"
HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
FONT = "font-family=\"Cantarell, 'Noto Sans', sans-serif\" font-weight=\"bold\""


def circle(inner):
    return f'{HEAD}<circle cx="32" cy="32" r="29" fill="{DARK}"/>{inner}</svg>\n'


def letter(ch, color, size=34):
    return (f'<text x="32" y="{32 + size * 0.36:.1f}" text-anchor="middle" '
            f'font-size="{size}" {FONT} fill="{color}">{ch}</text>')


def pill(text, size=20, width=60):
    x = (64 - width) / 2
    return (f'{HEAD}<rect x="{x}" y="14" width="{width}" height="36" rx="12" '
            f'fill="{DARK}"/>{letter(text, "#ffffff", size).replace("y=", "y=", 1)}</svg>\n')


def menu_icon():
    bars = "".join(f'<rect x="21" y="{y}" width="22" height="4" rx="2" fill="#fff"/>'
                   for y in (22, 30, 38))
    return circle(bars)


def view_icon():
    return circle('<rect x="18" y="20" width="18" height="14" rx="3" fill="none" '
                  'stroke="#fff" stroke-width="3.5"/><rect x="28" y="30" width="18" '
                  f'height="14" rx="3" fill="{DARK}" stroke="#fff" stroke-width="3.5"/>')


def stick(side):
    return (f'{HEAD}<circle cx="32" cy="32" r="29" fill="{DARK}"/>'
            '<circle cx="32" cy="32" r="18" fill="none" stroke="#fff" '
            f'stroke-width="3" opacity="0.6"/>{letter(side, "#ffffff", 22)}</svg>\n')


def dpad():
    return (f'{HEAD}<path d="M24 6h16v18h18v16H40v18H24V40H6V24h18z" fill="{DARK}"/>'
            '<path d="M32 10l5 7h-10zM32 54l5-7h-10zM10 32l7-5v10zM54 32l-7-5v10z" '
            'fill="#fff" opacity="0.8"/></svg>\n')


styles = {
    "xbox": {
        "a": circle(letter("A", "#6bbf3a")),
        "b": circle(letter("B", "#e2453c")),
        "x": circle(letter("X", "#3c8be2")),
        "y": circle(letter("Y", "#f2c230")),
        "lb": pill("LB"), "rb": pill("RB"), "lt": pill("LT"), "rt": pill("RT"),
        "start": menu_icon(), "select": view_icon(),
    },
    "playstation": {
        # cross, circle, square, triangle in the usual places
        "a": circle('<path d="M20 20l24 24M44 20L20 44" stroke="#7ea6e0" '
                    'stroke-width="5" stroke-linecap="round"/>'),
        "b": circle('<circle cx="32" cy="32" r="13" fill="none" stroke="#ff6b6b" '
                    'stroke-width="5"/>'),
        "x": circle('<rect x="20" y="20" width="24" height="24" fill="none" '
                    'stroke="#d48ccf" stroke-width="5"/>'),
        "y": circle('<path d="M32 17L46 42H18z" fill="none" stroke="#3fc9a6" '
                    'stroke-width="5" stroke-linejoin="round"/>'),
        "lb": pill("L1"), "rb": pill("R1"), "lt": pill("L2"), "rt": pill("R2"),
        "start": menu_icon(), "select": view_icon(),
    },
    "steamdeck": {
        "a": circle(letter("A", "#ffffff")),
        "b": circle(letter("B", "#ffffff")),
        "x": circle(letter("X", "#ffffff")),
        "y": circle(letter("Y", "#ffffff")),
        "lb": pill("L1"), "rb": pill("R1"), "lt": pill("L2"), "rt": pill("R2"),
        "start": menu_icon(), "select": view_icon(),
    },
}

for style, icons in styles.items():
    folder = out / style
    folder.mkdir(parents=True, exist_ok=True)
    icons["dpad"] = dpad()
    icons["rstick"] = stick("R")
    for name, svg in icons.items():
        (folder / f"{name}.svg").write_text(svg)
        print(f"    <file>icons/console/{style}/{name}.svg</file>")
