import streamlit as st
import io
import zipfile
from engine.transformer import TextTransformer
from engine.perplexity import compute_perplexity_score
from engine.unicode_purge import purge_zero_width
from engine.docx_processor import read_docx, write_docx

st.set_page_config(
    page_title="Turnitout — AI Text Humanizer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    .stat-box {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #e63946;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        margin: 4px;
    }
    .stat-box h3 { color: #e63946; margin: 0; font-size: 1.8em; }
    .stat-box p { color: #aaa; margin: 4px 0 0 0; font-size: 0.85em; }
    .score-good { color: #2ecc71 !important; }
    .score-mid { color: #f39c12 !important; }
    .score-bad { color: #e63946 !important; }
</style>
""", unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.title("Turnitout Engine")
        st.caption("100% Rule-Based — Zero AI APIs — Zero Cost")
        st.divider()

        mode = st.radio(
            "Mode",
            ["Text Humanizer", "Document (.docx)", "Perplexity Checker"],
            index=0,
        )

        st.divider()
        st.subheader("Engine Controls")

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
        st.caption("Built for personal use. No data stored.")

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
            f"<p>Perplexity Score (after)</p></div>",
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
    st.header("Text Humanizer")
    st.caption(
        "Paste text below. The engine rewrites it using deterministic rules — "
        "synonym swaps, phrase rewrites, discourse rotation, and n-gram disruption."
    )

    input_text = st.text_area(
        "Input Text",
        height=250,
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
            st.subheader("Original")
            st.text_area("original_display", input_text, height=300, disabled=True, label_visibility="collapsed")
        with col_right:
            st.subheader("Humanized")
            st.text_area("result_display", result, height=300, label_visibility="collapsed")

        with st.expander("Transformation Breakdown"):
            for key, val in stats.items():
                if key != "total" and val > 0:
                    st.write(f"**{key.replace('_', ' ').title()}**: {val}")


def docx_page(aggressiveness, purge_unicode, seed):
    st.header("Document Processor (.docx)")
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

        with st.expander("Preview Changes (first 10 paragraphs)"):
            for i, (orig, new) in enumerate(zip(full_before[:10], full_after[:10])):
                if orig != new:
                    st.markdown(f"**Paragraph {i+1}**")
                    st.text(f"  Before: {orig[:200]}...")
                    st.text(f"  After:  {new[:200]}...")
                    st.divider()


def checker_page():
    st.header("Perplexity Checker")
    st.caption(
        "Check how 'human' your text reads using compression-based entropy analysis. "
        "No AI API calls — uses zlib/lzma compression ratios as a proxy for text predictability."
    )

    input_text = st.text_area(
        "Text to Analyze",
        height=250,
        placeholder="Paste text to check its perplexity score...",
    )

    if st.button("Analyze", type="primary", use_container_width=True):
        if not input_text.strip():
            st.warning("Paste some text first.")
            return

        scores = compute_perplexity_score(input_text)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Combined Score", f"{scores['combined_score']:.1f}/100")
        with col2:
            st.metric("zlib Ratio", f"{scores['zlib_ratio']:.3f}")
        with col3:
            st.metric("lzma Ratio", f"{scores['lzma_ratio']:.3f}")

        verdict = scores["verdict"]
        if verdict == "Likely Human":
            st.success(f"Verdict: {verdict}")
        elif verdict == "Likely AI":
            st.error(f"Verdict: {verdict}")
        else:
            st.warning(f"Verdict: {verdict}")

        st.caption(
            "This is a heuristic based on compression entropy, not a definitive detector. "
            "Higher scores indicate more varied/unpredictable text patterns."
        )


def main():
    mode, aggressiveness, purge_unicode, seed = render_sidebar()

    if mode == "Text Humanizer":
        text_humanizer_page(aggressiveness, purge_unicode, seed)
    elif mode == "Document (.docx)":
        docx_page(aggressiveness, purge_unicode, seed)
    elif mode == "Perplexity Checker":
        checker_page()


if __name__ == "__main__":
    main()
