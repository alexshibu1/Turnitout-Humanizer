import zlib
import lzma


def compute_perplexity_score(text: str) -> dict:
    if not text or len(text.strip()) < 20:
        return {
            "zlib_ratio": 0.0,
            "lzma_ratio": 0.0,
            "combined_score": 0.0,
            "verdict": "Too short to analyze",
        }

    raw = text.encode("utf-8")
    raw_size = len(raw)

    zlib_size = len(zlib.compress(raw, 9))
    lzma_size = len(lzma.compress(raw, preset=9))

    zlib_ratio = zlib_size / raw_size
    lzma_ratio = lzma_size / raw_size

    # Scale the average ratio into a 0-100 score.
    # Typical ratios: highly repetitive AI text ~0.25-0.40, human text ~0.45-0.70+
    avg_ratio = (zlib_ratio + lzma_ratio) / 2.0
    score = min(100.0, max(0.0, (avg_ratio - 0.20) / 0.50 * 100.0))

    if score < 30:
        verdict = "Likely AI"
    elif score < 55:
        verdict = "Mixed/Uncertain"
    else:
        verdict = "Likely Human"

    return {
        "zlib_ratio": round(zlib_ratio, 4),
        "lzma_ratio": round(lzma_ratio, 4),
        "combined_score": round(score, 1),
        "verdict": verdict,
    }
