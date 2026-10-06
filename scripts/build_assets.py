"""
Builds every SVG in the profile README (orbit + pipeline design), light and dark.

    pip install fonttools brotli
    python scripts/build_assets.py

Fonts (Space Grotesk, JetBrains Mono, both OFL) are subset per SVG and embedded,
so GitHub renders the real typefaces. In GitHub Actions the script also pulls
your contribution count for the pipeline header (needs GITHUB_TOKEN).

Edit the CONTENT section to change any text.
"""
import base64
import io
import json
import math
import os
import random
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS, DATA, FONTS = ROOT / "assets", ROOT / "data", ROOT / "fonts"
USER = "M-Wajeeh"

# ═══════════════════════════════ CONTENT ═══════════════════════════════

HANDLE = "~/M-Wajeeh"
NAME = ["Wajeeh", "Ul Hassan"]
TAGLINE = "AI/ML engineer building LLM agents, RAG systems and ML pipelines that actually reach production."
STATUS = "status: ready to deploy"

ORBIT = [  # (ring, tools)
    ("genai", ["LangChain", "RAG", "Agents"]),
    ("ml", ["PyTorch", "XGBoost", "OpenCV", "scikit-learn"]),
    ("ops", ["Docker", "FastAPI", "MLflow", "DVC", "AWS"]),
]

FACTS = [("Based in", "Islamabad, Pakistan"), ("Focus", "GenAI and MLOps"),
         ("Latest win", "Vyrothon AI Hackathon, 1st")]

STAGES = [  # (stage, title, subtitle, when)
    ("data", "NUML Islamabad", "BS Artificial Intelligence", "2022 – 2026"),
    ("train", "SiberKoza Alpha", "AI/ML Engineer Intern, NASTP", "Jul – Sep 2025"),
    ("evaluate", "Vyrothon", "AI Hackathon, 1st of 580+", "2026"),
    ("fine-tune", "CESAI, EME", "AI Engineer Intern", "Jul – Sep 2026"),
    ("deploy", "Your team", "Full-time AI/ML role", "now"),
]
LOG = [  # (when, stage, passed, text)
    ("2022", "data", True, "BS Artificial Intelligence, NUML Islamabad"),
    ("2025", "train", True, "ML pipelines on 80K+ records, ~88% accuracy, 40+ MLflow runs"),
    ("2026", "evaluate", True, "Vyrothon AI Hackathon: 1st among 580+ participants"),
    ("2026", "fine-tune", True, "defect detection at 83.5%, LLM chatbot for borescope inspection"),
    ("now", "deploy", False, "waiting for an AI/ML team"),
]

METRICS = [("1st", "of 580+ at the Vyrothon AI Hackathon", "sunText"),
           ("90.2%", "accuracy on PurchasePulse, 0.89 AUC", "text"),
           ("80K+", "records through production ML pipelines", "text"),
           ("40+", "experiments tracked in MLflow", "text")]

PROJECTS = [  # slug, type, title, chip, featured, desc, stack, link text
    ("tryon", "diffusion", "AI Virtual Try-On", "final year project", True,
     "Puts any garment on a person photo using diffusion inpainting guided by body pose.",
     ["PyTorch", "CatVTON", "Stable Diffusion", "OpenPose"]),
    ("purchasepulse", "model", "PurchasePulse", "90.2% acc", True,
     "Real-time purchase intent API with experiment tracking, data versioning and automated retraining.",
     ["XGBoost", "FastAPI", "MLflow", "DVC"]),
    ("rag", "rag", "RAG Insight Engine", "grounded", False,
     "Ask questions over your documents and get answers that cite their source chunks.",
     ["embeddings", "ChromaDB", "LLMs"]),
    ("n8n", "agent", "n8n AI Search Assistant", "voice agent", False,
     "Whisper transcribes, Llama 3.3 routes intent to web research or data lookup.",
     ["n8n", "Whisper", "Llama 3.3"]),
    ("insurance", "pipeline", "Vehicle Insurance MLOps", "end to end", False,
     "MongoDB to a FastAPI service on EC2, with data validation, S3 model storage and CI/CD.",
     ["FastAPI", "Docker", "AWS", "GitHub Actions"]),
    ("sql", "analytics", "SQL Customer Analytics", "SQL Server", False,
     "End-to-end SQL Server project turning raw customer data into business insights.",
     ["SQL Server", "T-SQL"]),
]
TYPE_COLOR = {"diffusion": "genai", "model": "ml", "rag": "genai", "agent": "genai",
              "pipeline": "ops", "analytics": "ml"}

