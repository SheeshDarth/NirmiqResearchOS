import re


def citation_coverage(answer: str) -> dict[str, object]:
    normalized_answer = re.sub(
        r"([.!?])[ \t]+((?:\[\d+\][ \t]*)+)",
        lambda match: f" {match.group(2).strip()}{match.group(1)} ",
        answer,
    )
    sentences: list[str] = []
    for line in normalized_answer.splitlines():
        if _is_structural_line(line):
            continue
        sentences.extend(
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", line)
            if _is_claim_like(sentence)
        )
    if not sentences:
        return {
            "citation_coverage": 0.0,
            "citation_sentence_count": 0,
            "citation_anchor_count": 0,
        }

    cited_sentences = [sentence for sentence in sentences if re.search(r"\[\d+\]", sentence)]
    anchor_count = len(re.findall(r"\[\d+\]", normalized_answer))
    return {
        "citation_coverage": round(len(cited_sentences) / len(sentences), 3),
        "citation_sentence_count": len(sentences),
        "citation_anchor_count": anchor_count,
    }


def _is_claim_like(sentence: str) -> bool:
    cleaned = re.sub(r"\[\d+\]", "", sentence).strip(" -*:")
    lowered = cleaned.lower()
    if len(cleaned.split()) < 4:
        return False
    if lowered in {
        "sources",
        "answer",
        "main ideas",
        "what it is about",
        "direct answer",
        "key points",
        "evidence note",
        "equation or reason from the source",
        "exam-ready answer",
        "source note",
        "steps from the source",
        "useful caveats / details",
        "diagram note",
    }:
        return False
    if lowered.startswith(
        (
            "document summary from",
            "exam-ready answer",
            "study guide from",
            "if you want",
            "open sources",
            "source note",
            "evidence note open sources",
            "equation or reason from the source",
            "exam-ready answer",
            "important questions",
            "steps from the source",
            "where this came from",
            "why this matters",
            "study takeaway",
            "trust note",
            "diagram note",
            "source diagram",
            "source diagrams",
            "no source diagram",
            "the retrieved passages did not contain enough",
        )
    ):
        return False
    if re.match(r"^q\d+\.", lowered):
        return False
    if re.match(r"^d\d+:\s*(source diagram|page|figure|diagram)", lowered):
        return False
    return True


def _is_structural_line(line: str) -> bool:
    lowered = re.sub(r"\s+", " ", line.strip().lower())
    if not lowered:
        return True
    if lowered.startswith("#"):
        return True
    if re.match(r"^q\d+\.", lowered):
        return True
    if lowered.startswith(
        (
            "document summary from",
            "study guide from",
            "source diagrams",
        )
    ):
        return True
    return False
