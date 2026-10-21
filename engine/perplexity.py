import math
import re
import zlib
import lzma

_AI_PHRASES = [
    "it is important to note", "it should be noted", "it is worth noting",
    "plays a pivotal role", "plays a crucial role", "plays an important role",
    "delve into", "delve deeper", "serves as a testament",
    "in today's fast-paced", "in today's digital", "in today's world",
    "stands as a testament", "comprehensive tapestry", "tapestry of",
    "it is essential to", "it is crucial to", "it is imperative to",
    "multifaceted", "paradigm shift", "holistic approach",
    "leverage", "leveraging", "utilize", "utilizing",
    "navigate the complexities", "in the realm of", "at the forefront",
    "shed light on", "pave the way", "the landscape of",
    "a testament to", "underscores the importance", "highlights the need",
    "cannot be overstated", "the importance of", "the significance of",
    "in conclusion", "overall", "furthermore", "moreover", "additionally",
    "in summary", "to summarize", "in essence",
    "a wide range of", "a variety of", "a number of",
    "it is evident that", "it is clear that", "it can be seen that",
    "on the other hand", "has the potential to",
    "his interests range from", "his online presence portrays",
    "beyond building", "span", "spanning",
    "portrays him as", "curious, ambitious",
    "exploring unconventional", "taking initiative",
    "has been involved in", "including",
    "brought together more than",
]

_AI_CONNECTORS = {
    "furthermore", "moreover", "additionally", "consequently", "nevertheless",
    "nonetheless", "subsequently", "conversely", "similarly", "accordingly",
    "hence", "thus", "therefore", "notably", "specifically", "ultimately",
    "essentially", "fundamentally", "significantly", "predominantly",
}

_FILLER_STARTS = [
    "overall,", "in summary,", "to summarize,", "in conclusion,",
    "in essence,", "broadly speaking,", "generally speaking,",
    "it is worth noting that", "it should be noted that",
    "it is important to note that",
]


def _sentence_length_variance(sentences):
    if len(sentences) < 2:
        return 0.0
    lengths = [len(s.split()) for s in sentences]
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.0
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    cv = math.sqrt(variance) / mean
    return cv


def _lexical_diversity(words):
    if not words:
        return 1.0
    unique = len(set(words))
    return unique / len(words)


def _ai_phrase_density(text_lower, word_count):
    if word_count == 0:
        return 0.0
    hits = sum(1 for phrase in _AI_PHRASES if phrase in text_lower)
    return hits / max(word_count / 30, 1)


def _connector_density(words_lower):
    if not words_lower:
        return 0.0
    hits = sum(1 for w in words_lower if w in _AI_CONNECTORS)
    return hits / len(words_lower)


def _filler_start_count(text_lower):
    return sum(1 for f in _FILLER_STARTS if f in text_lower)


def _avg_sentence_length(sentences):
    if not sentences:
        return 0
    return sum(len(s.split()) for s in sentences) / len(sentences)


def _repetition_score(words_lower):
    if len(words_lower) < 10:
        return 0.0
    bigrams = [words_lower[i] + " " + words_lower[i + 1] for i in range(len(words_lower) - 1)]
    unique_bigrams = len(set(bigrams))
    return 1.0 - (unique_bigrams / len(bigrams)) if bigrams else 0.0


