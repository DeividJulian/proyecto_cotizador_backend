"""Generates the presentation slide (1920x1080) as an editable .pptx and as an .html that Chrome turns into .png/.pdf.

    python presentacion/generar_diapositiva.py          (needs python-pptx; Chrome for the png and pdf)

Everything on the slide comes from the code of this project and of cotizador-front.
"""
import html
import shutil
import subprocess
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu, Pt

HERE = Path(__file__).resolve().parent
W, H = 1920, 1080
FONT = "Segoe UI"

BG, CARD, BORDER = "0F1419", "182029", "2A3542"
TEXT, MUTED, ACCENT, AI = "F2F5F8", "B6C2CF", "4FB3FF", "B79CFF"

TITLE = "Cotizador IA"
TAGLINE = "Convierte la descripción de un proyecto de software en una cotización: módulos, horas PERT, precio y propuesta comercial."
AUDIENCE = "Para freelancers que no saben cuánto cobrar."

# (title, color, lines)
BLOCKS = [
    ("Frontend", ACCENT, ["Angular 21 + TypeScript", "Signals y standalone", "Web, Shared y Service Worker"]),
    ("Backend", ACCENT, ["FastAPI + Pydantic", "SQLAlchemy", "Contrato OpenAPI versionado"]),
    ("Datos y despliegue", ACCENT, ["PostgreSQL en Neon", "API en Render", "Front en Vercel"]),
    ("Comunicación", ACCENT, ["REST con cliente generado", "gRPC: Connect + Protobuf", "Progreso en streaming"]),
    ("Algoritmos", ACCENT, ["Módulos por catálogo", "Estimación PERT", "Monte Carlo y TF-IDF"]),
    ("Inteligencia artificial", AI, ["Groq con JSON estricto", "Segunda opinión y textos", "No cambia horas ni precios"]),
    ("Seguridad", ACCENT, ["Login con código al correo", "JWT y CORS limitado", "Sin datos personales a la IA"]),
    ("Calidad", ACCENT, ["Pytest y Vitest", "Respuestas parseadas (Zod)", "Tipos de la BD al componente"]),
]

# Layout in pixels (shared by the pptx and the html)
MARGIN_X, TOP = 96, 64
COLS, ROWS, GAP = 4, 2, 32
GRID_TOP = 420
CARD_W = (W - 2 * MARGIN_X - (COLS - 1) * GAP) // COLS
CARD_H = (H - GRID_TOP - 64 - (ROWS - 1) * GAP) // ROWS
TITLE_PX, TAGLINE_PX, AUDIENCE_PX, BLOCK_TITLE_PX, BLOCK_TEXT_PX = 96, 36, 30, 32, 26


def px(value: float) -> Emu:
    return Emu(int(value * 9525))  # 1 px at 96 dpi = 9525 EMU


def rgb(hex_color: str) -> RGBColor:
    return RGBColor.from_string(hex_color)


def text_box(slide, x, y, w, h, paragraphs):
    """paragraphs: list of (text, size_px, color, bold, space_before_px)."""
    box = slide.shapes.add_textbox(px(x), px(y), px(w), px(h))
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    for i, (text, size, color, bold, before) in enumerate(paragraphs):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.space_before = Pt(before * 0.75)
        run = p.add_run()
        run.text = text
        run.font.name = FONT
        run.font.size = Pt(size * 0.75)  # px -> pt
        run.font.bold = bold
        run.font.color.rgb = rgb(color)
    return box


def build_pptx(path: Path) -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = px(W), px(H)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(BG)

    bar = slide.shapes.add_shape(1, px(MARGIN_X), px(TOP), px(120), px(10))
    bar.fill.solid()
    bar.fill.fore_color.rgb = rgb(ACCENT)
    bar.line.fill.background()

    text_box(slide, MARGIN_X, TOP + 36, W - 2 * MARGIN_X, 130, [(TITLE, TITLE_PX, TEXT, True, 0)])
    text_box(
        slide, MARGIN_X, TOP + 168, W - 2 * MARGIN_X, 130,
        [(TAGLINE, TAGLINE_PX, TEXT, False, 0), (AUDIENCE, AUDIENCE_PX, MUTED, False, 10)],
    )

    for i, (title, color, lines) in enumerate(BLOCKS):
        col, row = i % COLS, i // COLS
        x = MARGIN_X + col * (CARD_W + GAP)
        y = GRID_TOP + row * (CARD_H + GAP)
        card = slide.shapes.add_shape(5, px(x), px(y), px(CARD_W), px(CARD_H))  # rounded rectangle
        card.adjustments[0] = 0.06
        card.fill.solid()
        card.fill.fore_color.rgb = rgb(CARD)
        card.line.color.rgb = rgb(BORDER)
        card.line.width = px(2)
        accent = slide.shapes.add_shape(1, px(x + 28), px(y + 28), px(48), px(6))
        accent.fill.solid()
        accent.fill.fore_color.rgb = rgb(color)
        accent.line.fill.background()
        paragraphs = [(title, BLOCK_TITLE_PX, TEXT, True, 0)]
        paragraphs += [(line, BLOCK_TEXT_PX, MUTED, False, 12) for line in lines]
        text_box(slide, x + 28, y + 52, CARD_W - 56, CARD_H - 72, paragraphs)
    prs.save(path)