ENDPOINTS = [("portfolio", "GET", "/portfolio", "m-wajeeh.dev", False),
             ("linkedin", "GET", "/linkedin", "in/hassanwajeeh", False),
             ("github", "GET", "/github", "M-Wajeeh", False),
             ("hire", "POST", "/hire", "wajeeh9233@gmail.com", True)]

CERTS = ["oracle-generative-ai-professional", "oracle-oci-ai-foundations-associate",
         "coursera-machine-learning", "coursera-excel", "udemy-data-analytics-bootcamp"]
LEARNING = ["LangSmith", "DeepEval", "Great Expectations", "agentic AI", "CI/CD for ML"]
FUN_FACT = "Fun fact: I have spent more time hunting one missing comma than watching an entire Netflix series."

# ═══════════════════════════════ THEMES ═══════════════════════════════

THEMES = {
    "dark": dict(hero="#11173A", surface="#141B40", log="#0E1433", chip="#1C2452", line="#262F63",
                 line2="#3A4583", track="#232B5C", text="#EEF0FA", muted="#A9AFD0", faint="#7880A8",
                 accent="#9DB1FF", sun="#F5B544", sunText="#F5B544", sunInk="#3A2600", genai="#B3A6FF", ml="#5FD4C2",
                 ops="#FF9B78", ok="#5FD4C2", okInk="#06322B", okText="#8FE6D8", okBg="#163a4a",
                 okLine="#2f7d78", star="#FFFFFF", starOp=".9"),
    "light": dict(hero="#F5F7FD", surface="#FFFFFF", log="#F7F8FD", chip="#EEF1FA", line="#DDE2F0",
                  line2="#B7BFD9", track="#E3E7F3", text="#141A3A", muted="#4B5275", faint="#6B7194",
                  accent="#3550D4", sun="#F2A91F", sunText="#A8640A", sunInk="#3A2600", genai="#5B45D6", ml="#0E8576",
                  ops="#CC4D23", ok="#0E8576", okInk="#FFFFFF", okText="#0B6B5F", okBg="#E3F3F0",
                  okLine="#9ACFC6", star="#3550D4", starOp=".45"),
}

FONT_FILES = {("sg", 400): "SpaceGrotesk-Regular.ttf", ("sg", 500): "SpaceGrotesk-Medium.ttf",
              ("sg", 700): "SpaceGrotesk-Bold.ttf", ("jb", 400): "JetBrainsMono-Regular.ttf",
              ("jb", 500): "JetBrainsMono-Medium.ttf"}
FAMILY = {"sg": "Space Grotesk", "jb": "JetBrains Mono"}
STACK = {"sg": "'Space Grotesk','Segoe UI',system-ui,sans-serif",
         "jb": "'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"}

_fonts = {}


def font(fam, w):
    key = (fam, w)
    if key not in _fonts:
        f = TTFont(FONTS / FONT_FILES[key])
        _fonts[key] = (f, f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm)
    return _fonts[key]


def measure(s, fam="sg", w=400, size=14, ls=0):
    _, cmap, hmtx, upm = font(fam, w)
    total = 0
    for ch in s:
        g = cmap.get(ord(ch))
        total += (hmtx[g][0] if g else upm * 0.55) * size / upm
    return total + ls * max(len(s) - 1, 0)


def wrap(s, width, fam="sg", w=400, size=14):
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if cur and measure(trial, fam, w, size) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur]


