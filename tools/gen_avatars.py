"""Genera los 30 avatares ilustrados (15 femeninos, 15 masculinos) en app/static/img/avatars/.

Estilo: busto plano dentro de un fondo de color (como las fotos de perfil ilustradas), con la
paleta del consultorio en fondos y ropa. Cada avatar combina tono de piel, peinado, color de
cabello, ropa y algún accesorio (lentes, barba, aretes) para que no haya dos iguales.

Uso:  python tools/gen_avatars.py
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "img" / "avatars"

BG = ["#c0cde6", "#dcebcc", "#e5def0", "#f3e3c8", "#d6e6f2", "#f2d7d9", "#e3eaf8", "#cfe8e0"]
SKIN = ["#f6d3b3", "#eebf98", "#d9a27a", "#b97d56", "#8d5a3b"]
HAIR = ["#2b1d14", "#4a2f1d", "#7a4a26", "#b07a3c", "#d9b26b", "#1c1c24", "#8a8a8a", "#5b2c1e"]
SHIRT = ["#012880", "#85b559", "#a393be", "#418d96", "#e07a5f", "#3d5a80", "#f2cc8f", "#6c4813"]
INK = "#2b1d14"

SHOULDERS = "M8 64 C8 50 19 44.5 32 44.5 C45 44.5 56 50 56 64 Z"


def shade(hex_color: str, k: float) -> str:
    """Oscurece (k<1) o aclara (k>1) un color."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    f = (lambda c: max(0, min(255, round(c * k)))) if k < 1 else (lambda c: round(c + (255 - c) * (k - 1)))
    return "#{:02x}{:02x}{:02x}".format(f(r), f(g), f(b))


# ---------- peinados: (detrás de la cabeza, delante) ----------
FEMALE_HAIR = {
    "largo": ("M18.5 30 C17 14 25.5 11.5 32 11.5 C38.5 11.5 47 14 45.5 30 L47 52 C40 55 24 55 17 52 Z",
              "M20 30 C19.5 16.5 26.5 13 32 13 C39 13 44.5 17 44 30 C41.5 21.5 36 19.5 30.5 20 C26 20.5 22 24 20 30 Z"),
    "bob": ("M18.5 30 C17.5 14.5 25.5 11.5 32 11.5 C38.5 11.5 46.5 14.5 45.5 30 L46 41 C42 43.5 22 43.5 18 41 Z",
            "M20 31 C19 16.5 26 13 32 13 C38 13 45 16.5 44 31 C43 23 40 19.5 32 19.5 C24 19.5 21 23 20 31 Z"),
    "chongo": ("M26 12.5 A6.5 6.5 0 1 1 38 12.5 A6.5 6.5 0 1 1 26 12.5 Z",
               "M20.5 29 C20 17.5 26 14.5 32 14.5 C38 14.5 44 17.5 43.5 29 C41 22.5 37 20.5 32 20.5 C27 20.5 23 22.5 20.5 29 Z"),
    "coleta": ("M42 16 C52 18 52 34 47 44 C45.5 36 46 26 42 22 Z",
               "M20.5 29.5 C20 17 26 13.5 32 13.5 C39 13.5 44.5 17 43.5 29 C41 21 34 19.5 28 21.5 C24.5 22.5 22 25.5 20.5 29.5 Z"),
    "rizado": ("M15 32 C12 22 17 12 25 11 C28 8 36 8 39 11 C47 12 52 22 49 32 C51 40 46 48 44 50 C38 52 26 52 20 50 C18 48 13 40 15 32 Z",
               "M20 28 C20 19 24 15 28 15.5 C30 13.5 34 13.5 36 15.5 C40 15 44 19 44 28 C42 23 38 21 35 22 C33 20.5 31 20.5 29 22 C26 21 22 23 20 28 Z"),
}
MALE_HAIR = {
    "corto": (None, "M20.5 28 C19.5 17 26 13.5 32 13.5 C39 13.5 44.5 17.5 43.5 28 C41 21.5 36.5 20.5 32 20.5 C27.5 20.5 23 21.5 20.5 28 Z"),
    "raya": (None, "M20.5 28.5 C19.5 17 25.5 13 32 13 C40 13 45 17.5 43.5 28 C42.5 22 39.5 19 34 18.5 C33 21 26 22.5 20.5 28.5 Z"),
    "rapado": (None, "M21 26 C21 18 26 15 32 15 C38 15 43 18 43 26 C40.5 21.5 36.5 20 32 20 C27.5 20 23.5 21.5 21 26 Z"),
    "copete": (None, "M20.5 28 C19.5 18 23 14 28 13 C30 9.5 38 9.5 41 13.5 C44.5 17 44.5 22 43.5 28 C41.5 21.5 37 19.5 32 20 C27 20.5 23 22 20.5 28 Z"),
    "rizos": (None, "M20 27 C19 20 22 15.5 26 15.5 C27 12.5 31 12 33 13.5 C35.5 11.5 40 13 40.5 16 C44 17 45 22 44 27 C42 22.5 38 21.5 35 22.5 C33 21 30 21 28 22.5 C25 21.5 22 23 20 27 Z"),
}

