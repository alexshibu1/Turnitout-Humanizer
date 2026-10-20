import streamlit as st
import re
import io
import zipfile
from engine.transformer import TextTransformer
from engine.perplexity import compute_perplexity_score
from engine.unicode_purge import purge_zero_width
from engine.docx_processor import read_docx, write_docx

st.set_page_config(
    page_title="Turnitout — Alex's Text Humanizer",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');

    .stApp {
        max-width: 1200px;
        margin: 0 auto;
        font-family: 'Quicksand', sans-serif;
    }

    /* Pastel Kawaii Theme */
    .stat-box {
        background: linear-gradient(135deg, #fce4ec, #f3e5f5);
        border: 2px solid #f8bbd0;
        border-radius: 18px;
        padding: 18px;
        text-align: center;
        margin: 4px;
        box-shadow: 0 4px 14px rgba(244, 143, 177, 0.15);
    }
    .stat-box h3 { color: #ad1457; margin: 0; font-size: 1.8em; font-weight: 700; }
    .stat-box p { color: #7b1fa2; margin: 4px 0 0 0; font-size: 0.85em; font-weight: 500; }
    .score-good { color: #66bb6a !important; }
    .score-mid { color: #ffa726 !important; }
    .score-bad { color: #ef5350 !important; }

    .sentence-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 12px;
        font-size: 0.92em;
        line-height: 1.5;
    }
    .sentence-row:nth-child(odd) { background: #fce4ec44; }
    .sentence-row:nth-child(even) { background: #e1bee744; }
    .score-pill {
        flex-shrink: 0;
        min-width: 56px;
        text-align: center;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.82em;
    }
    .pill-good { background: #c8e6c9; color: #2e7d32; }
    .pill-mid { background: #fff3e0; color: #e65100; }
    .pill-bad { background: #ffcdd2; color: #c62828; }
    .sentence-text { flex: 1; }

    .brand-footer {
        text-align: center;
        padding: 24px 0 12px 0;
        color: #ce93d8;
        font-size: 0.8em;
        font-weight: 500;
    }
    .brand-footer a { color: #f48fb1; text-decoration: none; }

    /* Override Streamlit defaults for kawaii vibe */
    .stRadio > label { font-weight: 600; }
    h1, h2, h3 { font-family: 'Quicksand', sans-serif !important; }
</style>
""", unsafe_allow_html=True)


def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]


def score_sentence(sentence):
    if len(sentence) < 20:
        return {"combined_score": 50.0, "verdict": "Too short"}
    return compute_perplexity_score(sentence)


def render_sentence_scores(sentences, label=""):
    if label:
        st.caption(label)
    html_parts = []
    for s in sentences:
        sc = score_sentence(s)
        score = sc["combined_score"]
        if score > 55:
            pill_class = "pill-good"
        elif score > 30:
            pill_class = "pill-mid"
        else:
            pill_class = "pill-bad"
        escaped = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_parts.append(
            f'<div class="sentence-row">'
            f'<span class="score-pill {pill_class}">{score:.0f}</span>'
            f'<span class="sentence-text">{escaped}</span>'
            f'</div>'
        )
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown("## 🌸 Turnitout")
        st.caption("Alex's personal humanizer")
        st.divider()

        mode = st.radio(
            "Mode",
            ["Text Humanizer", "Document (.docx)", "Sentence Scanner"],
            index=0,
        )

        st.divider()
        st.markdown("##### Engine Controls")

        aggressiveness = st.slider(
            "Rewrite Intensity",
            min_value=0.1,
            max_value=1.0,
            value=0.5,
            step=0.05,
            help="Higher = more words replaced, more transformations applied",
        )

        purge_unicode = st.checkbox(
            "Purge Zero-Width Unicode",
            value=True,
            help="Remove invisible tracking characters (U+200B, U+200D, etc.)",
        )

        seed = st.number_input(
            "Random Seed (0 = random)",
            min_value=0,
            max_value=999999,
            value=0,
            help="Set a seed for reproducible results",
        )

        st.divider()
        st.markdown(
            '<div class="brand-footer">built by <strong>Alex Shibu</strong></div>',
            unsafe_allow_html=True,
        )

    return mode, aggressiveness, purge_unicode, seed


def render_stats(stats, before_score, after_score):
    cols = st.columns(4)
    with cols[0]:
        total = stats.get("total", 0)
        st.markdown(
            f'<div class="stat-box"><h3>{total}</h3><p>Total Transforms</p></div>',
            unsafe_allow_html=True,
        )
    with cols[1]:
        syn = stats.get("synonyms_replaced", 0) + stats.get("phrases_replaced", 0)
        st.markdown(
            f'<div class="stat-box"><h3>{syn}</h3><p>Word & Phrase Swaps</p></div>',
            unsafe_allow_html=True,
        )
    with cols[2]:
        score_class = (
            "score-good" if after_score > 55 else "score-mid" if after_score > 30 else "score-bad"
        )
        st.markdown(
            f'<div class="stat-box"><h3 class="{score_class}">{after_score:.0f}</h3>'
            f"<p>Perplexity (after)</p></div>",
            unsafe_allow_html=True,
        )
    with cols[3]:
        delta = after_score - before_score
        arrow = "+" if delta > 0 else ""
        st.markdown(
            f'<div class="stat-box"><h3>{arrow}{delta:.1f}</h3><p>Score Change</p></div>',
            unsafe_allow_html=True,
        )


def run_transform(text, aggressiveness, purge_unicode, seed):
    actual_seed = seed if seed != 0 else None
    transformer = TextTransformer(aggressiveness=aggressiveness, seed=actual_seed)

    if purge_unicode:
        text, zw_count = purge_zero_width(text)
    else:
        zw_count = 0

    before = compute_perplexity_score(text)
    result = transformer.transform(text)
    after = compute_perplexity_score(result)

    stats = transformer.stats
    if zw_count > 0:
        stats["zero_width_removed"] = zw_count

    return result, stats, before["combined_score"], after["combined_score"]


def text_humanizer_page(aggressiveness, purge_unicode, seed):
    st.markdown("### 🌷 Text Humanizer")
    st.caption(
        "Paste text below. The engine rewrites using deterministic rules — "
        "synonym swaps, phrase rewrites, discourse rotation, and n-gram disruption."
    )

    input_text = st.text_area(
        "Input Text",
        height=220,
        placeholder="Paste your text here...",
    )

    if st.button("Humanize", type="primary", use_container_width=True):
        if not input_text.strip():
            st.warning("Paste some text first.")
            return

        with st.spinner("Running transformation pipeline..."):
            result, stats, before_score, after_score = run_transform(
                input_text, aggressiveness, purge_unicode, seed
            )

        render_stats(stats, before_score, after_score)
        st.divider()

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("##### Original")
            st.text_area("original_display", input_text, height=250, disabled=True, label_visibility="collapsed")
        with col_right:
            st.markdown("##### Humanized")
            st.text_area("result_display", result, height=250, label_visibility="collapsed")

        st.divider()
        st.markdown("##### Per-Sentence AI Score (Humanized)")
        sentences = split_sentences(result)
        render_sentence_scores(sentences)

        with st.expander("Transformation Breakdown"):
            for key, val in stats.items():
                if key != "total" and val > 0:
                    st.write(f"**{key.replace('_', ' ').title()}**: {val}")


def docx_page(aggressiveness, purge_unicode, seed):
    st.markdown("### 📄 Document Processor (.docx)")
    st.caption("Upload a Word document. Formatting is preserved — only text content is transformed.")

    uploaded = st.file_uploader("Upload .docx", type=["docx"], accept_multiple_files=False)

    if uploaded and st.button("Process Document", type="primary", use_container_width=True):
        file_bytes = uploaded.read()

        with st.spinner("Processing document..."):
            paragraphs = read_docx(file_bytes)

            actual_seed = seed if seed != 0 else None
            transformer = TextTransformer(aggressiveness=aggressiveness, seed=actual_seed)

            transformed_texts = []
            full_before = []
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
                full_before.append(text)
                full_after.append(result)

            output_bytes = write_docx(file_bytes, transformed_texts)

            before_score = compute_perplexity_score("\n".join(full_before))["combined_score"] if full_before else 0
            after_score = compute_perplexity_score("\n".join(full_after))["combined_score"] if full_after else 0

        render_stats(transformer.stats, before_score, after_score)

        st.download_button(
            label="Download Humanized Document",
            data=output_bytes,
            file_name=f"humanized_{uploaded.name}",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

        st.divider()
        st.markdown("##### Per-Sentence AI Score (Humanized)")
        all_sentences = []
        for t in full_after:
            all_sentences.extend(split_sentences(t))
        render_sentence_scores(all_sentences[:30])

        with st.expander("Preview Changes (first 10 paragraphs)"):
            for i, (orig, new) in enumerate(zip(full_before[:10], full_after[:10])):
                if orig != new:
                    st.markdown(f"**Paragraph {i+1}**")
                    st.text(f"  Before: {orig[:200]}...")
                    st.text(f"  After:  {new[:200]}...")
                    st.divider()


def scanner_page():
    st.markdown("### 🔍 Sentence Scanner")
    st.caption(
        "Paste any text and see a per-sentence AI score breakdown. "
        "Each sentence gets its own compression-based perplexity score."
    )

    input_text = st.text_area(
        "Text to Scan",
        height=220,
        placeholder="Paste text to scan each sentence...",
    )

    if st.button("Scan Sentences", type="primary", use_container_width=True):
        if not input_text.strip():
            st.warning("Paste some text first.")
            return

        overall = compute_perplexity_score(input_text)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Overall Score", f"{overall['combined_score']:.1f}/100")
        with col2:
            st.metric("zlib Ratio", f"{overall['zlib_ratio']:.3f}")
        with col3:
            st.metric("lzma Ratio", f"{overall['lzma_ratio']:.3f}")

        verdict = overall["verdict"]
        if verdict == "Likely Human":
            st.success(f"Overall: {verdict}")
        elif verdict == "Likely AI":
            st.error(f"Overall: {verdict}")
        else:
            st.warning(f"Overall: {verdict}")

        st.divider()
        st.markdown("##### Sentence-by-Sentence Breakdown")
        sentences = split_sentences(input_text)
        render_sentence_scores(sentences)

        st.caption(
            "Scores are heuristic (compression entropy). "
            "Higher = more varied text patterns. Lower = more predictable/AI-like."
        )


def main():
    mode, aggressiveness, purge_unicode, seed = render_sidebar()

    if mode == "Text Humanizer":
        text_humanizer_page(aggressiveness, purge_unicode, seed)
    elif mode == "Document (.docx)":
        docx_page(aggressiveness, purge_unicode, seed)
    elif mode == "Sentence Scanner":
        scanner_page()

    st.markdown(
        '<div class="brand-footer">'
        '🌸 <strong>Turnitout</strong> by Alex Shibu — rule-based, zero AI, zero cost'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
