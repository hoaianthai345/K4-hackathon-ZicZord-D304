import unicodedata

from .schemas import Lecture
from .seed import LECTURES


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def all_lectures() -> list[Lecture]:
    return [Lecture.model_validate(item) for item in LECTURES]


def retrieve_lectures(query: str, limit: int = 2) -> list[Lecture]:
    normalized_query = normalize(query)
    stopwords = {
        "ban",
        "cach",
        "cho",
        "con",
        "minh",
        "mot",
        "nhung",
        "the",
        "van",
        "voi",
    }
    terms = {
        term
        for term in normalized_query.split()
        if len(term) > 3 and term not in stopwords
    }
    scored: list[tuple[int, Lecture]] = []

    for lecture in all_lectures():
        searchable = normalize(
            " ".join([lecture.title, lecture.module, lecture.content, *lecture.keywords])
        )
        score = sum(2 if normalize(keyword) in normalized_query else 0 for keyword in lecture.keywords)
        score += sum(1 for term in terms if term in searchable)
        scored.append((score, lecture))

    scored.sort(key=lambda item: item[0], reverse=True)
    matches = [lecture for score, lecture in scored if score >= 2]
    return (matches or [all_lectures()[1]])[:limit]