BEARD = "M21 30.5 C21.5 42 27.5 45.5 32 45.5 C36.5 45.5 42.5 42 43 30.5 C41 36.5 36.5 38.5 32 38.5 C27.5 38.5 23 36.5 21 30.5 Z"
MUSTACHE = "M27.5 35.6 C29.5 34.2 31 34.6 32 35.2 C33 34.6 34.5 34.2 36.5 35.6 C34.5 36.4 33 36.4 32 36 C31 36.4 29.5 36.4 27.5 35.6 Z"


def avatar(sex: str, bg: str, skin: str, hair_style: str, hair: str, shirt: str,
           glasses=False, beard=None, earrings=False, freckles=False, collar="crew") -> str:
    styles = FEMALE_HAIR if sex == "f" else MALE_HAIR
    back, front = styles[hair_style]
    neck = shade(skin, 0.9)
    parts = [f'<rect width="64" height="64" fill="{bg}"/>']
    parts.append(f'<path d="{SHOULDERS}" fill="{shirt}"/>')
    if back:   # el cabello largo cae sobre los hombros
        parts.append(f'<path d="{back}" fill="{shade(hair, 0.92)}"/>')
    if collar == "v":
        parts.append(f'<path d="M26.5 44.6 L32 52 L37.5 44.6 Z" fill="{neck}"/>')
    elif collar == "coat":   # bata clínica abierta
        parts.append(f'<path d="M8 64 C8 50 19 44.5 26 44.6 L32 64 Z" fill="#f4f6fb"/><path d="M56 64 C56 50 45 44.5 38 44.6 L32 64 Z" fill="#f4f6fb"/>')
    parts.append(f'<rect x="28" y="37" width="8" height="9" rx="3.5" fill="{neck}"/>')
    if collar == "crew":
        parts.append(f'<path d="M26 44.8 C28 47.2 36 47.2 38 44.8" fill="none" stroke="{shade(shirt, 0.8)}" stroke-width="1.4" stroke-linecap="round"/>')
    # orejas y cabeza
    parts.append(f'<ellipse cx="20.6" cy="30.5" rx="2.2" ry="3" fill="{skin}"/><ellipse cx="43.4" cy="30.5" rx="2.2" ry="3" fill="{skin}"/>')
    parts.append(f'<ellipse cx="32" cy="29" rx="11.6" ry="13.2" fill="{skin}"/>')
    if earrings:
        parts.append('<circle cx="20.4" cy="34.4" r="1.2" fill="#f2cc8f"/><circle cx="43.6" cy="34.4" r="1.2" fill="#f2cc8f"/>')
    if beard == "full":
        parts.append(f'<path d="{BEARD}" fill="{hair}"/>')
    # rasgos
    parts.append(f'<path d="M25.6 26.6 Q27.6 25.4 29.6 26.4 M34.4 26.4 Q36.4 25.4 38.4 26.6" fill="none" stroke="{shade(hair, 0.85)}" stroke-width="1.1" stroke-linecap="round"/>')
    parts.append(f'<circle cx="27.6" cy="30" r="1.3" fill="{INK}"/><circle cx="36.4" cy="30" r="1.3" fill="{INK}"/>')
    parts.append(f'<path d="M31.4 30.8 Q30.6 33.4 32.2 33.6" fill="none" stroke="{shade(skin, 0.78)}" stroke-width="1" stroke-linecap="round"/>')
    if beard == "mustache":
        parts.append(f'<path d="{MUSTACHE}" fill="{hair}"/>')
    parts.append(f'<path d="M28.6 36 Q32 38.8 35.4 36" fill="none" stroke="{shade(skin, 0.55)}" stroke-width="1.2" stroke-linecap="round"/>')
    parts.append(f'<circle cx="24.6" cy="33.4" r="1.9" fill="#e8858f" opacity=".22"/><circle cx="39.4" cy="33.4" r="1.9" fill="#e8858f" opacity=".22"/>')
    if freckles:
        parts.append(f'<g fill="{shade(skin, 0.72)}"><circle cx="25.6" cy="32.2" r=".45"/><circle cx="27" cy="33.2" r=".45"/><circle cx="37" cy="33.2" r=".45"/><circle cx="38.4" cy="32.2" r=".45"/></g>')
    parts.append(f'<path d="{front}" fill="{hair}"/>')
    if glasses:
        parts.append(f'<g fill="none" stroke="{INK}" stroke-width="1.1"><circle cx="27.6" cy="30" r="3.4"/><circle cx="36.4" cy="30" r="3.4"/><path d="M31 30 L33 30 M24.2 29.4 L21.6 28.6 M39.8 29.4 L42.4 28.6"/></g>')
    body = "".join(parts)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img">{body}</svg>\n'


