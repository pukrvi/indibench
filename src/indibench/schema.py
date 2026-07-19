"""Dataset schema for IndiBench-Text (design doc §2, decisions D-030/D-031/D-038).

The public artifact is a JSON file per language track:
{"canary": "<canary string>", "examples": [<Item>, ...]}
Provenance is stripped to coarse form before public release (see design §2).
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

MAX_CHOICES = 8  # rendered as letters A–H by the eval harnesses


class Language(str, Enum):
    """The 12 v1 language tracks (D-031). BCP-47-valid tags.

    Code-mixed is one track with two language codes (Hinglish, Tanglish).
    Refresh waves extend toward all 22 scheduled languages (D-017).
    """

    HINDI = "hi"
    BENGALI = "bn"
    TAMIL = "ta"
    TELUGU = "te"
    MARATHI = "mr"
    KANNADA = "kn"
    MALAYALAM = "ml"
    GUJARATI = "gu"
    PUNJABI = "pa"
    ODIA = "or"
    ENGLISH_INDIA = "en-IN"
    HINGLISH = "hi-Latn"
    TANGLISH = "ta-Latn"


class Domain(str, Enum):
    """The 10-domain balanced grid (D-030)."""

    LAW_CONSTITUTION = "law_constitution"
    GOVERNANCE_ADMIN = "governance_admin"
    STEM_INDIA = "stem_india"
    MEDICINE_AYUSH = "medicine_ayush"
    FINANCE_TAX = "finance_tax"
    AGRICULTURE = "agriculture"
    HISTORY_HERITAGE = "history_heritage"
    LITERATURE_ARTS = "literature_arts"
    GEOGRAPHY_ENVIRONMENT = "geography_environment"
    SOCIETY_DAILY_LIFE = "society_daily_life"


# Human-readable display names for presentation surfaces (dashboards, reports).
# The enum VALUES stay canonical in data/CSV/JSON; these are for humans only.
LANGUAGE_NAMES: dict[str, str] = {
    "hi": "Hindi", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
    "mr": "Marathi", "kn": "Kannada", "ml": "Malayalam", "gu": "Gujarati",
    "pa": "Punjabi", "or": "Odia", "en-IN": "English (India)",
    "hi-Latn": "Hinglish", "ta-Latn": "Tanglish",
}
DOMAIN_NAMES: dict[str, str] = {
    "law_constitution": "Law & Constitution",
    "governance_admin": "Governance & Admin",
    "stem_india": "STEM (India)",
    "medicine_ayush": "Medicine & AYUSH",
    "finance_tax": "Finance & Taxation",
    "agriculture": "Agriculture",
    "history_heritage": "History & Heritage",
    "literature_arts": "Literature & Arts",
    "geography_environment": "Geography & Environment",
    "society_daily_life": "Society & Daily Life",
}


class Tag(str, Enum):
    """Cross-cutting reportable slices (D-027 historical, D-038 safety)."""

    HISTORICAL = "historical"
    SAFETY = "safety"


class AnswerType(str, Enum):
    EXACT_MATCH = "exactMatch"
    MULTIPLE_CHOICE = "multipleChoice"


def _validate_mcq(answer_type: "AnswerType", answer: str, choices: list[str] | None) -> None:
    if answer_type is AnswerType.MULTIPLE_CHOICE:
        if not choices:
            raise ValueError("multipleChoice items require choices")
        if len(choices) > MAX_CHOICES:
            raise ValueError(f"at most {MAX_CHOICES} choices (rendered A–H)")
        valid_letters = {chr(ord("A") + i) for i in range(len(choices))}
        if answer not in valid_letters:
            raise ValueError(f"multipleChoice answer must be one of {sorted(valid_letters)}")
    elif choices:
        raise ValueError("exactMatch items must not carry choices")


class DifficultyEvidence(BaseModel):
    """Why an item survived the S3 adversarial filter (D-029/D-035)."""

    models_failed: list[str]
    models_passed: list[str]
    filter_round: str  # e.g. "2026-07"


class Provenance(BaseModel):
    """Generation provenance. Public releases carry only coarse/hashed refs;
    the full form lives in the private pipeline records (design §2)."""

    source_type: str  # textbook | gazette | case_law | syllabus | ...
    source_ref: str  # hashed/coarse public form
    generator_model: str
    verifier_models: list[str]


class Item(BaseModel):
    id: str  # ibt-<lang>-<domain>-<uuid8>
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)  # exactMatch: short answer; multipleChoice: option LETTER ("A".."H")
    answer_type: AnswerType
    choices: list[str] | None = None  # required iff multipleChoice (max 8, rendered A–H)
    language: Language
    script: str  # ISO 15924 (Deva, Beng, Taml, ... ; Latn for romanized code-mix)
    domain: Domain
    tags: list[Tag] = Field(default_factory=list)
    difficulty_evidence: DifficultyEvidence
    provenance: Provenance
    image: str = ""  # reserved for Phase 3 (D-016); always empty in v1

    @model_validator(mode="after")
    def _check_choices(self) -> "Item":
        _validate_mcq(self.answer_type, self.answer, self.choices)
        return self


class DatasetFile(BaseModel):
    """One public data file: canary wrapper + items (D-013, IndicGenBench pattern)."""

    canary: str
    examples: list[Item]


class CandidateDraft(BaseModel):
    """S1 output (D-041): an authored candidate awaiting S2 verification,
    S3 adversarial filtering, and S4 spot-check. Becomes an Item only after
    surviving S3 (which is when difficulty_evidence exists)."""

    id: str | None = None  # assigned at assembly: ibc-<lang>-<domain>-<uuid8>
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)  # exactMatch: short answer; multipleChoice: option LETTER
    answer_type: AnswerType
    choices: list[str] | None = None
    language: Language
    script: str
    domain: Domain
    tags: list[Tag] = Field(default_factory=list)
    generator_model: str = ""
    # S0 assigns this once a candidate is grounded in a registered document.
    # It is deliberately optional for the v0 seed so that the seed remains a
    # review queue, never release-ready material.
    source_document_id: str | None = None
    grounding_note: str  # claimed source basis — verified in S2/S4, never trusted
    review_priority: str = "normal"  # "high" = needs native-speaker review first

    @model_validator(mode="after")
    def _check_choices(self) -> "CandidateDraft":
        _validate_mcq(self.answer_type, self.answer, self.choices)
        return self


class CandidateFile(BaseModel):
    """A canary-wrapped candidate pool file. status makes UNFILTERED explicit
    so candidate files can never be mistaken for a release."""

    canary: str
    status: Literal["candidates-unfiltered"] = "candidates-unfiltered"
    examples: list[CandidateDraft]
