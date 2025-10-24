"""
WHO/WHAT/WHERE/WHEN/WHY Context Dimension Models

This module defines the Pydantic models for all five dimensions of legal context:
- WHO: Parties, judges, attorneys, witnesses
- WHAT: Legal issues, claims, citations, causes of action
- WHERE: Jurisdiction, venue, court information
- WHEN: Timeline, deadlines, case age, urgency
- WHY: Legal reasoning, precedents, argument analysis

All models include case_id as a required field for case-scoped context construction.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid


# ============================================================================
# WHO DIMENSION - Parties, Judges, Attorneys, Witnesses
# ============================================================================

class Party(BaseModel):
    """
    Represents a party in a legal case.

    Attributes:
        id: Unique identifier for the party
        name: Full name of the party
        role: Legal role (plaintiff, defendant, third_party, intervenor)
        entity_type: Type of entity (person, corporation, government_entity)
        case_id: Case this party belongs to (REQUIRED)
        metadata: Additional party information
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str  # plaintiff, defendant, third_party, intervenor
    entity_type: str  # person, corporation, government_entity
    case_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('role')
    def validate_role(cls, v):
        valid_roles = ['plaintiff', 'defendant', 'third_party', 'intervenor',
                       'petitioner', 'respondent', 'appellant', 'appellee']
        if v.lower() not in valid_roles:
            raise ValueError(f"Invalid role: {v}. Must be one of {valid_roles}")
        return v.lower()


class Judge(BaseModel):
    """
    Represents a judge assigned to a case.

    Attributes:
        id: Unique identifier
        name: Judge's full name
        court: Court where judge presides
        case_id: Case this judge is assigned to (REQUIRED)
        assignment_date: Date assigned to case
        history_with_parties: Historical case counts with each party
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    court: str
    case_id: str
    assignment_date: Optional[datetime] = None
    history_with_parties: Dict[str, int] = Field(default_factory=dict)


class Attorney(BaseModel):
    """
    Represents an attorney in a case.

    Attributes:
        id: Unique identifier
        name: Attorney's full name
        firm: Law firm (if applicable)
        bar_number: State bar number
        representing: List of party IDs this attorney represents
        case_id: Case this attorney is involved in (REQUIRED)
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    firm: Optional[str] = None
    bar_number: Optional[str] = None
    representing: List[str] = Field(default_factory=list)
    case_id: str


class Witness(BaseModel):
    """
    Represents a witness in a case.

    Attributes:
        id: Unique identifier
        name: Witness full name
        witness_type: Type (expert, fact, character)
        representing_party: Party ID this witness supports
        case_id: Case this witness is involved in (REQUIRED)
        expertise: Area of expertise (for expert witnesses)
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    witness_type: str  # expert, fact, character
    representing_party: Optional[str] = None
    case_id: str
    expertise: Optional[str] = None


class WhoContext(BaseModel):
    """
    Complete WHO dimension context for a case.

    Contains all parties, judges, attorneys, witnesses, and their relationships.
    """
    case_id: str
    case_name: str
    parties: List[Party] = Field(default_factory=list)
    judges: List[Judge] = Field(default_factory=list)
    attorneys: List[Attorney] = Field(default_factory=list)
    witnesses: List[Witness] = Field(default_factory=list)
    party_relationships: Dict[str, List[str]] = Field(default_factory=dict)
    representation_map: Dict[str, str] = Field(default_factory=dict)  # party_id → attorney_id

    def get_party_count(self) -> int:
        """Get total number of parties"""
        return len(self.parties)

    def get_parties_by_role(self, role: str) -> List[Party]:
        """Get all parties with specific role"""
        return [p for p in self.parties if p.role == role.lower()]


# ============================================================================
# WHAT DIMENSION - Legal Issues, Claims, Citations
# ============================================================================

class Citation(BaseModel):
    """
    Represents a legal citation (statute, case law, regulation).

    Attributes:
        text: Full citation text
        type: Citation type (statute, case_law, regulation)
        jurisdiction: Legal jurisdiction
        confidence: Extraction confidence score (0.0-1.0)
        case_id: Case where this citation appears
    """
    text: str
    type: str  # statute, case_law, regulation
    jurisdiction: str
    confidence: float = Field(ge=0.0, le=1.0)
    case_id: Optional[str] = None

    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class CauseOfAction(BaseModel):
    """
    Represents a cause of action in a case.

    Attributes:
        id: Unique identifier
        name: Name of cause of action
        description: Detailed description
        elements: Legal elements to prove
        case_id: Case containing this cause of action
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    elements: List[str] = Field(default_factory=list)
    case_id: str


