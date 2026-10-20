import json
import os
import re
import random


_RULES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules")

_VOICE_VERBS = {
    "analyze": "analyzed", "demonstrate": "demonstrated", "investigate": "investigated",
    "examine": "examined", "evaluate": "evaluated", "observe": "observed",
    "compute": "computed", "derive": "derived", "implement": "implemented",
    "propose": "proposed", "develop": "developed", "apply": "applied",
    "measure": "measured", "determine": "determined", "establish": "established",
    "validate": "validated", "simulate": "simulated", "formulate": "formulated",
    "assess": "assessed", "identify": "identified",
}

# Pattern: "We/They/The authors <verb> the/a/this ..."
_ACTIVE_RE = re.compile(
    r"\b(We|They|The authors?|Researchers?)\s+("
    + "|".join(_VOICE_VERBS.keys())
    + r")\b\s+(the|a|an|this|these|those|each|our)\b",
    re.IGNORECASE,
)


def _load_json(filename, default):
    path = os.path.join(_RULES_DIR, filename)
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TextTransformer:
    def __init__(self, aggressiveness: float = 0.5, seed: int | None = None):
        self.aggressiveness = max(0.0, min(1.0, aggressiveness))
        self.rng = random.Random(seed)
        self.stats: dict[str, int] = {}
        self._used_discourse: dict[str, str] = {}
        self._load_rules()

    def _load_rules(self):
        self.synonyms: dict[str, list[str]] = _load_json("synonyms.json", {})
        self.phrases: list[list[str]] = _load_json("phrases.json", [])
        self.hedge_words: list[str] = _load_json("hedge_words.json", [])
        self.determiners: dict[str, list[str]] = _load_json("determiners.json", {})
        self.discourse_markers: dict[str, list[str]] = _load_json("discourse_markers.json", {})
        self.protected_terms: list[str] = _load_json("protected_terms.json", [])
        # Build a lowercase lookup for synonyms for fast matching
        self._syn_lower = {k.lower(): v for k, v in self.synonyms.items()}

    def _reset_stats(self):
        self.stats = {
            "phrases_replaced": 0,
            "synonyms_replaced": 0,
            "determiners_swapped": 0,
            "discourse_rotated": 0,
            "hedge_words_injected": 0,
            "sentences_split": 0,
            "voice_transformed": 0,
            "total": 0,
        }
        self._used_discourse = {}

    def transform(self, text: str) -> str:
        self._reset_stats()
        lines = text.split("\n")
        result = []
        for line in lines:
            result.append(self._transform_line(line))
        self.stats["total"] = sum(
            v for k, v in self.stats.items() if k != "total"
        )
        return "\n".join(result)

    def _transform_line(self, line: str) -> str:
        stripped = line.strip()
        if not stripped:
            return line

        leading_ws = line[: len(line) - len(line.lstrip())]

        text = stripped
        text, placeholders = self._protect_terms(text)
        text = self._apply_phrase_rewrites(text)
        text = self._apply_synonyms(text)
        text = self._swap_determiners(text)
        text = self._rotate_discourse_markers(text)
        text = self._inject_hedge_words(text)
        text = self._split_compound(text)
        text = self._transform_voice(text)
        text = self._restore_terms(text, placeholders)

        return leading_ws + text

    # ---- Stage 1: Protect terms ----

    def _protect_terms(self, text: str) -> tuple[str, list[tuple[str, str]]]:
        placeholders = []
        for i, term in enumerate(self.protected_terms):
            tag = f"\x00PROT_{i}\x00"
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            match = pattern.search(text)
            if match:
                original = match.group()
                text = pattern.sub(tag, text)
                placeholders.append((tag, original))
        return text, placeholders

    def _restore_terms(self, text: str, placeholders: list[tuple[str, str]]) -> str:
        for tag, original in placeholders:
            text = text.replace(tag, original)
        return text

    # ---- Stage 2: Phrase rewrites ----

    def _apply_phrase_rewrites(self, text: str) -> str:
        prob = self.aggressiveness * 0.8
        for entry in self.phrases:
            if len(entry) != 2:
                continue
            pattern_str, replacement = entry
            if self.rng.random() > prob:
                continue
            try:
                compiled = re.compile(pattern_str, re.IGNORECASE)
                match = compiled.search(text)
                if match:
                    original = match.group()
                    # Preserve leading capitalization
                    final = _match_case(original, replacement)
                    text = compiled.sub(final, text, count=1)
                    self.stats["phrases_replaced"] += 1
            except re.error:
                continue
        return text

    # ---- Stage 3: Synonym replacement ----

    def _apply_synonyms(self, text: str) -> str:
        prob = self.aggressiveness * 0.4
        tokens = re.split(r"(\W+)", text)
        changed = False
        for i, token in enumerate(tokens):
            if not token or not token[0].isalpha():
                continue
            lower = token.lower()
            if lower not in self._syn_lower:
                continue
            if self.rng.random() > prob:
                continue
            alternatives = self._syn_lower[lower]
            chosen = self.rng.choice(alternatives)
            tokens[i] = _match_case(token, chosen)
            self.stats["synonyms_replaced"] += 1
            changed = True
        return "".join(tokens) if changed else text

    # ---- Stage 4: Determiner swaps ----

    def _swap_determiners(self, text: str) -> str:
        prob = self.aggressiveness * 0.3
        for det, alternatives in self.determiners.items():
            if self.rng.random() > prob:
                continue
            pattern = re.compile(r"\b" + re.escape(det) + r"\b", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                original = match.group()
                chosen = self.rng.choice(alternatives)
                final = _match_case(original, chosen)
                text = pattern.sub(final, text, count=1)
                self.stats["determiners_swapped"] += 1
        return text

    # ---- Stage 5: Discourse marker rotation ----

    def _rotate_discourse_markers(self, text: str) -> str:
        prob = self.aggressiveness * 0.6
        for marker, alternatives in self.discourse_markers.items():
            if self.rng.random() > prob:
                continue
            pattern = re.compile(r"\b" + re.escape(marker) + r"\b", re.IGNORECASE)
            match = pattern.search(text)
            if not match:
                continue
            original = match.group()
            # Avoid repeating the same replacement within one transform() call
            available = [a for a in alternatives if a != self._used_discourse.get(marker)]
            if not available:
                available = alternatives
            chosen = self.rng.choice(available)
            self._used_discourse[marker] = chosen
            final = _match_case(original, chosen)
            text = pattern.sub(final, text, count=1)
            self.stats["discourse_rotated"] += 1
        return text

    # ---- Stage 6: Hedge word injection ----

    def _inject_hedge_words(self, text: str) -> str:
        if not self.hedge_words:
            return text
        prob = self.aggressiveness * 0.25
        if len(text) < 60 or self.rng.random() > prob:
            return text

        # Insert a hedge word after the first comma or semicolon
        for sep in [", ", "; "]:
            idx = text.find(sep)
            if idx != -1 and idx > 15:
                hedge = self.rng.choice(self.hedge_words)
                insert_pos = idx + len(sep)
                text = text[:insert_pos] + hedge + " " + text[insert_pos:]
                self.stats["hedge_words_injected"] += 1
                return text
        return text

    # ---- Stage 7: Compound sentence splitting ----

    def _split_compound(self, text: str) -> str:
        prob = self.aggressiveness * 0.3
        if self.rng.random() > prob:
            return text

        for conj in [" and ", " but "]:
            idx = text.find(conj)
            if idx == -1:
                continue
            left = text[:idx].strip()
            right = text[idx + len(conj):].strip()
            if len(left) < 40 or len(right) < 40:
                continue
            # Only split if both sides look like independent clauses
            # (start with uppercase or contain a verb-like pattern)
            right_sent = right[0].upper() + right[1:] if right else right
            if not left.endswith((".", "!", "?")):
                left += "."
            text = left + " " + right_sent
            self.stats["sentences_split"] += 1
            return text
        return text

    # ---- Stage 8: Voice transformation ----

    def _transform_voice(self, text: str) -> str:
        prob = self.aggressiveness * 0.2
        if self.rng.random() > prob:
            return text

        match = _ACTIVE_RE.search(text)
        if not match:
            return text

        full = match.group()
        subject = match.group(1)
        verb = match.group(2).lower()
        det = match.group(3)

        past_participle = _VOICE_VERBS.get(verb)
        if not past_participle:
            return text

        # Extract the object: everything after the determiner until end of sentence or comma
        rest_start = match.end()
        rest = text[rest_start:]
        obj_match = re.match(r"([^,.;]+)", rest)
        if not obj_match:
            return text

        obj = det + " " + obj_match.group(1).strip()
        obj_capitalized = obj[0].upper() + obj[1:]
        passive = f"{obj_capitalized} was {past_participle}"

        replacement_end = rest_start + obj_match.end()
        text = text[: match.start()] + passive + text[replacement_end:]
        self.stats["voice_transformed"] += 1
        return text


def _match_case(original: str, replacement: str) -> str:
    if not original or not replacement:
        return replacement
    if original[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement
