import streamlit as st
import re
import math
import io
import base64
import pathlib
from engine.transformer import TextTransformer
from engine.perplexity import compute_perplexity_score
from engine.unicode_purge import purge_zero_width
from engine.docx_processor import read_docx, write_docx

_BLISS_PATH = pathlib.Path(__file__).parent / "assets" / "bliss.jpg"
_BLISS_B64 = base64.b64encode(_BLISS_PATH.read_bytes()).decode()

st.set_page_config(
    page_title="TURNITOUT.EXE — Alex's AI Humanizer",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# RETRO 90s CSS — Windows 95 Design System
# ============================================================
_bliss_css = f"""
.stApp {{
    background-image: url('data:image/jpeg;base64,{_BLISS_B64}') !important;
    background-repeat: no-repeat !important;
    background-position: center center !important;
    background-attachment: fixed !important;
    background-size: cover !important;
    background-color: #3a7bd5 !important;
    min-height: 100vh;
}}
[data-testid="stAppViewContainer"] {{
    background: transparent !important;
}}
[data-testid="stMain"] {{
    background: transparent !important;
}}
"""

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');

/* ---- STREAMLIT CHROME — transparent, not hidden (sidebar toggle lives here) ---- */
[data-testid="stHeader"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stToolbar"] {
    background: transparent !important;
    border: none !important;
}
#MainMenu { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }

/* Sidebar toggle buttons — rainbow, big, always visible */
@keyframes hamburger-rainbow {
    0% { background-color: #ff0000; }
    16% { background-color: #ff8800; }
    33% { background-color: #ffff00; }
    50% { background-color: #00cc00; }
    66% { background-color: #0066ff; }
    83% { background-color: #8800ff; }
    100% { background-color: #ff0000; }
}
/* Force the toggle container always visible (Streamlit hides on no-hover) */
[data-testid="stSidebarCollapseButton"],
[data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"] {
    opacity: 1 !important;
    visibility: visible !important;
    display: flex !important;
    position: relative !important;
    z-index: 999999 !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"] button {
    animation: hamburger-rainbow 2s linear infinite !important;
    color: #fff !important;
    border: 3px solid #fff !important;
    width: 56px !important;
    height: 56px !important;
    min-width: 56px !important;
    min-height: 56px !important;
    padding: 12px !important;
    box-shadow: 2px 2px 0 #000, 0 0 10px rgba(0,0,0,0.3) !important;
    font-weight: 900 !important;
    opacity: 1 !important;
    visibility: visible !important;
}
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stExpandSidebarButton"] svg,
[data-testid="collapsedControl"] svg {
    color: #fff !important;
    width: 32px !important;
    height: 32px !important;
    filter: drop-shadow(1px 1px 2px rgba(0,0,0,0.5)) !important;
}

/* ---- GLOBAL RESET ---- */
*, *::before, *::after {
    border-radius: 0 !important;
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}

/* Main content block — frosted glass so Bliss shows through */
[data-testid="stMainBlockContainer"] {
    background: rgba(192, 192, 192, 0.55) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    border: 2px solid;
    border-color: #dfdfdf #808080 #808080 #dfdfdf;
    padding: 16px !important;
    padding-top: 0 !important;
    margin-top: 0;
    box-shadow: 2px 2px 8px rgba(0,0,0,0.2);
}
.stApp [data-testid="stAppViewBlockContainer"] {
    padding-top: 0 !important;
}
.block-container {
    padding-top: 0 !important;
}

/* ---- SIDEBAR ---- */
[data-testid="stSidebar"] {
    background: rgba(192, 192, 192, 0.75) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border-right: 2px solid;
    border-color: #dfdfdf #404040 #404040 #dfdfdf !important;
}
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3,
[data-testid="stSidebar"] .stMarkdown h5 {
    font-family: "Segoe UI", Tahoma, sans-serif !important;
    color: #000080 !important;
    text-transform: uppercase;
    font-weight: 800 !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown span {
    color: #000 !important;
}

/* Sidebar feature box */
.sidebar-feature-box {
    background: #ffff00;
    border: 2px solid;
    border-color: #dfdfdf #404040 #404040 #dfdfdf;
    padding: 10px 12px;
    margin: 10px 0;
    font-family: "Segoe UI", Tahoma, sans-serif;
    font-size: 13px;
    color: #000;
}
.sidebar-feature-box b {
    font-family: "Segoe UI", Tahoma, sans-serif;
    font-weight: 800;
    color: #000;
    font-size: 13px;
}
.sidebar-feature-box ul {
    margin: 6px 0 0 0;
    padding-left: 18px;
}
.sidebar-feature-box li {
    margin-bottom: 3px;
    font-size: 12px;
}

/* Sidebar info panel */
.sidebar-info {
    background: #fff;
    border: 2px solid;
    border-color: #808080 #dfdfdf #dfdfdf #808080;
    padding: 10px 12px;
    margin: 10px 0;
    font-family: "Segoe UI", Tahoma, sans-serif;
    font-size: 12px;
    color: #000;
    text-align: center;
}
.sidebar-info .operator-name {
    font-weight: 800;
    font-size: 14px;
    color: #000080;
    letter-spacing: 0.5px;
}
.sidebar-info .tagline {
    font-size: 11px;
    color: #808080;
    margin-top: 4px;
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
    text-shadow: 1px 1px 0 rgba(0,0,0,0.3);
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
    border-color: #dfdfdf #404040 #404040 #dfdfdf;
    box-shadow: 1px 1px 0 #000;
    overflow: hidden;
    padding: 8px 0;
    margin-bottom: 16px;
}
.retro-marquee-inner {
    display: inline-block;
    white-space: nowrap;
    animation: scroll-left 40s linear infinite, marquee-rainbow 3s linear infinite;
    font-family: "VT323", "Courier New", monospace;
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 2px;
    text-shadow: 1px 1px 0 rgba(0,0,0,0.15);
    background: linear-gradient(
        90deg,
        #ff0000, #ff4400, #ff8800, #ffcc00, #ffff00, #88ff00, #00ff00,
        #00ff88, #00ffff, #0088ff, #0044ff, #4400ff, #8800ff, #ff00ff, #ff0088,
        #ff0000, #ff4400, #ff8800, #ffcc00, #ffff00, #88ff00, #00ff00
    );
    background-size: 300% 100%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
@keyframes marquee-rainbow {
    0% { background-position: 0% 50%; }
    100% { background-position: 300% 50%; }
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

/* ---- SIDEBAR SPICE ---- */

/* Blinking online indicator */
@keyframes blink-online {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}
.online-indicator {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: "Courier New", monospace;
    font-size: 11px;
    font-weight: bold;
    color: #008000;
    padding: 4px 10px;
    background: #000;
    border: 1px solid;
    border-color: #808080 #dfdfdf #dfdfdf #808080;
    margin: 6px 0;
}
.online-dot {
    width: 8px;
    height: 8px;
    background: #00ff00;
    border-radius: 50% !important;
    animation: blink-online 1.5s ease-in-out infinite;
    box-shadow: 0 0 4px #00ff00;
}

/* Sidebar retro clock */
.retro-clock {
    font-family: "VT323", "Courier New", monospace;
    font-size: 24px;
    color: #00ff00;
    background: #0a1a0a;
    border: 2px solid;
    border-color: #808080 #dfdfdf #dfdfdf #808080;
    padding: 6px 14px;
    text-align: center;
    letter-spacing: 3px;
    text-shadow: 0 0 6px #00ff00;
    margin: 4px 0 2px 0;
}

/* Sidebar mini hit counter */
.mini-hit-counter {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: #c0c0c0;
    border: 2px solid;
    border-color: #808080 #dfdfdf #dfdfdf #808080;
    padding: 6px 12px;
    margin: 2px 0 8px 0;
    font-family: "Courier New", monospace;
    font-size: 12px;
    color: #000;
    font-weight: bold;
}
.mini-hit-counter .counter-digits {
    font-family: "VT323", "Courier New", monospace;
    font-size: 18px;
    color: #cc0000;
    letter-spacing: 2px;
    background: #fff;
    padding: 2px 8px;
    border: 2px solid;
    border-color: #808080 #dfdfdf #dfdfdf #808080;
}

/* Sidebar taskbar */
.sidebar-taskbar {
    background: #c0c0c0;
    border: 2px solid;
    border-color: #dfdfdf #404040 #404040 #dfdfdf;
    padding: 3px 6px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: "Segoe UI", Tahoma, sans-serif;
    font-size: 11px;
    color: #000;
    margin-top: 12px;
}
.taskbar-start {
    background: #c0c0c0;
    border: 2px solid;
    border-color: #dfdfdf #404040 #404040 #dfdfdf;
    padding: 2px 10px 2px 4px;
    font-weight: 800;
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
}
.taskbar-tray {
    border: 1px solid;
    border-color: #808080 #dfdfdf #dfdfdf #808080;
    padding: 2px 8px;
    font-family: "Courier New", monospace;
    font-size: 11px;
}

/* Tone preset buttons */
.preset-row {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
    margin: 6px 0 10px 0;
}
.preset-btn {
    background: #c0c0c0;
    border: 2px solid;
    border-color: #dfdfdf #404040 #404040 #dfdfdf;
    padding: 4px 10px;
    font-family: "Segoe UI", Tahoma, sans-serif;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    color: #000;
}
.preset-btn:hover {
    background: #d4d4d4;
}
.preset-btn.active {
    border-color: #404040 #dfdfdf #dfdfdf #404040;
    background: #a0a0a0;
}

/* Copy button */
.copy-btn-wrap {
    text-align: right;
    margin: -4px 0 8px 0;
}
.copy-btn-wrap button {
    background: #c0c0c0;
    border: 2px solid;
    border-color: #dfdfdf #404040 #404040 #dfdfdf;
    padding: 6px 18px;
    font-family: "Segoe UI", Tahoma, sans-serif;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    color: #000;
    text-transform: uppercase;
}
.copy-btn-wrap button:active {
    border-color: #404040 #dfdfdf #dfdfdf #404040;
}

/* Before/After comparison */
.ba-compare {
    display: flex;
    gap: 16px;
    justify-content: center;
    align-items: flex-start;
    flex-wrap: wrap;
}
.ba-card {
    flex: 1;
    min-width: 180px;
    max-width: 260px;
    text-align: center;
}
.ba-label {
    font-family: "Segoe UI", Tahoma, sans-serif;
    font-weight: 800;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
    padding: 4px 0;
}
.ba-label.before { color: #cc0000; background: #ffcccc; border: 1px solid #cc0000; }
.ba-label.after { color: #006600; background: #ccffcc; border: 1px solid #006600; }
.ba-arrow {
    font-size: 36px;
    color: #000080;
    align-self: center;
    font-weight: 900;
    padding-top: 30px;
}

/* ---- MOBILE RESPONSIVE (≤768px) ---- */
@media screen and (max-width: 768px) {
    /* Full-bleed container */
    [data-testid="stMainBlockContainer"] {
        padding: 10px !important;
        margin: 0 !important;
        border: none !important;
        box-shadow: none !important;
        background: rgba(192, 192, 192, 0.75) !important;
        max-width: 100% !important;
    }
    .block-container {
        padding-left: 6px !important;
        padding-right: 6px !important;
        max-width: 100% !important;
    }
    /* Hide Streamlit toolbar icons on mobile */
    [data-testid="stToolbar"] { display: none !important; }

    /* Title bar — bigger text */
    .win95-titlebar { font-size: 15px !important; padding: 10px 12px !important; }
    .win95-titlebar span { font-size: 15px !important; }
    .win95-titlebar .win-buttons { display: none !important; }

    /* Marquee */
    .retro-marquee { padding: 6px 0; margin-bottom: 10px; }
    .retro-marquee-inner { font-size: 16px; }

    /* Stack columns vertically */
    [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        width: 100% !important; flex: 1 1 100% !important; min-width: 0 !important;
    }

    /* Bigger text areas */
    .stTextArea textarea {
        font-size: 16px !important;
        min-height: 180px !important;
    }

    /* Bigger buttons — full width, tall tap targets */
    .stButton > button,
    .stButton > button[kind="primary"] {
        font-size: 16px !important;
        padding: 14px 20px !important;
        min-height: 50px;
        width: 100% !important;
    }

    /* Before/After */
    .ba-compare { flex-direction: column !important; align-items: center !important; gap: 8px !important; }
    .ba-card { min-width: unset !important; max-width: 220px !important; }
    .ba-arrow { font-size: 28px !important; transform: rotate(90deg); }

    /* Panels — bigger padding, bigger text */
    .win95-panel-content { padding: 12px !important; font-size: 15px !important; }

    /* Footer status bar */
    .status-bar {
        flex-wrap: wrap !important; gap: 6px !important;
        justify-content: center !important; padding: 8px 10px !important;
    }
    .status-bar .status-section { font-size: 12px !important; padding: 4px 8px !important; }

    /* Copy button full width */
    .copy-btn-wrap { text-align: center; }
    .copy-btn-wrap button { width: 100%; padding: 12px 16px !important; min-height: 48px; font-size: 15px !important; }

    /* Prevent iOS zoom */
    input, select, textarea { font-size: 16px !important; }

    /* General text scaling */
    .stMarkdown p, .stMarkdown li { font-size: 15px !important; }

    /* Sidebar — more opaque on mobile */
    [data-testid="stSidebar"] {
        background: rgba(192, 192, 192, 0.95) !important;
    }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
    .rainbow-text { animation: none; color: #ff0000; }
    .blink-new { animation: none; }
    .retro-marquee-inner { animation: none; }
    .online-dot { animation: none; }
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<style>{_bliss_css}</style>", unsafe_allow_html=True)

# Clear stuck sidebar collapsed state (st.components.v1.html runs JS reliably)
import streamlit.components.v1 as components
components.html("""
<script>
try { window.parent.localStorage.removeItem('stSidebarCollapsed'); } catch(e){}
</script>
""", height=0)


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
    ("before_ai_pct", 0), ("before_human_pct", 0),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ============================================================
# SIDEBAR
# ============================================================
import random
if "visitor_count" not in st.session_state:
    st.session_state.visitor_count = random.randint(48200, 51999)

with st.sidebar:
    st.markdown("""
    <div class="win95-titlebar" style="margin-bottom:0;padding:6px 10px;">
        <span style="font-size:14px;letter-spacing:1px;">⚡ TURNITOUT.EXE</span>
        <div class="win-buttons">
            <span class="win-btn">_</span>
            <span class="win-btn">□</span>
            <span class="win-btn">X</span>
        </div>
    </div>
    <div class="sidebar-info" style="margin-top:0;border-top:none;padding:14px 12px;">
        <div class="operator-name" style="font-size:16px;">ALEX SHIBU</div>
        <div class="tagline">Physics + CS // UofToronto</div>
        <div class="tagline">God Bless the Hustle 🚢</div>
        <div class="online-indicator"><span class="online-dot"></span> ONLINE — READY</div>
        <a href="https://alexshibu.com" target="_blank" rel="noopener noreferrer" style="display:inline-block;margin-top:6px;color:#0000ff;font-family:'Courier New',monospace;font-size:11px;text-decoration:underline;font-weight:bold;">🌐 alexshibu.com</a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="retro-clock" id="retroClock">00:00:00</div>
    <div class="mini-hit-counter">
        <span>👁 VISITORS:</span>
        <span class="counter-digits">{st.session_state.visitor_count:06d}</span>
    </div>
    <script>
    function updateClock() {{
        const now = new Date();
        const h = String(now.getHours()).padStart(2, '0');
        const m = String(now.getMinutes()).padStart(2, '0');
        const s = String(now.getSeconds()).padStart(2, '0');
        const els = document.querySelectorAll('#retroClock, .retro-clock');
        els.forEach(el => {{ el.textContent = h + ':' + m + ':' + s; }});
    }}
    updateClock();
    setInterval(updateClock, 1000);
    </script>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="sidebar-feature-box">
        <b>What This Does:</b>
        <ul>
            <li>Rewrites AI text to sound human</li>
            <li>1012+ synonym/phrase rules</li>
            <li>11-stage transformation pipeline</li>
            <li>Per-sentence AI detection scoring</li>
            <li>Zero APIs. Zero cost. Zero data stored.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("##### MODE")
    mode = st.radio("Select mode", ["Humanizer", "Scanner", "Document"], index=0, label_visibility="collapsed")

    st.markdown('<div class="groove-hr"></div>', unsafe_allow_html=True)
    st.markdown("##### WRITING STYLE")

    PRESETS = {
        "📄 Academic": 0.70,
        "✏️ Essay": 0.45,
        "🔬 Lab Report": 0.60,
        "💬 Casual": 0.35,
        "⚙️ Custom": None,
    }
    preset = st.radio("Select style", list(PRESETS.keys()), index=0, label_visibility="collapsed", horizontal=True)

    if PRESETS[preset] is not None:
        aggressiveness = PRESETS[preset]
        st.markdown(
            f'<div style="font-family:Courier New,monospace;font-size:12px;'
            f'color:#000080;margin:-8px 0 8px 0;">'
            f'INTENSITY: <b>{aggressiveness:.2f}</b></div>',
            unsafe_allow_html=True,
        )
    else:
        aggressiveness = st.slider("REWRITE INTENSITY", 0.1, 1.0, 0.55, 0.05)

    purge_unicode = st.checkbox("PURGE ZERO-WIDTH UNICODE", value=True)

    seed = st.number_input("SEED (0=RANDOM)", 0, 999999, 0)

    st.markdown("""
    <div class="sidebar-feature-box" style="background:#fff;margin-top:16px;">
        <b>Bypasses:</b>
        <ul>
            <li>Turnitin</li>
            <li>GPTZero</li>
            <li>Copyleaks</li>
            <li>ZeroGPT</li>
            <li>Originality.ai</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="sidebar-taskbar">
        <div class="taskbar-start">🪟 Start</div>
        <div style="flex:1;"></div>
        <div class="taskbar-tray" id="trayTime">--:--</div>
    </div>
    <script>
    function updateTray() {{
        const now = new Date();
        const h = now.getHours() % 12 || 12;
        const m = String(now.getMinutes()).padStart(2, '0');
        const ap = now.getHours() >= 12 ? 'PM' : 'AM';
        const els = document.querySelectorAll('#trayTime, .taskbar-tray');
        els.forEach(el => {{ el.textContent = h + ':' + m + ' ' + ap; }});
    }}
    updateTray();
    setInterval(updateTray, 1000);
    </script>
    """, unsafe_allow_html=True)


# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div class="win95-titlebar" style="font-size:20px;padding:12px 16px;margin-bottom:0;position:relative;z-index:999;">
    <span style="letter-spacing:1.5px;">🖥️ TURNITOUT — AI TEXT HUMANIZER</span>
    <div class="win-buttons">
        <span class="win-btn">_</span>
        <span class="win-btn">□</span>
        <span class="win-btn">X</span>
    </div>
</div>
<div class="retro-marquee">
    <div class="retro-marquee-inner">
        ★ TURNITOUT ★
        &nbsp;&nbsp;—&nbsp;&nbsp;
        "Turned $3K into $100K, then lost it all. Asymmetric outcomes go both ways." — Alex
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        "Education is kindling a flame, not filling a vessel." — Socrates (never cited his sources)
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        "This isn't cheating. This is a sidequest." — Alex
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        "The only thing I know is that I know nothing." — Socrates (still got tenure)
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        "If the AI wrote it and I edited it, that's a collab." — Alex
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        "The mind is not a vessel to be filled but a fire to be kindled." — Plutarch (recycled Socrates)
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        "God bless the hustle." — Alex
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        "I don't always test my code, but when I do, I do it in production." — Alex
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        "Build first. Ask permission never." — Alex
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        "Getting dangerous at things is more fun than getting good." — Alex
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        "My professor said 'write in your own words.' These are my own words now." — Alex
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        "Every rabbit hole is a curriculum no one assigned." — Alex
        &nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;
        BUILT BY ALEX SHIBU — ZERO AI — 1012+ RULES
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
            before = compute_perplexity_score(input_text)
            before_human = before["combined_score"]
            before_ai = max(0, 100 - before_human)
            result, stats, ai_pct, human_pct = run_transform(
                input_text, aggressiveness, purge_unicode, seed
            )
        st.session_state.result = result
        st.session_state.stats = stats
        st.session_state.input_text = input_text
        st.session_state.ai_pct = ai_pct
        st.session_state.human_pct = human_pct
        st.session_state.before_ai_pct = before_ai
        st.session_state.before_human_pct = before_human

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
            b_ai = st.session_state.before_ai_pct
            b_human = st.session_state.before_human_pct
            drop = b_ai - ai
            st.markdown(
                f'<div class="win95-panel"><div class="win95-panel-content" '
                f'style="text-align:center;padding:12px;">'
                f'<div class="ba-compare">'
                f'<div class="ba-card">'
                f'<div class="ba-label before">BEFORE</div>'
                f'{render_donut_svg(b_ai, b_human, 140)}'
                f'</div>'
                f'<div class="ba-arrow">→</div>'
                f'<div class="ba-card">'
                f'<div class="ba-label after">AFTER</div>'
                f'{render_donut_svg(ai, human, 140)}'
                f'</div>'
                f'</div>'
                f'<div style="margin-top:8px;font-family:Courier New,monospace;'
                f'font-size:13px;font-weight:bold;color:#006600;">'
                f'AI SCORE DROPPED {drop:.0f} POINTS</div>'
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

        escaped_result = html_escape(st.session_state.result).replace("'", "\\'").replace("\n", "\\n")
        st.markdown(
            f'''<div class="copy-btn-wrap">
            <button onclick="
                navigator.clipboard.writeText('{escaped_result}');
                this.textContent='✅ COPIED!';
                setTimeout(()=>this.textContent='📋 COPY TO CLIPBOARD', 1500);
            ">📋 COPY TO CLIPBOARD</button>
            </div>''',
            unsafe_allow_html=True,
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
    <div class="status-section">Built by <b><a href="https://alexshibu.com" target="_blank" rel="noopener noreferrer" style="color:#000080;text-decoration:underline;">Alex Shibu</a></b></div>
    <div class="status-section">Engine v2.0 — 11 Stages</div>
    <div class="status-section">1012+ Rules</div>
    <div class="status-section">Zero APIs — Zero Cost</div>
</div>
""", unsafe_allow_html=True)
