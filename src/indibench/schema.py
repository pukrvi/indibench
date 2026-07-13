"""Dataset schema for IndiBench-Text (design doc §2, decisions D-030/D-031/D-038).

The public artifact is a JSON file per language track:
{"canary": "<canary string>", "examples": [<Item>, ...]}
Provenance is stripped to coarse form before public release (see design §2).
"""

from enum import Enum

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


class Tag(str, Enum):
    """Cross-cutting reportable slices (D-027 historical, D-038 safety)."""

    HISTORICAL = "historical"
    SAFETY = "safety"


class AnswerType(str, Enum):
    EXACT_MATCH = "exactMatch"
    MULTIPLE_CHOICE = "multipleChoice"


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
    question: str
    answer: str  # exactMatch: the short answer; multipleChoice: the option LETTER ("A".."H")
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
        if self.answer_type is AnswerType.MULTIPLE_CHOICE:
            if not self.choices:
                raise ValueError("multipleChoice items require choices")
            if len(self.choices) > MAX_CHOICES:
                raise ValueError(f"at most {MAX_CHOICES} choices (rendered A–H)")
            valid_letters = {chr(ord("A") + i) for i in range(len(self.choices))}
            if self.answer not in valid_letters:
                raise ValueError(f"multipleChoice answer must be one of {sorted(valid_letters)}")
        elif self.choices:
            raise ValueError("exactMatch items must not carry choices")
        return self


class DatasetFile(BaseModel):
    """One public data file: canary wrapper + items (D-013, IndicGenBench pattern)."""

    canary: str
    examples: list[Item]