class WhatContext(BaseModel):
    """
    Complete WHAT dimension context for a case.

    Contains all legal issues, claims, citations, and causes of action.
    """
    case_id: str
    case_name: str
    causes_of_action: List[CauseOfAction] = Field(default_factory=list)
    legal_issues: List[str] = Field(default_factory=list)
    doctrines: List[str] = Field(default_factory=list)
    statutes: List[Citation] = Field(default_factory=list)
    case_citations: List[Citation] = Field(default_factory=list)
    primary_legal_theory: Optional[str] = None
    issue_complexity: float = Field(default=0.5, ge=0.0, le=1.0)
    jurisdiction_type: str = "federal"  # federal, state, mixed

    def get_statute_count(self) -> int:
        """Get total number of statute citations"""
        return len(self.statutes)

    def get_case_citation_count(self) -> int:
        """Get total number of case citations"""
        return len(self.case_citations)


# ============================================================================
# WHERE DIMENSION - Jurisdiction, Venue, Court
# ============================================================================

class LocalRule(BaseModel):
    """
    Represents a local court rule.

    Attributes:
        rule_number: Rule number/identifier
        description: Rule description
        jurisdiction: Court jurisdiction
    """
    rule_number: str
    description: str
    jurisdiction: str


class WhereContext(BaseModel):
    """
    Complete WHERE dimension context for a case.

    Contains jurisdiction, venue, court information, and local rules.
    """
    case_id: str
    case_name: str
    primary_jurisdiction: str
    court: str
    venue: str
    judge_chambers: Optional[str] = None
    local_rules: List[LocalRule] = Field(default_factory=list)
    filing_requirements: List[str] = Field(default_factory=list)
    related_proceedings: List[Dict[str, Any]] = Field(default_factory=list)

    def get_full_court_name(self) -> str:
        """Get complete court name with jurisdiction"""
        return f"{self.court}, {self.primary_jurisdiction}"


# ============================================================================
# WHEN DIMENSION - Timeline, Deadlines, Case Age
# ============================================================================

class TimelineEvent(BaseModel):
    """
    Represents an event in the case timeline.

    Attributes:
        date: Event date
        event_type: Type of event (filing, hearing, motion, order)
        description: Event description
        case_id: Case this event belongs to
    """
    date: datetime
    event_type: str
    description: str
    case_id: str


class Deadline(BaseModel):
    """
    Represents a case deadline.

    Attributes:
        deadline_date: Date of deadline
        deadline_type: Type (discovery, motion, trial)
        description: Deadline description
        case_id: Case this deadline applies to
        is_met: Whether deadline has been met
        priority: Priority level (high, medium, low)
    """
    deadline_date: datetime
    deadline_type: str
    description: str
    case_id: str
    is_met: bool = False
    priority: str = "medium"  # high, medium, low


class WhenContext(BaseModel):
    """
    Complete WHEN dimension context for a case.

    Contains timeline, deadlines, case age, and urgency metrics.
    """
    case_id: str
    case_name: str
    filing_date: datetime
    incident_date: Optional[datetime] = None
    timeline: List[TimelineEvent] = Field(default_factory=list)
    upcoming_deadlines: List[Deadline] = Field(default_factory=list)
    past_deadlines: List[Deadline] = Field(default_factory=list)
    discovery_cutoff: Optional[datetime] = None
    motion_deadline: Optional[datetime] = None
    trial_date: Optional[datetime] = None
    statute_of_limitations: Optional[datetime] = None
    days_until_next_deadline: Optional[int] = None
    urgency_score: float = Field(default=0.5, ge=0.0, le=1.0)
    case_age_days: int = 0

    def calculate_case_age(self) -> int:
        """Calculate case age in days from filing date"""
        if self.filing_date:
            age = (datetime.now() - self.filing_date).days
            return max(0, age)
        return 0

    def get_next_deadline(self) -> Optional[Deadline]:
        """Get the next upcoming deadline"""
        if not self.upcoming_deadlines:
            return None
        return min(self.upcoming_deadlines, key=lambda d: d.deadline_date)


# ============================================================================
# WHY DIMENSION - Legal Reasoning, Precedents, Arguments
# ============================================================================

class PrecedentAnalysis(BaseModel):
    """
    Represents analysis of a legal precedent.

    Attributes:
        case_name: Name of precedent case
        citation: Full citation
        relevance_score: Relevance to current case (0.0-1.0)
        holding: Legal holding
        distinguishing_factors: Factors that distinguish from current case
        favorability: Whether precedent is favorable (supporting, opposing, neutral)
    """
    case_name: str
    citation: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    holding: str
    distinguishing_factors: List[str] = Field(default_factory=list)
    favorability: str = "neutral"  # supporting, opposing, neutral


class LegalTheory(BaseModel):
    """
    Represents a legal theory for the case.

    Attributes:
        id: Unique identifier
        name: Theory name
        description: Detailed description
        strength: Theory strength (0.0-1.0)
        supporting_precedents: List of supporting precedents
        case_id: Case this theory applies to
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    strength: float = Field(ge=0.0, le=1.0)
    supporting_precedents: List[str] = Field(default_factory=list)
    case_id: str


class WhyContext(BaseModel):
    """
    Complete WHY dimension context for a case.

    Contains legal theories, precedent analysis, arguments, and strategy.
    """
    case_id: str
    case_name: str
    legal_theories: List[LegalTheory] = Field(default_factory=list)
    argument_outline: List[Dict[str, Any]] = Field(default_factory=list)
    supporting_precedents: List[PrecedentAnalysis] = Field(default_factory=list)
    opposing_precedents: List[PrecedentAnalysis] = Field(default_factory=list)
    distinguishing_factors: List[str] = Field(default_factory=list)
    argument_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_factors: List[str] = Field(default_factory=list)
    mitigation_strategies: List[str] = Field(default_factory=list)
    similar_case_outcomes: Dict[str, float] = Field(default_factory=dict)
    judge_ruling_patterns: Dict[str, float] = Field(default_factory=dict)

    def get_supporting_precedent_count(self) -> int:
        """Get count of supporting precedents"""
        return len(self.supporting_precedents)

    def get_average_relevance(self) -> float:
        """Calculate average relevance score of all precedents"""
        all_precedents = self.supporting_precedents + self.opposing_precedents
        if not all_precedents:
            return 0.0
        return sum(p.relevance_score for p in all_precedents) / len(all_precedents)


# ============================================================================
# COMBINED CONTEXT RESPONSE
# ============================================================================

class ContextResponse(BaseModel):
    """
    Complete multi-dimensional context response for a case.

    Combines all five dimensions (WHO/WHAT/WHERE/WHEN/WHY) with metadata
    about context quality, completeness, and execution time.
    """
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    case_name: str
    who: Optional[WhoContext] = None
    what: Optional[WhatContext] = None
    where: Optional[WhereContext] = None
    when: Optional[WhenContext] = None
    why: Optional[WhyContext] = None
    context_score: float = Field(default=0.0, ge=0.0, le=1.0)
    is_complete: bool = False
    cached: bool = False
    execution_time_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

    def get_dimension_count(self) -> int:
        """Get count of populated dimensions"""
        count = 0
        if self.who: count += 1
        if self.what: count += 1
        if self.where: count += 1
        if self.when: count += 1
        if self.why: count += 1
        return count

    def is_dimension_complete(self, dimension: str) -> bool:
        """Check if a specific dimension is populated"""
        dimension_map = {
            'who': self.who,
            'what': self.what,
            'where': self.where,
            'when': self.when,
            'why': self.why
        }
        return dimension_map.get(dimension.lower()) is not None

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for context"""
        return {
            'query_id': self.query_id,
            'case_id': self.case_id,
            'case_name': self.case_name,
            'dimensions_populated': self.get_dimension_count(),
            'context_score': self.context_score,
            'is_complete': self.is_complete,
            'execution_time_ms': self.execution_time_ms,
            'cached': self.cached,
            'who_summary': {
                'parties': len(self.who.parties) if self.who else 0,
                'judges': len(self.who.judges) if self.who else 0,
                'attorneys': len(self.who.attorneys) if self.who else 0
            } if self.who else None,
            'what_summary': {
                'causes_of_action': len(self.what.causes_of_action) if self.what else 0,
                'statutes': len(self.what.statutes) if self.what else 0,
                'case_citations': len(self.what.case_citations) if self.what else 0
            } if self.what else None,
            'when_summary': {
                'timeline_events': len(self.when.timeline) if self.when else 0,
                'upcoming_deadlines': len(self.when.upcoming_deadlines) if self.when else 0,
                'case_age_days': self.when.case_age_days if self.when else 0
            } if self.when else None,
            'why_summary': {
                'legal_theories': len(self.why.legal_theories) if self.why else 0,
                'supporting_precedents': len(self.why.supporting_precedents) if self.why else 0,
                'opposing_precedents': len(self.why.opposing_precedents) if self.why else 0
            } if self.why else None
        }


# ============================================================================
# DIMENSION QUALITY METRICS
# ============================================================================

class DimensionQualityMetrics(BaseModel):
    """
    Quality metrics for a dimension.

    Attributes:
        dimension_name: Name of dimension (WHO/WHAT/WHERE/WHEN/WHY)
        completeness_score: Completeness score (0.0-1.0)
        data_points: Number of data points extracted
        confidence_avg: Average confidence of extracted data
        is_sufficient: Whether dimension meets quality threshold (>= 0.85)
    """
    dimension_name: str
    completeness_score: float = Field(ge=0.0, le=1.0)
    data_points: int
    confidence_avg: float = Field(ge=0.0, le=1.0)
    is_sufficient: bool = False

    @validator('is_sufficient', always=True)
    def validate_sufficiency(cls, v, values):
        """Auto-calculate sufficiency based on completeness score"""
        if 'completeness_score' in values:
            return values['completeness_score'] >= 0.85
        return False