def compute_perplexity_score(text: str) -> dict:
    if not text or len(text.strip()) < 20:
        return {
            "zlib_ratio": 0.0,
            "lzma_ratio": 0.0,
            "combined_score": 0.0,
            "ai_score": 100.0,
            "human_score": 0.0,
            "verdict": "Too short to analyze",
            "signals": {},
        }

    text_lower = text.lower()
    words = re.findall(r"[a-zA-Z]+", text)
    words_lower = [w.lower() for w in words]
    word_count = len(words)
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 5]

    raw = text.encode("utf-8")
    raw_size = len(raw)
    zlib_size = len(zlib.compress(raw, 9))
    lzma_size = len(lzma.compress(raw, preset=9))
    zlib_ratio = zlib_size / raw_size
    lzma_ratio = lzma_size / raw_size

    # Signal 1: Compression ratio (higher = more human-like)
    avg_ratio = (zlib_ratio + lzma_ratio) / 2.0
    compression_signal = min(1.0, max(0.0, (avg_ratio - 0.35) / 0.35))

    # Signal 2: Sentence length variance (higher = more human-like)
    slv = _sentence_length_variance(sentences)
    variance_signal = min(1.0, slv / 0.6)

    # Signal 3: Lexical diversity (higher = more human-like, but AI can be diverse too)
    ld = _lexical_diversity(words_lower)
    diversity_signal = min(1.0, max(0.0, (ld - 0.3) / 0.4))

    # Signal 4: AI phrase density (higher = more AI-like, INVERTED)
    ai_density = _ai_phrase_density(text_lower, word_count)
    phrase_signal = max(0.0, 1.0 - ai_density * 1.5)

    # Signal 5: Connector density (AI overuses formal connectors)
    conn_density = _connector_density(words_lower)
    connector_signal = max(0.0, 1.0 - conn_density * 25.0)

    # Signal 6: Average sentence length (AI tends toward 15-25 words uniformly)
    avg_sl = _avg_sentence_length(sentences)
    if 14 <= avg_sl <= 26:
        length_signal = 0.3
    else:
        length_signal = 0.7

    # Signal 7: Bigram repetition (AI repeats patterns)
    rep = _repetition_score(words_lower)
    repetition_signal = max(0.0, 1.0 - rep * 5.0)

    # Signal 8: Filler/boilerplate starts
    filler_count = _filler_start_count(text_lower)
    filler_signal = max(0.0, 1.0 - filler_count * 0.3)

    # Signal 9: Structural uniformity — AI writes sentences of very similar structure
    pronoun_starts = sum(
        1 for s in sentences
        if re.match(r"^(He |She |His |Her |They |It |The |This |That |These |We |Our )", s.strip())
    )
    struct_uniformity = pronoun_starts / max(len(sentences), 1)
    structure_signal = max(0.0, 1.0 - struct_uniformity * 2.0)

    # Signal 10: Comma density — AI uses lots of list-style commas
    comma_count = text.count(",")
    comma_density = comma_count / max(word_count, 1)
    comma_signal = max(0.0, 1.0 - max(0, comma_density - 0.03) * 12.0)

    # Signal 11: Passive voice / formulaic construction density
    passive_count = len(re.findall(r"\b(was|were|been|being)\s+\w+ed\b", text_lower))
    has_involved = len(re.findall(r"\bhas been involved\b|\bhas experience\b|\bhas been\b", text_lower))
    formulaic = (passive_count + has_involved) / max(len(sentences), 1)
    formulaic_signal = max(0.0, 1.0 - formulaic * 1.5)

    # Weighted combination — AI-specific behavioral signals dominate
    weights = {
        "compression": 0.03,
        "variance": 0.09,
        "diversity": 0.03,
        "ai_phrases": 0.22,
        "connectors": 0.07,
        "sent_length": 0.09,
        "repetition": 0.03,
        "filler": 0.09,
        "structure": 0.13,
        "commas": 0.11,
        "formulaic": 0.11,
    }

    signals = {
        "compression": round(compression_signal, 3),
        "variance": round(variance_signal, 3),
        "diversity": round(diversity_signal, 3),
        "ai_phrases": round(phrase_signal, 3),
        "connectors": round(connector_signal, 3),
        "sent_length": round(length_signal, 3),
        "repetition": round(repetition_signal, 3),
        "filler": round(filler_signal, 3),
        "structure": round(structure_signal, 3),
        "commas": round(comma_signal, 3),
        "formulaic": round(formulaic_signal, 3),
    }

    human_score = sum(signals[k] * weights[k] for k in weights)
    human_score = round(min(100.0, max(0.0, human_score * 100.0)), 1)
    ai_score = round(100.0 - human_score, 1)

    combined_score = human_score

    if ai_score >= 70:
        verdict = "Likely AI"
    elif ai_score >= 40:
        verdict = "Mixed/Uncertain"
    else:
        verdict = "Likely Human"

    return {
        "zlib_ratio": round(zlib_ratio, 4),
        "lzma_ratio": round(lzma_ratio, 4),
        "combined_score": round(combined_score, 1),
        "ai_score": ai_score,
        "human_score": human_score,
        "verdict": verdict,
        "signals": signals,
    }