class SVG:
    """Collects body markup and the characters used per font, then embeds subset fonts."""

    def __init__(self, w, h, label):
        self.w, self.h, self.label = w, h, label
        self.body, self.css = [], []
        self.used = defaultdict(set)

    def add(self, s):
        self.body.append(s)

    def text(self, x, y, s, fill, size=14, fam="sg", w=400, anchor=None, extra="", ls=None):
        self.used[(fam, w)].update(s)
        a = f' text-anchor="{anchor}"' if anchor else ""
        l = f' letter-spacing="{ls}"' if ls is not None else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{STACK[fam]}" font-size="{size}" '
                 f'font-weight="{w}" fill="{fill}"{a}{l} {extra}>{escape(s)}</text>')

    def font_faces(self):
        out = []
        for (fam, w), chars in sorted(self.used.items()):
            f = TTFont(FONTS / FONT_FILES[(fam, w)])
            opts = Options()
            opts.flavor = "woff2"
            opts.layout_features = ["kern", "liga"]
            sub = Subsetter(opts)
            sub.populate(text="".join(chars) + " ")
            sub.subset(f)
            buf = io.BytesIO()
            f.flavor = "woff2"
            f.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            out.append(f"@font-face{{font-family:'{FAMILY[fam]}';font-weight:{w};"
                       f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
        return "".join(out)

    def render(self):
        css = (self.font_faces() + "".join(self.css) +
               "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
                f'height="{self.h}" role="img" aria-label="{escape(self.label)}"><style>{css}</style>'
                + "".join(self.body) + "</svg>")


def card(x, y, w, h, fill, stroke, rx=16, dash=False):
    d = ' stroke-dasharray="5 4"' if dash else ""
    return (f'<rect x="{x+.5:.1f}" y="{y+.5:.1f}" width="{w-1:.1f}" height="{h-1:.1f}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}"{d}/>')


def pulse_dot(cx, cy, color, r=4.5):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" opacity=".7">'
            f'<animate attributeName="r" values="{r};{r*2.6}" dur="1.8s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values=".7;0" dur="1.8s" repeatCount="indefinite"/></circle>')


# ═══════════════════════════════ DATA ═══════════════════════════════

def contributions():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    cache = DATA / "contributions.json"
    if token:
        try:
            q = "query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{totalContributions}}}}"
            req = urllib.request.Request("https://api.github.com/graphql",
                                         data=json.dumps({"query": q, "variables": {"l": USER}}).encode(),
                                         headers={"Authorization": f"bearer {token}"})
            with urllib.request.urlopen(req, timeout=30) as r:
                n = json.load(r)["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
            DATA.mkdir(exist_ok=True)
            cache.write_text(json.dumps({"total": n, "updated": date.today().isoformat()}))
            return n
        except Exception as ex:
            print("contribution fetch failed:", ex)
    if cache.exists():
        return json.loads(cache.read_text())["total"]
    return None


# ═══════════════════════════════ SECTIONS ═══════════════════════════════

def hero(t):
    W, H = 880, 470
    s = SVG(W, H, f"Wajeeh Ul Hassan. {TAGLINE} Skills orbit: " +
            "; ".join(f"{r}: {', '.join(n)}" for r, n in ORBIT))
    s.css.append("@keyframes tw{0%,100%{opacity:.12}50%{opacity:1}}.tw{animation:tw 4s ease-in-out infinite}")
    s.add(card(0, 0, W, H, t["hero"], t["line"], 20))
    rnd = random.Random(11)
    for _ in range(50):
        x, y = rnd.uniform(14, W - 14), rnd.uniform(14, H - 14)
        r = 1.5 if rnd.random() < .2 else 1
        s.add(f'<circle class="tw" cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{t["star"]}" opacity="{t["starOp"]}" '
              f'style="animation-delay:-{rnd.uniform(0, 4):.1f}s;animation-duration:{rnd.uniform(2.5, 5.5):.1f}s"/>')

    s.text(44, 72, HANDLE, t["faint"], 13, "jb")
    s.text(42, 140, NAME[0], t["text"], 66, "sg", 700, ls=-1.4)
    s.text(42, 202, NAME[1], t["text"], 66, "sg", 700, ls=-1.4)
    y = 244
    for line in wrap(TAGLINE, 350, "sg", 400, 17):
        s.text(44, y, line, t["muted"], 17)
        y += 25
    py = y + 14
    pw = measure(STATUS, "jb", 400, 13) + 50
    s.add(f'<rect x="44.5" y="{py+.5}" width="{pw:.0f}" height="35" rx="17.5" fill="{t["okBg"]}" stroke="{t["okLine"]}"/>')
    s.add(pulse_dot(64, py + 18, t["ok"]))
    s.text(78, py + 22.5, STATUS, t["okText"], 13, "jb")
    lx = 44
    for ring, label in (("genai", "genai"), ("ml", "ml · dl"), ("ops", "mlops")):
        s.add(f'<circle cx="{lx+4}" cy="{py+66}" r="4" fill="{t[ring]}"/>')
        s.text(lx + 14, py + 70, label, t["muted"], 12, "jb")
        lx += measure(label, "jb", 400, 12) + 36

    cx, cy, k = 600, 238, 0.52
    radii, durs = [80, 132, 184], [26, 40, 58]
    for (ring, _), r in zip(ORBIT, radii):
        s.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r*k:.1f}" fill="none" stroke="{t[ring]}" '
              f'stroke-dasharray="4 5" opacity=".55"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="48" fill="{t["sun"]}" opacity=".16"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="34" fill="{t["sun"]}"/>')
    s.text(cx, cy + 7.5, "WH", t["sunInk"], 21, "sg", 700, "middle")
    for ri, ((ring, names), r, dur) in enumerate(zip(ORBIT, radii, durs)):
        path = f"M{cx+r},{cy} A{r},{r*k:.1f} 0 1,1 {cx-r},{cy} A{r},{r*k:.1f} 0 1,1 {cx+r},{cy}"
        for i, name in enumerate(names):
            lw = measure(name, "jb", 400, 11.5) + 16
            g = (f'<circle r="7" fill="{t[ring]}" stroke="{t["hero"]}" stroke-width="4"/>'
                 f'<rect x="12" y="-11" width="{lw:.0f}" height="22" rx="6" fill="{t["chip"]}" stroke="{t["line"]}"/>')
            s.add(f"<g>{g}")
            s.text(20, 4, name, t["text"], 11.5, "jb")
            s.add(f'<animateMotion dur="{dur}s" begin="-{(dur*i/len(names) + dur*0.37*ri) % dur:.1f}s" repeatCount="indefinite" '
                  f'path="{path}"/></g>')
    return s.render()