def build_html(path: Path) -> None:
    cards = "\n".join(
        f'<div class="card"><span class="accent" style="background:#{color}"></span>'
        f"<h2>{html.escape(title)}</h2>" + "".join(f"<p>{html.escape(line)}</p>" for line in lines) + "</div>"
        for title, color, lines in BLOCKS
    )
    page = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>{TITLE}</title>
<style>
  @page {{ size: {W}px {H}px; margin: 0; }}
  * {{ box-sizing: border-box; margin: 0; }}
  html, body {{ width: {W}px; height: {H}px; background: #{BG}; color: #{TEXT}; font-family: '{FONT}', system-ui, sans-serif; }}
  body {{ position: relative; overflow: hidden; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .bar {{ position: absolute; left: {MARGIN_X}px; top: {TOP}px; width: 120px; height: 10px; background: #{ACCENT}; border-radius: 5px; }}
  h1 {{ position: absolute; left: {MARGIN_X}px; top: {TOP + 36}px; font-size: {TITLE_PX}px; line-height: 1.15; font-weight: 700; letter-spacing: -1px; }}
  .tagline {{ position: absolute; left: {MARGIN_X}px; top: {TOP + 168}px; width: {W - 2 * MARGIN_X}px; }}
  .tagline p:first-child {{ font-size: {TAGLINE_PX}px; line-height: 1.3; }}
  .tagline p + p {{ font-size: {AUDIENCE_PX}px; color: #{MUTED}; margin-top: 10px; }}
  .grid {{ position: absolute; left: {MARGIN_X}px; top: {GRID_TOP}px; display: grid;
    grid-template-columns: repeat({COLS}, {CARD_W}px); grid-auto-rows: {CARD_H}px; gap: {GAP}px; }}
  .card {{ background: #{CARD}; border: 2px solid #{BORDER}; border-radius: 18px; padding: 28px; overflow: hidden; }}
  .accent {{ display: block; width: 48px; height: 6px; border-radius: 3px; margin-bottom: 18px; }}
  h2 {{ font-size: {BLOCK_TITLE_PX}px; line-height: 1.25; margin-bottom: 4px; }}
  .card p {{ font-size: {BLOCK_TEXT_PX}px; line-height: 1.3; color: #{MUTED}; margin-top: 12px; }}
</style></head>
<body>
  <span class="bar"></span>
  <h1>{TITLE}</h1>
  <div class="tagline"><p>{html.escape(TAGLINE)}</p><p>{html.escape(AUDIENCE)}</p></div>
  <div class="grid">
{cards}
  </div>
</body></html>
"""
    path.write_text(page, encoding="utf-8")


def chrome() -> str | None:
    for candidate in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        shutil.which("google-chrome") or "",
        shutil.which("chromium") or "",
    ):
        if candidate and Path(candidate).exists():
            return candidate
    return None


def main() -> None:
    build_pptx(HERE / "Cotizador-IA.pptx")
    source = HERE / "diapositiva.html"
    build_html(source)
    browser = chrome()
    if not browser:
        print("Sin Chrome: solo se generaron el .pptx y el .html")
        return
    common = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={W},{H}"]
    subprocess.run([*common, f"--screenshot={HERE / 'Cotizador-IA.png'}", source.as_uri()], check=True)
    subprocess.run(
        [*common, f"--print-to-pdf={HERE / 'Cotizador-IA.pdf'}", "--no-pdf-header-footer", source.as_uri()], check=True
    )
    print("Listo: Cotizador-IA.pptx, Cotizador-IA.png y Cotizador-IA.pdf")


if __name__ == "__main__":
    main()
