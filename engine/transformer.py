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

_TRANSITION_PHRASES = [
    "Furthermore,", "In addition,", "Moreover,", "Consequently,", "As a result,",
    "Similarly,", "In particular,", "Notably,", "Accordingly,", "By contrast,",
    "Conversely,", "In this regard,", "To this end,", "As such,", "In light of this,",
    "For this reason,", "Along these lines,", "On this basis,", "With this in mind,",
    "In a similar vein,", "On the other hand,", "At the same time,",
    "By the same token,", "In the same way,", "To that effect,",
    "With respect to this,", "From this perspective,", "Given these considerations,",
    "Under these circumstances,", "Bearing this in mind,", "Importantly,",
    "Significantly,", "Remarkably,", "In essence,",
]

_NOMINALIZE_MAP = {
    "analyze": "analysis", "investigate": "investigation", "apply": "application",
    "develop": "development", "improve": "improvement", "evaluate": "evaluation",
    "derive": "derivation", "compute": "computation", "simulate": "simulation",
    "approximate": "approximation", "converge": "convergence", "solve": "solution",
    "implement": "implementation", "formulate": "formulation",
    "transform": "transformation", "integrate": "integration",
    "observe": "observation", "measure": "measurement", "determine": "determination",
    "classify": "classification", "optimize": "optimization",
    "validate": "validation", "demonstrate": "demonstration",
    "reduce": "reduction", "extend": "extension",
}

_CLAUSE_FRONT_RE = re.compile(
    r"^(In |For |Using |By |With |Through |During )(.*?),\s+(.+)$"
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
        self._used_transitions: set[str] = set()
        self._load_rules()

    def _load_rules(self):
        self.synonyms: dict[str, list[str]] = _load_json("synonyms.json", {})
        self.phrases: list[list[str]] = _load_json("phrases.json", [])
        self.hedge_words: list[str] = _load_json("hedge_words.json", [])
        self.determiners: dict[str, list[str]] = _load_json("determiners.json", {})
        self.discourse_markers: dict[str, list[str]] = _load_json("discourse_markers.json", {})
        self.protected_terms: list[str] = _load_json("protected_terms.json", [])
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
            "transitions_injected": 0,
            "nominalizations": 0,
            "clauses_reordered_adv": 0,
            "total": 0,
        }
        self._used_discourse = {}
        self._used_transitions = set()

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
        text = self._inject_transitions(text)
        text = self._nominalize(text)
        text = self._reorder_clauses_advanced(text)
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

        verb = match.group(2).lower()
        det = match.group(3)

        past_participle = _VOICE_VERBS.get(verb)
        if not past_participle:
            return text

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

    # ---- Stage 9: Transition phrase injection ----

    def _inject_transitions(self, text: str) -> str:
        prob = self.aggressiveness * 0.2
        if len(text) < 80 or self.rng.random() > prob:
            return text

        # Find a sentence boundary (". " followed by an uppercase letter)
        boundary = re.search(r"\.\s+([A-Z])", text)
        if not boundary:
            return text

        available = [t for t in _TRANSITION_PHRASES if t not in self._used_transitions]
        if not available:
            self._used_transitions.clear()
            available = list(_TRANSITION_PHRASES)

        chosen = self.rng.choice(available)
        self._used_transitions.add(chosen)

        insert_pos = boundary.start() + 2  # after ". "
        text = text[:insert_pos] + chosen + " " + text[insert_pos:]
        self.stats["transitions_injected"] += 1
        return text

    # ---- Stage 10: Nominalization ----

    def _nominalize(self, text: str) -> str:
        prob = self.aggressiveness * 0.15
        if self.rng.random() > prob:
            return text

        # Pattern: "We <verb>d ..." → "The <noun> of ... was conducted"
        for verb, noun in _NOMINALIZE_MAP.items():
            pattern = re.compile(
                r"\bWe\s+" + re.escape(verb) + r"d\s+(the|a|an|this|these|our)\s+(\w[\w\s]{3,30})",
                re.IGNORECASE,
            )
            match = pattern.search(text)
            if match:
                det = match.group(1)
                obj = match.group(2).strip().rstrip(".,;:")
                replacement = f"The {noun} of {det} {obj} was conducted"
                text = text[:match.start()] + replacement + text[match.end():]
                self.stats["nominalizations"] += 1
                return text

        # Pattern: "<Verb>ing ..." → "The <noun> of ..."
        for verb, noun in _NOMINALIZE_MAP.items():
            cap_verb = verb[0].upper() + verb[1:]
            pattern = re.compile(
                r"\b" + re.escape(cap_verb) + r"ing\s+(the|a|an|this|these)\s+(\w[\w\s]{3,30})",
            )
            match = pattern.search(text)
            if match:
                det = match.group(1)
                obj = match.group(2).strip().rstrip(".,;:")
                replacement = f"The {noun} of {det} {obj}"
                text = text[:match.start()] + replacement + text[match.end():]
                self.stats["nominalizations"] += 1
                return text

        return text

    # ---- Stage 11: Advanced clause reordering ----

    def _reorder_clauses_advanced(self, text: str) -> str:
        prob = self.aggressiveness * 0.2
        if self.rng.random() > prob:
            return text

        match = _CLAUSE_FRONT_RE.match(text)
        if not match:
            return text

        prep = match.group(1).strip().lower()
        prep_obj = match.group(2).strip()
        main_clause = match.group(3).strip()

        # Rebuild with the prepositional phrase moved to the end
        if main_clause and main_clause[-1] in ".!?":
            punctuation = main_clause[-1]
            main_clause = main_clause[:-1].strip()
        else:
            punctuation = "."

        result = main_clause[0].upper() + main_clause[1:] + " " + prep + prep_obj + punctuation
        self.stats["clauses_reordered_adv"] += 1
        return result


def _match_case(original: str, replacement: str) -> str:
    if not original or not replacement:
        return replacement
    if original[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement
