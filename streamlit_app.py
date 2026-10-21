import streamlit as st
import re
import math
import io
from engine.transformer import TextTransformer
from engine.perplexity import compute_perplexity_score
from engine.unicode_purge import purge_zero_width
from engine.docx_processor import read_docx, write_docx

st.set_page_config(
    page_title="TURNITOUT.EXE — Alex's AI Humanizer",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# RETRO 90s CSS — Windows 95 Design System
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');

/* ---- GLOBAL RESET ---- */
*, *::before, *::after {
    border-radius: 0 !important;
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}

.stApp {
    background-color: #c0c0c0 !important;
}

/* ---- SIDEBAR ---- */
[data-testid="stSidebar"] {
    background-color: #c0c0c0 !important;
    border-right: 2px solid #808080 !important;
}
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3,
[data-testid="stSidebar"] .stMarkdown h5 {
    font-family: "Arial Black", Impact, sans-serif !important;
    color: #000080 !important;
    text-transform: uppercase;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown span {
    color: #000 !important;
}

/* ---- BUTTONS — beveled outset ---- */
.stButton > button {
    background-color: #c0c0c0 !important;
    color: #000 !important;
    border: 2px solid !important;
    border-color: #dfdfdf #404040 #404040 #dfdfdf !important;
    box-shadow: 1px 1px 0 #000 !important;
    font-weight: bold !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px;
    padding: 8px 20px !important;
    transition: none !important;
}
.stButton > button:hover {
    background-color: #d4d4d4 !important;
    color: #000 !important;
}
.stButton > button:active {
    border-color: #404040 #dfdfdf #dfdfdf #404040 !important;
    box-shadow: none !important;
    transform: translate(1px, 1px);
}
/* Primary buttons */
.stButton > button[kind="primary"] {
    background-color: #c0c0c0 !important;
    color: #000 !important;
    border: 2px solid !important;
    border-color: #dfdfdf #404040 #404040 #dfdfdf !important;
    box-shadow: 1px 1px 0 #000 !important;
    font-size: 15px !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #d4d4d4 !important;
    color: #000 !important;
}
.stButton > button[kind="primary"]:active {
    border-color: #404040 #dfdfdf #dfdfdf #404040 !important;
    box-shadow: none !important;
    transform: translate(1px, 1px);
}

/* ---- TEXT AREAS — inset sunken ---- */
.stTextArea textarea {
    background-color: #fff !important;
    color: #000 !important;
    border: 2px solid !important;
    border-color: #808080 #dfdfdf #dfdfdf #808080 !important;
    box-shadow: inset 1px 1px 2px rgba(0,0,0,0.15) !important;
    font-family: "Segoe UI", Tahoma, sans-serif !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
}

/* ---- SLIDERS ---- */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background-color: #c0c0c0 !important;
    border: 2px solid !important;
    border-color: #fff #808080 #808080 #fff !important;
}

/* ---- RADIO ---- */
.stRadio > div > label {
    color: #000 !important;
    font-weight: 600 !important;
}

/* ---- EXPANDER ---- */
.streamlit-expanderHeader {
    background-color: #c0c0c0 !important;
    border: 2px solid !important;
    border-color: #fff #808080 #808080 #fff !important;
    color: #000 !important;
    font-weight: bold !important;
}

/* ============================================================
   CUSTOM COMPONENT CLASSES
   ============================================================ */

/* Windows 95 Title Bar */
.win95-titlebar {
    background: linear-gradient(to right, #000080, #1084d0);
    color: #fff;
    font-family: "Segoe UI", Tahoma, sans-serif;
    font-weight: 800;
    font-size: 13px;
    padding: 5px 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: none;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.win95-titlebar .win-buttons {
    display: flex;
    gap: 2px;
}
.win95-titlebar .win-btn {
    width: 16px;
    height: 14px;
    background: #c0c0c0;
    border: 1px solid;
    border-color: #fff #808080 #808080 #fff;
    font-size: 9px;
    line-height: 12px;
    text-align: center;
    color: #000;
    font-family: "Courier New", monospace;
    font-weight: bold;
    cursor: default;
}

/* Windows 95 Window (titlebar + body) */
.win95-window {
    background-color: #c0c0c0;
    border: 2px solid;
    border-color: #dfdfdf #404040 #404040 #dfdfdf;
    box-shadow: 1px 1px 0 #000;
    margin-bottom: 14px;
}

/* Windows 95 Panel */
.win95-panel {
    background-color: #c0c0c0;
    border: 2px solid;
    border-color: #dfdfdf #404040 #404040 #dfdfdf;
    box-shadow: 1px 1px 0 #000;
    margin-bottom: 12px;
}
.win95-panel-content {
    background-color: #fff;
    border: 2px solid;
    border-color: #808080 #dfdfdf #dfdfdf #808080;
    margin: 3px;
    padding: 14px;
    min-height: 60px;
}
.win95-panel-content.yellow {
    background-color: #ffffee;
}

/* Marquee */
.retro-marquee {
    background: #c0c0c0;
    border: 2px solid;
    border-color: #808080 #fff #fff #808080;
    box-shadow: inset 1px 1px 0 #404040;
    overflow: hidden;
    padding: 5px 0;
    margin-bottom: 16px;
}
.retro-marquee-inner {
    display: inline-block;
    white-space: nowrap;
    animation: scroll-left 35s linear infinite;
    font-family: "VT323", "Courier New", monospace;
    font-size: 15px;
    letter-spacing: 1px;
}
@keyframes scroll-left {
    0% { transform: translateX(100vw); }
    100% { transform: translateX(-100%); }
}

/* Rainbow Text */
@keyframes rainbow {
    0% { color: #ff0000; }
    17% { color: #ff8000; }
    33% { color: #ffff00; }
    50% { color: #00ff00; }
    67% { color: #0080ff; }
    83% { color: #8000ff; }
    100% { color: #ff0000; }
}
.rainbow-text {
    animation: rainbow 4s linear infinite;
    font-family: "Arial Black", Impact, sans-serif;
    font-weight: 900;
    font-size: 28px;
    text-transform: uppercase;
}

/* Blinking NEW badge */
@keyframes blink-badge {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}
.blink-new {
    display: inline-block;
    background: #ff0000;
    color: #ffff00;
    font-family: "Arial Black", Impact, sans-serif;
    font-size: 10px;
    font-weight: 900;
    padding: 1px 6px;
    border: 1px solid #800000;
    animation: blink-badge 1s step-end infinite;
    vertical-align: super;
    margin-left: 4px;
}

/* Pulse Glow */
@keyframes pulse-glow {
    0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255,0,0,0.7); }
    50% { transform: scale(1.03); box-shadow: 0 0 8px 2px rgba(255,0,0,0.4); }
}

/* Hit Counter */
.hit-counter {
    display: inline-flex;
    align-items: center;
    gap: 16px;
    background: #c0c0c0;
    border: 2px solid;
    border-color: #fff #808080 #808080 #fff;
    box-shadow: inset -1px -1px 0 #404040, inset 1px 1px 0 #dfdfdf;
    padding: 10px 20px;
    font-family: "Courier New", monospace;
    font-size: 16px;
    letter-spacing: 1px;
}
.hit-counter .label {
    color: #808080;
    font-size: 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
    font-weight: bold;
}
.hit-counter .value {
    color: #000080;
    font-weight: bold;
    font-size: 18px;
    background: #fff;
    border: 1px solid;
    border-color: #808080 #fff #fff #808080;
    padding: 2px 8px;
    display: inline-block;
    min-width: 50px;
    text-align: center;
}
.hit-counter .value.red { color: #cc0000; }
.hit-counter .value.yellow { color: #996600; }
.hit-counter .value.cyan { color: #006699; }

/* Groove HR */
.groove-hr {
    border: none;
    height: 4px;
    background: linear-gradient(to bottom, #808080 0%, #808080 50%, #fff 50%, #fff 100%);
    margin: 16px 0;
}

/* Status Bar Footer */
.status-bar {
    background: #c0c0c0;
    border: 2px solid;
    border-color: #dfdfdf #404040 #404040 #dfdfdf;
    padding: 6px 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: "Segoe UI", Tahoma, sans-serif;
    font-size: 12px;
    color: #000;
    margin-top: 20px;
}
.status-bar .status-section {
    border: 1px solid;
    border-color: #808080 #dfdfdf #dfdfdf #808080;
    padding: 2px 10px;
    background: #c0c0c0;
}
.status-bar .status-section b {
    color: #000080;
}

/* Donut Chart Container */
.donut-container {
    text-align: center;
    padding: 12px;
}
.donut-container svg { margin: 0 auto; display: block; }

/* Score pills */
.score-pills {
    display: flex;
    gap: 10px;
    justify-content: center;
    margin: 12px 0 4px 0;
    flex-wrap: wrap;
}
.score-pill {
    padding: 5px 16px;
    border: 2px solid;
    border-color: #dfdfdf #404040 #404040 #dfdfdf;
    font-family: "Segoe UI", Tahoma, sans-serif;
    font-weight: 700;
    font-size: 13px;
}
.score-pill.ai {
    background: #c0c0c0;
    color: #cc0000;
}
.score-pill.mixed {
    background: #c0c0c0;
    color: #808000;
}
.score-pill.human {
    background: #c0c0c0;
    color: #006600;
}

/* Sentence highlight rows */
.sent-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 6px 8px;
    margin: 2px 0;
    font-size: 13px;
    line-height: 1.5;
    border-bottom: 1px solid #e0e0e0;
}
.sent-row:nth-child(odd) { background: #fff; }
.sent-row:nth-child(even) { background: #e8e8e8; }
.sent-badge {
    flex-shrink: 0;
    min-width: 42px;
    text-align: center;
    padding: 2px 6px;
    font-family: "Courier New", monospace;
    font-weight: bold;
    font-size: 11px;
    border: 1px solid;
}
.sent-badge.ai { background: #ff0000; color: #fff; border-color: #800000; }
.sent-badge.mixed { background: #ffff00; color: #000; border-color: #808000; }
.sent-badge.human { background: #00aa00; color: #fff; border-color: #006600; }
.sent-text { flex: 1; color: #000; font-family: "Segoe UI", Tahoma, sans-serif; }

/* Highlighted text panel */
.highlighted-text {
    font-family: "Segoe UI", Tahoma, sans-serif;
    font-size: 14px;
    line-height: 1.8;
    color: #000;
}
.hl-ai { background: #ffcccc; padding: 1px 0; border-bottom: 2px solid #ff0000; }
.hl-mixed { background: #ffffcc; padding: 1px 0; border-bottom: 2px solid #cccc00; }
.hl-human { background: #ccffcc; padding: 1px 0; }
.hl-none { padding: 1px 0; }

/* Footer */
.retro-footer {
    text-align: center;
    padding: 20px 0 8px 0;
    font-family: "Courier New", monospace;
    font-size: 12px;
    color: #808080;
}
.retro-footer a { color: #0000ff; text-decoration: underline; }
.retro-footer a:hover { color: #ff0000; }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
    .rainbow-text { animation: none; color: #ff0000; }
    .blink-new { animation: none; }
    .retro-marquee-inner { animation: none; }
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPERS
# ============================================================

def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]


def score_sentence(sentence):
    if len(sentence) < 25:
        return 50.0
    return compute_perplexity_score(sentence)["combined_score"]


def html_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_donut_svg(ai_pct, human_pct, size=180):
    r = 65
    cx, cy = size // 2, size // 2
    circ = 2 * math.pi * r
    ai_len = (ai_pct / 100) * circ
    human_len = (human_pct / 100) * circ

    ai_color = "#ff0000"
    human_color = "#00aa00"
    if ai_pct < 30:
        verdict_text = "LIKELY HUMAN"
        verdict_color = "#00aa00"
    elif ai_pct < 60:
        verdict_text = "MIXED"
        verdict_color = "#808000"
    else:
        verdict_text = "AI DETECTED"
        verdict_color = "#ff0000"

    svg = f'''
    <svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" style="margin:0 auto;display:block;">
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#e0e0e0" stroke-width="22"/>
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
        stroke="{ai_color}" stroke-width="22"
        stroke-dasharray="{ai_len:.1f} {circ - ai_len:.1f}"
        transform="rotate(-90 {cx} {cy})"/>
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
        stroke="{human_color}" stroke-width="22"
        stroke-dasharray="{human_len:.1f} {circ - human_len:.1f}"
        stroke-dashoffset="{-ai_len:.1f}"
        transform="rotate(-90 {cx} {cy})"/>
      <text x="{cx}" y="{cy - 8}" text-anchor="middle"
        font-family="Arial Black, Impact, sans-serif" font-size="30" font-weight="900"
        fill="{verdict_color}">{ai_pct:.0f}%</text>
      <text x="{cx}" y="{cy + 14}" text-anchor="middle"
        font-family="Courier New, monospace" font-size="11" fill="#808080"
        font-weight="bold">{verdict_text}</text>
      <!-- Legend -->
      <rect x="10" y="{size - 22}" width="10" height="10" fill="{ai_color}"/>
      <text x="24" y="{size - 13}" font-family="Courier New" font-size="10" fill="#000">AI {ai_pct:.0f}%</text>
      <rect x="{size - 80}" y="{size - 22}" width="10" height="10" fill="{human_color}"/>
      <text x="{size - 66}" y="{size - 13}" font-family="Courier New" font-size="10" fill="#000">Human {human_pct:.0f}%</text>
    </svg>'''
    return svg


def render_highlighted_html(text):
    sentences = split_sentences(text)
    if not sentences:
        return html_escape(text)
    parts = []
    for s in sentences:
        sc = score_sentence(s)
        escaped = html_escape(s)
        if sc < 30:
            parts.append(f'<span class="hl-ai">{escaped}</span>')
        elif sc < 55:
            parts.append(f'<span class="hl-mixed">{escaped}</span>')
        else:
            parts.append(f'<span class="hl-human">{escaped}</span>')
    return " ".join(parts)


def render_sentence_list(text):
    sentences = split_sentences(text)
    if not sentences:
        return ""
    rows = []
    for s in sentences:
        sc = score_sentence(s)
        escaped = html_escape(s)
        if sc < 30:
            badge_class = "ai"
            badge_label = "AI"
        elif sc < 55:
            badge_class = "mixed"
            badge_label = "MIX"
        else:
            badge_class = "human"
            badge_label = "OK"
        rows.append(
            f'<div class="sent-row">'
            f'<span class="sent-badge {badge_class}">{badge_label}</span>'
            f'<span class="sent-text">{escaped}</span>'
            f'</div>'
        )
    return "".join(rows)


# ============================================================
# SESSION STATE
# ============================================================
for key, default in [
    ("result", None), ("stats", None), ("input_text", ""),
    ("ai_pct", 0), ("human_pct", 0),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
    <div class="win95-titlebar" style="margin-bottom:12px;">
        <span>TURNITOUT.EXE</span>
        <div class="win-buttons">
            <span class="win-btn">_</span>
            <span class="win-btn">□</span>
            <span class="win-btn">X</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("##### CONTROLS")

    mode = st.radio("MODE", ["Humanizer", "Scanner", "Document"], index=0)

    st.markdown('<div class="groove-hr"></div>', unsafe_allow_html=True)

    aggressiveness = st.slider("REWRITE INTENSITY", 0.1, 1.0, 0.55, 0.05)

    purge_unicode = st.checkbox("PURGE ZERO-WIDTH UNICODE", value=True)

    seed = st.number_input("SEED (0=RANDOM)", 0, 999999, 0)

    st.markdown('<div class="groove-hr"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="text-align:center;font-family:Courier New,monospace;'
        'font-size:11px;color:#808080;">'
        'OPERATOR: <b style="color:#000080;">ALEX SHIBU</b><br>'
        'ENGINE v2.0 // ZERO AI APIS'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div class="win95-titlebar" style="font-size:16px;padding:6px 12px;margin-bottom:0;">
    <span>🖥️ TURNITOUT — AI TEXT HUMANIZER</span>
    <div class="win-buttons">
        <span class="win-btn">_</span>
        <span class="win-btn">□</span>
        <span class="win-btn">X</span>
    </div>
</div>
<div class="retro-marquee">
    <div class="retro-marquee-inner">
        <span style="color:#000080;">★ TURNITOUT ★</span>
        &nbsp;&nbsp;—&nbsp;&nbsp;
        <span style="color:#006600;">"Education is the kindling of a flame, not the filling of a vessel." — Socrates (who never had to cite his sources)</span>
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        <span style="color:#800000;">"The only thing I know is that I know nothing." — Also Socrates (still got tenure)</span>
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        <span style="color:#800080;">"Tell me and I forget. Teach me and I remember. Involve me and I learn." — Ben Franklin (who definitely plagiarized that from a fortune cookie)</span>
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        <span style="color:#cc6600;">"The mind is not a vessel to be filled but a fire to be kindled." — Plutarch (who recycled Socrates and got away with it)</span>
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        <span style="color:#006699;">"An investment in knowledge pays the best interest." — Ben Franklin (ironic, from a guy who flew a kite in a storm)</span>
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        <span style="color:#000080;">BUILT BY ALEX SHIBU — ZERO AI — 1012+ RULES — BYPASS TURNITIN • GPTZERO • COPYLEAKS</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# MAIN CONTENT
# ============================================================

def run_transform(text, aggressiveness, purge_unicode, seed):
    actual_seed = seed if seed != 0 else None
    transformer = TextTransformer(aggressiveness=aggressiveness, seed=actual_seed)
    if purge_unicode:
        text, zw_count = purge_zero_width(text)
    else:
        zw_count = 0
    result = transformer.transform(text)
    after = compute_perplexity_score(result)
    stats = transformer.stats
    if zw_count > 0:
        stats["zero_width_removed"] = zw_count
    human_score = after["combined_score"]
    ai_score = max(0, 100 - human_score)
    return result, stats, ai_score, human_score


# ---- HUMANIZER MODE ----
if mode == "Humanizer":
    col_input, col_score = st.columns([3, 2])

    with col_input:
        st.markdown("""
        <div class="win95-titlebar">
            <span>📝 INPUT TEXT</span>
            <div class="win-buttons">
                <span class="win-btn">_</span>
                <span class="win-btn">□</span>
                <span class="win-btn">X</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        input_text = st.text_area(
            "input_text_area",
            height=280,
            placeholder="Paste your AI-generated text here...",
            label_visibility="collapsed",
        )
        humanize_clicked = st.button(
            "⚡ HUMANIZE THIS TEXT ⚡",
            type="primary",
            use_container_width=True,
        )

    if humanize_clicked and input_text.strip():
        with st.spinner("PROCESSING..."):
            result, stats, ai_pct, human_pct = run_transform(
                input_text, aggressiveness, purge_unicode, seed
            )
        st.session_state.result = result
        st.session_state.stats = stats
        st.session_state.input_text = input_text
        st.session_state.ai_pct = ai_pct
        st.session_state.human_pct = human_pct

    with col_score:
        st.markdown("""
        <div class="win95-titlebar">
            <span>📊 AI DETECTION SCORE</span>
            <div class="win-buttons">
                <span class="win-btn">_</span>
                <span class="win-btn">□</span>
                <span class="win-btn">X</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.result:
            ai = st.session_state.ai_pct
            human = st.session_state.human_pct
            st.markdown(
                f'<div class="win95-panel"><div class="win95-panel-content" '
                f'style="text-align:center;padding:16px;">'
                f'{render_donut_svg(ai, human)}'
                f'<div class="score-pills">'
                f'<span class="score-pill ai">AI {ai:.0f}%</span>'
                f'<span class="score-pill human">HUMAN {human:.0f}%</span>'
                f'</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="win95-panel"><div class="win95-panel-content yellow" '
                'style="text-align:center;padding:40px 16px;color:#808080;'
                'font-family:Courier New,monospace;">'
                'AWAITING INPUT...<br><br>'
                '<span style="font-size:11px;">Paste text and click HUMANIZE</span>'
                '</div></div>',
                unsafe_allow_html=True,
            )

    # ---- RESULTS SECTION ----
    if st.session_state.result:
        st.markdown('<div class="groove-hr"></div>', unsafe_allow_html=True)

        # Original text with sentence highlighting
        st.markdown("""
        <div class="win95-titlebar">
            <span>🔍 ORIGINAL — SENTENCE ANALYSIS</span>
            <div class="win-buttons">
                <span class="win-btn">_</span>
                <span class="win-btn">□</span>
                <span class="win-btn">X</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(
            f'<div class="win95-panel"><div class="win95-panel-content">'
            f'<div class="highlighted-text">{render_highlighted_html(st.session_state.input_text)}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # Sentence list
        with st.expander("VIEW ALL SENTENCES WITH SCORES"):
            st.markdown(render_sentence_list(st.session_state.input_text), unsafe_allow_html=True)

        st.markdown('<div class="groove-hr"></div>', unsafe_allow_html=True)

        # Humanized output
        st.markdown("""
        <div class="win95-titlebar" style="background:linear-gradient(to right,#006600,#00aa00);">
            <span>✅ HUMANIZED OUTPUT</span>
            <div class="win-buttons">
                <span class="win-btn">_</span>
                <span class="win-btn">□</span>
                <span class="win-btn">X</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.text_area(
            "output_display",
            st.session_state.result,
            height=250,
            label_visibility="collapsed",
        )

        # Stats hit counter
        stats = st.session_state.stats
        total = stats.get("total", 0)
        phrases = stats.get("phrases_replaced", 0)
        synonyms = stats.get("synonyms_replaced", 0)
        discourse = stats.get("discourse_rotated", 0)
        other = total - phrases - synonyms - discourse
        st.markdown(
            f'<div style="text-align:center;margin:12px 0;">'
            f'<div class="hit-counter">'
            f'<span><span class="label">TRANSFORMS</span><br><span class="value">{total:05d}</span></span>'
            f'<span><span class="label">PHRASES</span><br><span class="value yellow">{phrases:04d}</span></span>'
            f'<span><span class="label">SYNONYMS</span><br><span class="value cyan">{synonyms:04d}</span></span>'
            f'<span><span class="label">DISCOURSE</span><br><span class="value">{discourse:04d}</span></span>'
            f'<span><span class="label">OTHER</span><br><span class="value red">{other:04d}</span></span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )


# ---- SCANNER MODE ----
elif mode == "Scanner":
    st.markdown("""
    <div class="win95-titlebar">
        <span>🔍 SENTENCE SCANNER — AI DETECTION ANALYSIS</span>
    </div>
    """, unsafe_allow_html=True)

    scan_text = st.text_area(
        "scan_input",
        height=220,
        placeholder="Paste text to scan for AI patterns...",
        label_visibility="collapsed",
    )

    if st.button("SCAN TEXT", type="primary", use_container_width=True):
        if not scan_text.strip():
            st.warning("Paste some text first.")
        else:
            overall = compute_perplexity_score(scan_text)
            human_sc = overall["combined_score"]
            ai_sc = max(0, 100 - human_sc)

            col_chart, col_detail = st.columns([2, 3])

            with col_chart:
                st.markdown(
                    f'<div class="win95-panel"><div class="win95-panel-content" '
                    f'style="text-align:center;padding:16px;">'
                    f'{render_donut_svg(ai_sc, human_sc)}'
                    f'<div class="score-pills">'
                    f'<span class="score-pill ai">AI {ai_sc:.0f}%</span>'
                    f'<span class="score-pill mixed">MIXED 0%</span>'
                    f'<span class="score-pill human">HUMAN {human_sc:.0f}%</span>'
                    f'</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

            with col_detail:
                st.markdown("""
                <div class="win95-titlebar">
                    <span>SENTENCE BREAKDOWN</span>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(
                    f'<div class="win95-panel"><div class="win95-panel-content" '
                    f'style="max-height:300px;overflow-y:auto;padding:4px;">'
                    f'{render_sentence_list(scan_text)}'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

            st.markdown('<div class="groove-hr"></div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="win95-titlebar">
                <span>HIGHLIGHTED TEXT</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(
                f'<div class="win95-panel"><div class="win95-panel-content">'
                f'<div class="highlighted-text">{render_highlighted_html(scan_text)}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )


# ---- DOCUMENT MODE ----
elif mode == "Document":
    st.markdown("""
    <div class="win95-titlebar">
        <span>📁 DOCUMENT PROCESSOR (.DOCX)</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(
        '<div class="win95-panel"><div class="win95-panel-content yellow">'
        'Upload a Word document. Formatting is preserved — only text content is transformed.'
        '</div></div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader("UPLOAD .DOCX", type=["docx"])

    if uploaded and st.button("PROCESS DOCUMENT", type="primary", use_container_width=True):
        file_bytes = uploaded.read()
        with st.spinner("PROCESSING DOCUMENT..."):
            paragraphs = read_docx(file_bytes)
            actual_seed = seed if seed != 0 else None
            transformer = TextTransformer(aggressiveness=aggressiveness, seed=actual_seed)
            transformed_texts = []
            full_after = []
            for para in paragraphs:
                text = para["text"]
                if not text.strip():
                    transformed_texts.append(text)
                    continue
                if purge_unicode:
                    text, _ = purge_zero_width(text)
                result = transformer.transform(text)
                transformed_texts.append(result)
                full_after.append(result)
            output_bytes = write_docx(file_bytes, transformed_texts)
            after_score = compute_perplexity_score("\n".join(full_after))["combined_score"] if full_after else 0

        ai_sc = max(0, 100 - after_score)
        st.markdown(
            f'<div style="text-align:center;margin:12px 0;">'
            f'<div class="hit-counter">'
            f'<span><span class="label">TRANSFORMS</span><br>'
            f'<span class="value">{transformer.stats.get("total", 0):05d}</span></span>'
            f'<span><span class="label">AI SCORE</span><br>'
            f'<span class="value red">{ai_sc:.0f}%</span></span>'
            f'<span><span class="label">HUMAN SCORE</span><br>'
            f'<span class="value">{after_score:.0f}%</span></span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        st.download_button(
            label="⬇ DOWNLOAD HUMANIZED DOCUMENT",
            data=output_bytes,
            file_name=f"humanized_{uploaded.name}",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )


# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div class="status-bar">
    <div class="status-section">Built by <b>Alex Shibu</b></div>
    <div class="status-section">Engine v2.0 — 11 Stages</div>
    <div class="status-section">1012+ Rules</div>
    <div class="status-section">Zero APIs — Zero Cost</div>
</div>
""", unsafe_allow_html=True)