# 15 + 15 combinaciones elegidas a mano para que no se repitan (piel, peinado, cabello, ropa, accesorios)
FEMALE = [
    dict(bg=0, skin=1, hair_style="largo", hair=1, shirt=3),
    dict(bg=1, skin=0, hair_style="bob", hair=4, shirt=0, earrings=True),
    dict(bg=2, skin=3, hair_style="rizado", hair=0, shirt=6),
    dict(bg=3, skin=2, hair_style="chongo", hair=2, shirt=2, glasses=True),
    dict(bg=4, skin=0, hair_style="coleta", hair=3, shirt=4, freckles=True),
    dict(bg=5, skin=4, hair_style="chongo", hair=5, shirt=1, earrings=True),
    dict(bg=6, skin=1, hair_style="bob", hair=7, shirt=5),
    dict(bg=7, skin=2, hair_style="largo", hair=0, shirt=7, collar="v"),
    dict(bg=0, skin=3, hair_style="coleta", hair=1, shirt=2),
    dict(bg=1, skin=0, hair_style="largo", hair=4, shirt=5, glasses=True),
    dict(bg=2, skin=4, hair_style="rizado", hair=5, shirt=3, earrings=True),
    dict(bg=3, skin=1, hair_style="chongo", hair=6, shirt=0, glasses=True),
    dict(bg=4, skin=2, hair_style="bob", hair=2, shirt=1, collar="v"),
    dict(bg=5, skin=0, hair_style="rizado", hair=3, shirt=7, freckles=True),
    dict(bg=6, skin=3, hair_style="largo", hair=7, shirt=4, collar="coat"),
]
MALE = [
    dict(bg=0, skin=1, hair_style="corto", hair=1, shirt=0),
    dict(bg=1, skin=0, hair_style="raya", hair=4, shirt=3, glasses=True),
    dict(bg=2, skin=3, hair_style="rizos", hair=0, shirt=6),
    dict(bg=3, skin=2, hair_style="copete", hair=2, shirt=5, beard="full"),
    dict(bg=4, skin=4, hair_style="rapado", hair=5, shirt=1),
    dict(bg=5, skin=0, hair_style="corto", hair=7, shirt=2, beard="mustache"),
    dict(bg=6, skin=1, hair_style="copete", hair=3, shirt=4, freckles=True),
    dict(bg=7, skin=3, hair_style="raya", hair=0, shirt=7, collar="v"),
    dict(bg=0, skin=2, hair_style="rizos", hair=1, shirt=3, beard="full"),
    dict(bg=1, skin=4, hair_style="corto", hair=5, shirt=4, glasses=True),
    dict(bg=2, skin=0, hair_style="rapado", hair=6, shirt=5, beard="full"),
    dict(bg=3, skin=1, hair_style="raya", hair=2, shirt=1, collar="coat"),
    dict(bg=4, skin=3, hair_style="copete", hair=5, shirt=0, glasses=True),
    dict(bg=5, skin=2, hair_style="corto", hair=3, shirt=6, beard="mustache"),
    dict(bg=6, skin=0, hair_style="rizos", hair=4, shirt=2),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for sex, specs in (("f", FEMALE), ("m", MALE)):
        assert len(specs) == 15
        for i, s in enumerate(specs, 1):
            svg = avatar(sex, BG[s["bg"]], SKIN[s["skin"]], s["hair_style"], HAIR[s["hair"]], SHIRT[s["shirt"]],
                         glasses=s.get("glasses", False), beard=s.get("beard"), earrings=s.get("earrings", False),
                         freckles=s.get("freckles", False), collar=s.get("collar", "crew"))
            (OUT / f"{sex}{i:02d}.svg").write_text(svg, encoding="utf-8")
    print(f"30 avatares en {OUT}")


if __name__ == "__main__":
    main()