def facts(t):
    W, H = 880, 90
    s = SVG(W, H, ". ".join(f"{a}: {b}" for a, b in FACTS))
    w = (W - 32) / 3
    for i, (label, value) in enumerate(FACTS):
        x = i * (w + 16)
        s.add(card(x, 0, w, H, t["surface"], t["line"], 14))
        s.text(x + 20, 34, label, t["faint"], 13)
        s.text(x + 20, 62, value, t["text"], 17, w=500)
    return s.render()


def pipeline(t, total):
    W = 880
    sh, sy = 180, 64
    log_y = sy + sh + 52
    log_h = 26 * (len(LOG) + 1) + 26
    H = log_y + log_h + 28
    s = SVG(W, H, "Career pipeline: " + "; ".join(f"{a} {b}, {c} ({d})" for a, b, c, d in STAGES))
    s.add(card(0, 0, W, H, t["surface"], t["line"], 18))
    passed = sum(1 for _, _, ok, _ in LOG if ok)
    meta = "run_id 2026-wuh" + (f"  ·  {total:,} contributions this year" if total else "")
    s.text(28, 40, meta, t["faint"], 12, "jb")
    s.text(W - 28, 40, f"{passed} of {len(STAGES)} stages passed", t["faint"], 12, "jb", anchor="end")
    n = len(STAGES)
    gap = 12
    w = (W - 56 - gap * (n - 1)) / n
    for i, (stage, title, sub, when) in enumerate(STAGES):
        x = 28 + i * (w + gap)
        last = i == n - 1
        s.add(card(x, sy, w, sh, t["chip"] if last else t["log"], t["genai"] if last else t["line"], 14, last))
        s.text(x + 16, sy + 28, f"{i+1:02d} · {stage}", t["genai"] if last else t["faint"], 12, "jb")
        if last:
            s.add(f'<circle cx="{x+w-22:.1f}" cy="{sy+24}" r="6" fill="none" stroke="{t["genai"]}" stroke-width="2"/>')
            s.add(pulse_dot(round(x + w - 22, 1), sy + 24, t["genai"], 3))
        else:
            s.add(f'<circle cx="{x+w-22:.1f}" cy="{sy+24}" r="9" fill="{t["ok"]}"/>'
                  f'<path d="M{x+w-26:.1f} {sy+24.5} l2.8 2.8 l5.2 -5.6" fill="none" stroke="{t["okInk"]}" '
                  f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
        ty = sy + 62
        for line in wrap(title, w - 32, "sg", 700, 18):
            s.text(x + 16, ty, line, t["text"], 18, w=700)
            ty += 22
        ty += 4
        for line in wrap(sub, w - 32, "sg", 400, 13):
            s.text(x + 16, ty, line, t["muted"], 13)
            ty += 18
        s.text(x + 16, sy + sh - 18, when, t["faint"], 12, "jb")
    py = sy + sh + 24
    s.add(f'<rect x="28" y="{py}" width="{W-56}" height="6" rx="3" fill="{t["track"]}"/>')
    target = (W - 56) * (passed / n + 0.01)
    s.add(f'<rect x="28" y="{py}" width="0" height="6" rx="3" fill="{t["ok"]}">'
          f'<animate attributeName="width" values="0;{target:.0f};{target:.0f}" keyTimes="0;.7;1" '
          f'dur="4.5s" repeatCount="indefinite"/></rect>')
    s.add(card(28, log_y, W - 56, log_h, t["log"], t["line"], 12))
    cols = [48, 112, 208, 232]
    for i, (when, stage, ok, text) in enumerate(LOG):
        y = log_y + 34 + i * 26
        s.text(cols[0], y, f"[{when}]", t["faint"], 12.5, "jb")
        s.text(cols[1], y, stage, t["ml"] if ok else t["genai"], 12.5, "jb")
        s.text(cols[2], y, "✓" if ok else "…", t["ok"] if ok else t["genai"], 12.5, "jb")
        s.text(cols[3], y, text, t["text"], 12.5, "jb")
    cy = log_y + 34 + len(LOG) * 26 - 13
    s.add(f'<rect x="{cols[3]}" y="{cy}" width="8" height="16" fill="{t["accent"]}">'
          f'<animate attributeName="opacity" values="1;0;1" dur="1.1s" calcMode="discrete" repeatCount="indefinite"/></rect>')
    return s.render()


def metrics(t):
    W, H = 880, 132
    s = SVG(W, H, ". ".join(f"{v} {l}" for v, l, _ in METRICS))
    w = (W - 42) / 4
    for i, (value, label, col) in enumerate(METRICS):
        x = i * (w + 14)
        s.add(card(x, 0, w, H, t["surface"], t["line"], 16))
        s.text(x + 20, 58, value, t[col], 40, w=700, ls=-0.8)
        y = 88
        for line in wrap(label, w - 40, "sg", 400, 14)[:2]:
            s.text(x + 20, y, line, t["muted"], 14)
            y += 20
    return s.render()


def project(t, typ, title, chip, featured, desc, stack, linked):
    W, H = 432, 252
    s = SVG(W, H, f"{title}: {desc} Built with {', '.join(stack)}.")
    s.add(card(0, 0, W, H, t["surface"], t["sun"] if featured else t["line"], 16))
    s.text(24, 38, f"artifact / {typ}", t[TYPE_COLOR[typ]], 12, "jb")
    cw = measure(chip, "jb", 400, 11.5) + 20
    if featured:
        s.add(f'<rect x="{W-24-cw:.1f}" y="22" width="{cw:.1f}" height="24" rx="12" fill="{t["sun"]}"/>')
        s.text(W - 24 - cw / 2, 38, chip, t["sunInk"], 11.5, "jb", anchor="middle")
    else:
        s.add(f'<rect x="{W-24-cw+.5:.1f}" y="22.5" width="{cw-1:.1f}" height="23" rx="11.5" fill="none" stroke="{t["line2"]}"/>')
        s.text(W - 24 - cw / 2, 38, chip, t["muted"], 11.5, "jb", anchor="middle")
    s.text(24, 78, title, t["text"], 22, w=700, ls=-0.2)
    y = 106
    for line in wrap(desc, W - 48, "sg", 400, 14.5)[:3]:
        s.text(24, y, line, t["muted"], 14.5)
        y += 22
    x = 24
    for tag in stack:
        tw = measure(tag, "jb", 400, 11.5) + 18
        s.add(f'<rect x="{x}" y="180" width="{tw:.1f}" height="24" rx="6" fill="{t["chip"]}"/>')
        s.text(x + 9, 196, tag, t["muted"], 11.5, "jb")
        x += tw + 6
    link = "View repo" if linked else "Repo coming soon"
    s.text(24, 233, link, t["accent"], 13.5, w=500)
    lx = 24 + measure(link, "sg", 500, 13.5) + 6
    if linked:
        s.add(f'<path d="M{lx:.1f} {233-1} l7 -7 M{lx+1.5:.1f} {226} h5.5 v5.5" fill="none" stroke="{t["accent"]}" '
              f'stroke-width="1.6" stroke-linecap="round"/>')
    return s.render()


def endpoint(t, method, route, value, hot):
    W, H = 212, 96
    s = SVG(W, H, f"{method} {route}: {value}")
    s.add(card(0, 0, W, H, t["surface"], t["sun"] if hot else t["line"], 14))
    mw = measure(method, "jb", 500, 11) + 16
    s.add(f'<rect x="18" y="16" width="{mw:.1f}" height="22" rx="5" fill="{t["sun"] if hot else t["chip"]}"/>')
    s.text(26, 31, method, t["sunInk"] if hot else t["ml"], 11, "jb", 500)
    s.text(18, 60, route, t["faint"], 12.5, "jb")
    size = 15 if measure(value, "sg", 500, 15) < W - 36 else 13.5
    s.text(18, 82, value, t["text"], size, w=500)
    return s.render()


def extras(t):
    W = 880
    w = (W - 16) / 2
    H = 236
    s = SVG(W, H, "Certifications: " + ", ".join(CERTS) + ". Currently learning: " + ", ".join(LEARNING) + ". " + FUN_FACT)
    s.add(card(0, 0, w, H, t["surface"], t["line"], 16))
    s.text(24, 40, "$", t["accent"], 14, "jb", 500)
    s.text(40, 40, "pip list --certified", t["text"], 14, "jb", 500)
    for i, c in enumerate(CERTS):
        s.text(24, 76 + i * 25, c, t["muted"], 12.5, "jb")
    x0 = w + 16
    s.add(card(x0, 0, w, H, t["surface"], t["line"], 16))
    s.text(x0 + 24, 40, "$", t["accent"], 14, "jb", 500)
    s.text(x0 + 40, 40, "cat currently_learning.txt", t["text"], 14, "jb", 500)
    x, y = x0 + 24, 60
    for item in LEARNING:
        iw = measure(item, "sg", 400, 14) + 24
        if x + iw > x0 + w - 24:
            x, y = x0 + 24, y + 42
        s.add(f'<rect x="{x+.5:.1f}" y="{y+.5}" width="{iw-1:.1f}" height="33" rx="8" fill="none" '
              f'stroke="{t["line2"]}" stroke-dasharray="4 3"/>')
        s.text(x + 12, y + 22, item, t["text"], 14)
        x += iw + 8
    y += 64
    for line in wrap(FUN_FACT, w - 48, "sg", 400, 14):
        s.text(x0 + 24, y, line, t["muted"], 14)
        y += 21
    return s.render()


def main():
    ASSETS.mkdir(exist_ok=True)
    total = contributions()
    for name, t in THEMES.items():
        out = {f"hero-{name}.svg": hero(t), f"facts-{name}.svg": facts(t),
               f"pipeline-{name}.svg": pipeline(t, total), f"metrics-{name}.svg": metrics(t),
               f"extras-{name}.svg": extras(t)}
        for slug, typ, title, chip, feat, desc, stack in PROJECTS:
            out[f"project-{slug}-{name}.svg"] = project(t, typ, title, chip, feat, desc, stack,
                                                         slug not in ("tryon", "insurance"))
        for slug, method, route, value, hot in ENDPOINTS:
            out[f"endpoint-{slug}-{name}.svg"] = endpoint(t, method, route, value, hot)
        for fn, svg in out.items():
            (ASSETS / fn).write_text(svg, encoding="utf-8")
    print(f"built {len(out) * 2} SVGs (contributions: {total if total is not None else 'n/a'})")


if __name__ == "__main__":
    main()
