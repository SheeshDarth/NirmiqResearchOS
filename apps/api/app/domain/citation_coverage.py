import re


def citation_coverage(answer: str) -> dict[str, object]:
    normalized_answer = re.sub(
        r"([.!?])\s+((?:\[\d+\]\s*)+)",
        lambda match: f" {match.group(2).strip()}{match.group(1)} ",
        answer,
    )
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", normalized_answer)
        if _is_claim_like(sentence)
    ]
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
    if len(cleaned.split()) < 4:
        return False
    if cleaned.lower() in {"sources", "answer", "main ideas", "what it is about"}:
        return False
    return True
