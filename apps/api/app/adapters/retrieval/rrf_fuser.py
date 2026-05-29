from typing import Iterable


def fuse_ranked_lists(lists: Iterable[list[str]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranked in lists:
        for rank, item in enumerate(ranked):
            scores[item] = scores.get(item, 0.0) + (1.0 / (k + rank + 1))
    return [item for item, _ in sorted(scores.items(), key=lambda pair: pair[1], reverse=True)]


def fuse_ranked_lists_with_scores(
    lists: Iterable[list[str]], k: int = 60
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranked in lists:
        for rank, item in enumerate(ranked):
            scores[item] = scores.get(item, 0.0) + (1.0 / (k + rank + 1))
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
