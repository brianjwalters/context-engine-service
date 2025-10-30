# Context Engine Dimension Reference

**Complete Guide to the WHO/WHAT/WHERE/WHEN/WHY Framework**

---

## Table of Contents

- [Overview](#overview)
- [WHO Dimension](#who-dimension)
- [WHAT Dimension](#what-dimension)
- [WHERE Dimension](#where-dimension)
- [WHEN Dimension](#when-dimension)
- [WHY Dimension](#why-dimension)
- [Dimension Interactions](#dimension-interactions)
- [Scope Levels](#scope-levels)
- [Quality Scoring](#quality-scoring)
- [Performance Optimization](#performance-optimization)
- [Best Practices](#best-practices)

---

## Overview

The Context Engine uses a **5-dimensional framework** to construct comprehensive legal context for case-based work. Each dimension answers a fundamental question about the case, and together they provide complete context for intelligent document generation.

### The Five Dimensions

| Dimension | Question | Primary Data | Use Cases |
|-----------|----------|--------------|-----------|
| **WHO** | Who are the parties? | Parties, judges, attorneys, witnesses | Party identification, representation mapping |
| **WHAT** | What is this case about? | Legal issues, causes of action, citations | Issue spotting, legal research |
| **WHERE** | Where is this being litigated? | Jurisdiction, court, venue | Procedural rules, filing requirements |
| **WHEN** | When are the deadlines? | Timeline, deadlines, case age | Urgency assessment, scheduling |
| **WHY** | Why will this succeed/fail? | Precedents, legal theories, arguments | Strategy, prediction, brief writing |

### Framework Philosophy

The WHO/WHAT/WHERE/WHEN/WHY framework is designed around **case-centric context construction**:

1. **Case-Scoped**: All queries require a `case_id` - 99% of legal work is case-specific
2. **Multi-Dimensional**: Each dimension provides different lens on same case
3. **Parallel Processing**: Dimensions analyzed concurrently for performance
4. **Quality-Driven**: Each dimension scored individually and collectively
5. **Graceful Degradation**: Missing data in one dimension doesn't fail entire context

---

## WHO Dimension

### Purpose

The WHO dimension identifies **all people and entities involved** in the case, along with their roles, relationships, and representation.

### Data Extracted

#### Parties
- **Plaintiffs**: Individuals or entities bringing the claim
- **Defendants**: Individuals or entities being sued
- **Third Parties**: Cross-defendants, intervenors, amici
- **Organizations**: Corporations, government entities, non-profits

#### Legal Representatives
- **Attorneys**: Lead counsel, co-counsel, local counsel
- **Law Firms**: Firm affiliations and partnerships
- **Bar Numbers**: State bar registrations
- **Representation Map**: Which attorneys represent which parties

#### Judicial Officers
- **Judges**: Assigned judge(s) for the case
- **Magistrates**: Assigned magistrate judges
- **Special Masters**: Court-appointed special masters
- **Historical Data**: Judge's history with parties/attorneys

#### Witnesses
- **Fact Witnesses**: Individuals with direct knowledge
- **Expert Witnesses**: Technical, scientific, medical experts
- **Character Witnesses**: Reputation and character testimony
- **Expertise Areas**: Fields of specialization for experts

### Data Model

```python
class WhoContext(BaseModel):
    case_id: str
    case_name: str
    parties: List[Party]
    judges: List[Judge]
    attorneys: List[Attorney]
    witnesses: List[Witness]
    party_relationships: Dict[str, List[str]]  # opposing parties, co-parties
    representation_map: Dict[str, str]  # party_id → attorney_id
```

### Extraction Strategy

```python
# Pseudocode for WHO dimension analysis
async def analyze_who_dimension(client_id: str, case_id: str):
    # 1. Query GraphRAG for entity relationships
    graph_query = """
    FIND entities WHERE case_id = {case_id}
    AND entity_type IN ['PARTY', 'JUDGE', 'ATTORNEY', 'WITNESS']
    WITH relationships ['REPRESENTS', 'OPPOSES', 'CO-PARTY_WITH']
    """
    graph_entities = await graphrag_client.query(graph_query)

    # 2. Query Supabase for structured entity data
    supabase_entities = await supabase_client.schema('client').table('entities') \
        .select('*') \
        .eq('case_id', case_id) \
        .in_('entity_type', ['PARTY', 'JUDGE', 'ATTORNEY', 'WITNESS']) \
        .execute()

    # 3. Merge and deduplicate entities
    merged_entities = merge_entities(graph_entities, supabase_entities)

    # 4. Build relationship graph
    relationships = build_relationship_graph(merged_entities)

    # 5. Construct WHO context
    return WhoContext(
        case_id=case_id,
        parties=extract_parties(merged_entities),
        judges=extract_judges(merged_entities),
        attorneys=extract_attorneys(merged_entities),
        witnesses=extract_witnesses(merged_entities),
        party_relationships=relationships,
        representation_map=build_representation_map(merged_entities)
    )
```

### Quality Scoring

```python
def score_who_dimension(who_context: WhoContext) -> float:
    """
    Score WHO dimension quality (0.0-1.0)

    Scoring factors:
    - Parties: At least 2 parties (plaintiff + defendant) = 0.3
    - Attorneys: At least 1 attorney per party = 0.2
    - Judges: Assigned judge identified = 0.2
    - Witnesses: Witnesses identified = 0.1
    - Relationships: Representation map complete = 0.2
    """
    score = 0.0

    # Parties (30% weight)
    if len(who_context.parties) >= 2:
        score += 0.3
    elif len(who_context.parties) >= 1:
        score += 0.15

    # Attorneys (20% weight)
    parties_with_counsel = sum(
        1 for party in who_context.parties
        if party.id in who_context.representation_map
    )
    if parties_with_counsel >= len(who_context.parties):
        score += 0.2
    else:
        score += 0.2 * (parties_with_counsel / len(who_context.parties))

    # Judges (20% weight)
    if len(who_context.judges) >= 1:
        score += 0.2

    # Witnesses (10% weight)
    if len(who_context.witnesses) >= 3:
        score += 0.1
    elif len(who_context.witnesses) >= 1:
        score += 0.05

    # Relationships (20% weight)
    if who_context.party_relationships:
        score += 0.2

    return min(1.0, score)
```

### Usage Examples

**Python Example - Retrieve WHO Dimension:**
```python
import httpx

async def get_who_context(client_id: str, case_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://10.10.0.87:8015/api/v1/context/dimension/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "dimension": "WHO"
            }
        )
        who_data = response.json()["data"]

        # Analyze parties
        print(f"Parties: {len(who_data['parties'])}")
        for party in who_data["parties"]:
            print(f"  - {party['name']} ({party['role']})")

        # Check representation
        print(f"\nAttorneys: {len(who_data['attorneys'])}")
        for attorney in who_data["attorneys"]:
            representing = ", ".join(attorney["representing"])
            print(f"  - {attorney['name']} representing: {representing}")

        return who_data

# Usage
who_context = await get_who_context("client-abc", "case-123")
```

**TypeScript Example - Analyze Party Network:**
```typescript
async function analyzePartyNetwork(clientId: string, caseId: string) {
    const response = await fetch('http://10.10.0.87:8015/api/v1/context/dimension/retrieve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            client_id: clientId,
            case_id: caseId,
            dimension: 'WHO'
        })
    });

    const { data: whoData } = await response.json();

    // Build network graph
    const network = {
        nodes: [
            ...whoData.parties.map(p => ({ id: p.id, label: p.name, type: 'party' })),
            ...whoData.attorneys.map(a => ({ id: a.id, label: a.name, type: 'attorney' })),
            ...whoData.judges.map(j => ({ id: j.id, label: j.name, type: 'judge' }))
        ],
        edges: Object.entries(whoData.representation_map).map(([partyId, attorneyId]) => ({
            from: attorneyId,
            to: partyId,
            label: 'represents'
        }))
    };

    console.log('Party Network:', network);
    return network;
}
```

---

## WHAT Dimension

### Purpose

The WHAT dimension identifies **what the case is about** - the legal issues, causes of action, claims, defenses, and relevant legal citations.

### Data Extracted

#### Legal Issues
- **Core Disputes**: Central questions of law or fact
- **Subsidiary Issues**: Related or dependent issues
- **Threshold Issues**: Jurisdiction, standing, ripeness
- **Issue Complexity**: Estimated complexity score (0.0-1.0)

#### Causes of Action
- **Primary Claims**: Main legal theories being pursued
- **Alternative Claims**: Backup or alternative theories
- **Elements**: Required elements to prove each claim
- **Legal Standards**: Applicable burden of proof

#### Citations
- **Statutes**: Federal and state statutory citations
- **Regulations**: Administrative regulations
- **Case Law**: Precedential case citations
- **Constitutional Provisions**: U.S. Constitution, state constitutions

#### Legal Doctrines
- **Substantive Doctrines**: Contract law, tort law, property law
- **Procedural Doctrines**: Standing, mootness, res judicata
- **Equitable Doctrines**: Estoppel, laches, unclean hands

### Data Model

```python
class WhatContext(BaseModel):
    case_id: str
    case_name: str
    causes_of_action: List[CauseOfAction]
    legal_issues: List[str]
    doctrines: List[str]
    statutes: List[Citation]
    case_citations: List[Citation]
    primary_legal_theory: Optional[str]
    issue_complexity: float  # 0.0-1.0
    jurisdiction_type: str  # federal, state, mixed
```

### Extraction Strategy

```python
async def analyze_what_dimension(client_id: str, case_id: str):
    # 1. Extract entities from document text
    entity_response = await entity_extraction_client.extract(
        case_id=case_id,
        entity_types=[
            'STATUTE_CITATION',
            'CASE_CITATION',
            'LEGAL_ISSUE',
            'CAUSE_OF_ACTION',
            'LEGAL_DOCTRINE'
        ]
    )

    # 2. Query GraphRAG for citation network
    citation_network = await graphrag_client.query(
        query=f"Find all legal citations in case {case_id} with their relationships"
    )

    # 3. Analyze issue complexity using LLM
    complexity_analysis = await prompt_service.complete(
        prompt=f"""
        Analyze the legal complexity of this case:
        Issues: {entity_response.legal_issues}
        Citations: {len(entity_response.citations)}

        Rate complexity on 0.0-1.0 scale where:
        0.0-0.3: Simple (single issue, clear law)
        0.4-0.6: Moderate (multiple issues, some ambiguity)
        0.7-1.0: Complex (novel issues, conflicting precedents)

        Return JSON: {{"complexity": 0.X, "reasoning": "..."}}
        """
    )

    # 4. Build WHAT context
    return WhatContext(
        case_id=case_id,
        causes_of_action=extract_causes(entity_response),
        legal_issues=entity_response.legal_issues,
        statutes=filter_citations(entity_response, type='statute'),
        case_citations=filter_citations(entity_response, type='case_law'),
        issue_complexity=complexity_analysis['complexity']
    )
```

### Quality Scoring

```python
def score_what_dimension(what_context: WhatContext) -> float:
    """
    Score WHAT dimension quality (0.0-1.0)

    Scoring factors:
    - Legal issues identified = 0.25
    - Causes of action = 0.25
    - Citations (statutes + cases) = 0.30
    - Primary legal theory = 0.20
    """
    score = 0.0

    # Legal issues (25%)
    if len(what_context.legal_issues) >= 3:
        score += 0.25
    elif len(what_context.legal_issues) >= 1:
        score += 0.25 * (len(what_context.legal_issues) / 3)

    # Causes of action (25%)
    if len(what_context.causes_of_action) >= 1:
        score += 0.25

    # Citations (30%)
    total_citations = len(what_context.statutes) + len(what_context.case_citations)
    if total_citations >= 10:
        score += 0.30
    elif total_citations >= 1:
        score += 0.30 * (total_citations / 10)

    # Primary legal theory (20%)
    if what_context.primary_legal_theory:
        score += 0.20

    return min(1.0, score)
```

### Usage Examples

**Python Example - Analyze Legal Issues:**
```python
async def analyze_legal_issues(client_id: str, case_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://10.10.0.87:8015/api/v1/context/dimension/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "dimension": "WHAT"
            }
        )
        what_data = response.json()["data"]

        print(f"Legal Issues ({len(what_data['legal_issues'])}):")
        for issue in what_data["legal_issues"]:
            print(f"  - {issue}")

        print(f"\nCauses of Action ({len(what_data['causes_of_action'])}):")
        for coa in what_data["causes_of_action"]:
            print(f"  - {coa['name']}: {coa['description']}")
            print(f"    Elements: {', '.join(coa['elements'])}")

        print(f"\nCitations:")
        print(f"  Statutes: {len(what_data['statutes'])}")
        print(f"  Case Law: {len(what_data['case_citations'])}")

        print(f"\nComplexity: {what_data['issue_complexity']:.2f}")

        return what_data
```

**TypeScript Example - Build Citation Map:**
```typescript
async function buildCitationMap(clientId: string, caseId: string) {
    const response = await fetch('http://10.10.0.87:8015/api/v1/context/dimension/retrieve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            client_id: clientId,
            case_id: caseId,
            dimension: 'WHAT'
        })
    });

    const { data: whatData } = await response.json();

    // Organize citations by type and jurisdiction
    const citationMap = {
        federal: {
            statutes: whatData.statutes.filter(c => c.jurisdiction === 'federal'),
            cases: whatData.case_citations.filter(c => c.jurisdiction === 'federal')
        },
        state: {
            statutes: whatData.statutes.filter(c => c.jurisdiction !== 'federal'),
            cases: whatData.case_citations.filter(c => c.jurisdiction !== 'federal')
        },
        highConfidence: [
            ...whatData.statutes,
            ...whatData.case_citations
        ].filter(c => c.confidence >= 0.9)
    };

    console.log('Citation Map:', citationMap);
    return citationMap;
}
```

---

## WHERE Dimension

### Purpose

The WHERE dimension determines **where the case is being litigated** - jurisdiction, venue, court level, and applicable local rules.

### Data Extracted

#### Jurisdiction
- **Primary Jurisdiction**: Federal, state, or mixed
- **Subject Matter Jurisdiction**: Diversity, federal question, supplemental
- **Personal Jurisdiction**: Minimum contacts, general/specific
- **Jurisdiction Type**: Original, appellate, removal

#### Court Information
- **Court Name**: Full official court name
- **Court Level**: District, circuit, appellate, supreme
- **Division**: Geographic division within district
- **Judge Chambers**: Physical location of assigned judge

#### Venue
- **Venue District**: Proper venue under 28 U.S.C. § 1391
- **Venue Factors**: Where claim arose, where parties reside
- **Transfer Issues**: Forum non conveniens, transfer motions

#### Local Rules
- **Local Court Rules**: Specific procedural requirements
- **Standing Orders**: Judge-specific procedures
- **Filing Requirements**: Electronic filing, paper format
- **Page Limits**: Motion page limits, brief limits

### Data Model

```python
class WhereContext(BaseModel):
    case_id: str
    case_name: str
    primary_jurisdiction: str  # federal, state, tribal
    court: str  # Full court name
    venue: str  # District/county
    judge_chambers: Optional[str]
    local_rules: List[LocalRule]
    filing_requirements: List[str]
    related_proceedings: List[Dict[str, Any]]
```

### Extraction Strategy

```python
async def analyze_where_dimension(client_id: str, case_id: str):
    # 1. Extract court information from case caption
    court_entities = await entity_extraction_client.extract(
        case_id=case_id,
        entity_types=['COURT', 'JURISDICTION', 'VENUE']
    )

    # 2. Query GraphRAG for related proceedings
    related_cases = await graphrag_client.query(
        query=f"""
        Find cases related to {case_id} by:
        - Same parties
        - Consolidated proceedings
        - Transfer history
        """
    )

    # 3. Lookup local rules from court database
    court_name = court_entities.court_name
    local_rules = await lookup_local_rules(court_name)

    # 4. Build WHERE context
    return WhereContext(
        case_id=case_id,
        primary_jurisdiction=determine_jurisdiction(court_entities),
        court=court_name,
        venue=court_entities.venue,
        local_rules=local_rules,
        related_proceedings=related_cases
    )
```

### Quality Scoring

```python
def score_where_dimension(where_context: WhereContext) -> float:
    """
    Score WHERE dimension quality (0.0-1.0)

    WHERE is typically binary - either we know the court or we don't.

    Scoring factors:
    - Primary jurisdiction identified = 0.33
    - Court identified = 0.33
    - Venue identified = 0.34
    """
    score = 0.0

    if where_context.primary_jurisdiction:
        score += 0.33

    if where_context.court:
        score += 0.33

    if where_context.venue:
        score += 0.34

    return score
```

### Usage Examples

**Python Example - Get Filing Requirements:**
```python
async def get_filing_requirements(client_id: str, case_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://10.10.0.87:8015/api/v1/context/dimension/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "dimension": "WHERE"
            }
        )
        where_data = response.json()["data"]

        print(f"Court: {where_data['court']}")
        print(f"Jurisdiction: {where_data['primary_jurisdiction']}")
        print(f"Venue: {where_data['venue']}")

        print(f"\nLocal Rules ({len(where_data['local_rules'])}):")
        for rule in where_data["local_rules"]:
            print(f"  - {rule['rule_number']}: {rule['description']}")

        print(f"\nFiling Requirements:")
        for req in where_data["filing_requirements"]:
            print(f"  - {req}")

        return where_data
```

**TypeScript Example - Check Jurisdiction:**
```typescript
async function checkJurisdiction(clientId: string, caseId: string) {
    const response = await fetch('http://10.10.0.87:8015/api/v1/context/dimension/retrieve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            client_id: clientId,
            case_id: caseId,
            dimension: 'WHERE'
        })
    });

    const { data: whereData } = await response.json();

    const jurisdictionInfo = {
        type: whereData.primary_jurisdiction,
        court: whereData.court,
        venue: whereData.venue,
        isFederal: whereData.primary_jurisdiction === 'federal',
        fullCourtName: whereData.get_full_court_name
            ? whereData.get_full_court_name()
            : `${whereData.court}, ${whereData.primary_jurisdiction}`
    };

    console.log('Jurisdiction:', jurisdictionInfo);
    return jurisdictionInfo;
}
```

---

## WHEN Dimension

### Purpose

The WHEN dimension tracks **temporal aspects** of the case - timeline of events, deadlines, case age, and urgency.

### Data Extracted

#### Case Timeline
- **Filing Date**: Original complaint filing
- **Incident Date**: Date(s) of underlying events
- **Timeline Events**: Motions filed, hearings held, orders entered
- **Case Age**: Days since filing

#### Deadlines
- **Discovery Deadlines**: Interrogatory responses, document production
- **Motion Deadlines**: Motion to dismiss, summary judgment
- **Trial Date**: Scheduled trial date
- **Statute of Limitations**: Applicable limitations period

#### Urgency Metrics
- **Days Until Next Deadline**: Countdown to nearest deadline
- **Urgency Score**: Computed urgency (0.0-1.0) based on deadlines
- **Overdue Deadlines**: Deadlines that have passed

### Data Model

```python
class WhenContext(BaseModel):
    case_id: str
    case_name: str
    filing_date: datetime
    incident_date: Optional[datetime]
    timeline: List[TimelineEvent]
    upcoming_deadlines: List[Deadline]
    past_deadlines: List[Deadline]
    discovery_cutoff: Optional[datetime]
    motion_deadline: Optional[datetime]
    trial_date: Optional[datetime]
    statute_of_limitations: Optional[datetime]
    days_until_next_deadline: Optional[int]
    urgency_score: float  # 0.0-1.0
    case_age_days: int
```

### Extraction Strategy

```python
async def analyze_when_dimension(client_id: str, case_id: str):
    # 1. Extract date entities from documents
    date_entities = await entity_extraction_client.extract(
        case_id=case_id,
        entity_types=['DATE', 'DEADLINE', 'TIMELINE_EVENT']
    )

    # 2. Query docket for filing history
    docket = await query_docket(case_id)

    # 3. Build timeline from events
    timeline = build_timeline(date_entities, docket)

    # 4. Identify upcoming deadlines
    now = datetime.now()
    upcoming = [d for d in timeline.deadlines if d.deadline_date > now]
    past = [d for d in timeline.deadlines if d.deadline_date <= now]

    # 5. Calculate urgency score
    urgency = calculate_urgency(upcoming, past, filing_date=docket.filing_date)

    # 6. Build WHEN context
    return WhenContext(
        case_id=case_id,
        filing_date=docket.filing_date,
        timeline=timeline.events,
        upcoming_deadlines=sorted(upcoming, key=lambda d: d.deadline_date),
        past_deadlines=past,
        urgency_score=urgency,
        case_age_days=(now - docket.filing_date).days,
        days_until_next_deadline=(upcoming[0].deadline_date - now).days if upcoming else None
    )

def calculate_urgency(upcoming, past, filing_date):
    """
    Calculate urgency score (0.0-1.0)

    Factors:
    - Days until next deadline (< 7 days = high urgency)
    - Number of upcoming deadlines
    - Overdue deadlines
    - Case age (older cases = higher urgency)
    """
    score = 0.0

    # Next deadline urgency
    if upcoming:
        days_until = (upcoming[0].deadline_date - datetime.now()).days
        if days_until <= 3:
            score += 0.4
        elif days_until <= 7:
            score += 0.3
        elif days_until <= 14:
            score += 0.2
        elif days_until <= 30:
            score += 0.1

    # Overdue deadlines
    if past:
        overdue_count = sum(1 for d in past if not d.is_met)
        score += min(0.3, overdue_count * 0.1)

    # Case age (older = more urgent)
    case_age_days = (datetime.now() - filing_date).days
    if case_age_days > 365:
        score += 0.2
    elif case_age_days > 180:
        score += 0.1

    # Deadline density (many deadlines = higher urgency)
    if len(upcoming) > 5:
        score += 0.1

    return min(1.0, score)
```

### Quality Scoring

```python
def score_when_dimension(when_context: WhenContext) -> float:
    """
    Score WHEN dimension quality (0.0-1.0)

    Scoring factors:
    - Filing date identified = 0.30
    - Timeline events = 0.30
    - Deadlines tracked = 0.40
    """
    score = 0.0

    # Filing date (30%)
    if when_context.filing_date:
        score += 0.30

    # Timeline events (30%)
    event_count = len(when_context.timeline)
    if event_count >= 10:
        score += 0.30
    elif event_count >= 1:
        score += 0.30 * (event_count / 10)

    # Deadlines (40%)
    total_deadlines = len(when_context.upcoming_deadlines) + len(when_context.past_deadlines)
    if total_deadlines >= 5:
        score += 0.40
    elif total_deadlines >= 1:
        score += 0.40 * (total_deadlines / 5)

    return min(1.0, score)
```

### Usage Examples

**Python Example - Monitor Deadlines:**
```python
async def monitor_deadlines(client_id: str, case_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://10.10.0.87:8015/api/v1/context/dimension/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "dimension": "WHEN"
            }
        )
        when_data = response.json()["data"]

        print(f"Case Age: {when_data['case_age_days']} days")
        print(f"Urgency Score: {when_data['urgency_score']:.2f}")

        if when_data["days_until_next_deadline"]:
            print(f"\nNext Deadline: {when_data['days_until_next_deadline']} days")

        print(f"\nUpcoming Deadlines ({len(when_data['upcoming_deadlines'])}):")
        for deadline in when_data["upcoming_deadlines"][:5]:  # First 5
            days_away = (datetime.fromisoformat(deadline['deadline_date']) - datetime.now()).days
            priority = deadline['priority']
            print(f"  [{priority.upper()}] {deadline['description']} - {days_away} days")

        # Alert on high urgency
        if when_data["urgency_score"] > 0.7:
            print("\n⚠️  HIGH URGENCY CASE")

        return when_data
```

**TypeScript Example - Build Timeline Visualization:**
```typescript
async function buildTimelineVisualization(clientId: string, caseId: string) {
    const response = await fetch('http://10.10.0.87:8015/api/v1/context/dimension/retrieve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            client_id: clientId,
            case_id: caseId,
            dimension: 'WHEN'
        })
    });

    const { data: whenData } = await response.json();

    // Convert to timeline visualization format
    const timeline = {
        filing: new Date(whenData.filing_date),
        events: whenData.timeline.map(event => ({
            date: new Date(event.date),
            type: event.event_type,
            description: event.description
        })),
        deadlines: {
            upcoming: whenData.upcoming_deadlines.map(d => ({
                date: new Date(d.deadline_date),
                description: d.description,
                priority: d.priority,
                daysAway: Math.floor(
                    (new Date(d.deadline_date) - new Date()) / (1000 * 60 * 60 * 24)
                )
            })),
            past: whenData.past_deadlines.map(d => ({
                date: new Date(d.deadline_date),
                description: d.description,
                wasMet: d.is_met
            }))
        },
        metrics: {
            caseAgeDays: whenData.case_age_days,
            urgency: whenData.urgency_score,
            nextDeadlineDays: whenData.days_until_next_deadline
        }
    };

    console.log('Timeline:', timeline);
    return timeline;
}
```

---

## WHY Dimension

### Purpose

The WHY dimension analyzes **why the case will succeed or fail** - legal theories, precedents, arguments, and strategic considerations.

### Data Extracted

#### Legal Theories
- **Primary Theory**: Main legal argument
- **Alternative Theories**: Backup legal positions
- **Theory Strength**: Estimated probability of success
- **Supporting Authority**: Cases/statutes supporting theory

#### Precedent Analysis
- **Supporting Precedents**: Cases favoring client's position
- **Opposing Precedents**: Cases favoring opponent
- **Distinguishing Factors**: How to distinguish unfavorable precedents
- **Relevance Scores**: How relevant each precedent is (0.0-1.0)

#### Strategic Analysis
- **Argument Strength**: Overall argument strength (0.0-1.0)
- **Risk Factors**: Potential weaknesses in position
- **Mitigation Strategies**: How to address weaknesses
- **Judge Ruling Patterns**: Historical rulings by assigned judge

#### Predictive Insights
- **Similar Case Outcomes**: Outcomes in similar cases
- **Success Probability**: Estimated win probability
- **Settlement Value**: Estimated settlement range

### Data Model

```python
class WhyContext(BaseModel):
    case_id: str
    case_name: str
    legal_theories: List[LegalTheory]
    argument_outline: List[Dict[str, Any]]
    supporting_precedents: List[PrecedentAnalysis]
    opposing_precedents: List[PrecedentAnalysis]
    distinguishing_factors: List[str]
    argument_strength: float  # 0.0-1.0
    risk_factors: List[str]
    mitigation_strategies: List[str]
    similar_case_outcomes: Dict[str, float]  # outcome → probability
    judge_ruling_patterns: Dict[str, float]  # issue → ruling rate
```

### Extraction Strategy

```python
async def analyze_why_dimension(client_id: str, case_id: str):
    # 1. Query GraphRAG for precedent network
    precedents = await graphrag_client.query(
        query=f"""
        Find precedents cited in {case_id} or relevant to its legal issues.
        Include:
        - Citation relationship strength
        - Favorable vs. opposing
        - Jurisdiction
        - Holding
        """
    )

    # 2. Use LLM to analyze argument strength
    legal_analysis = await prompt_service.complete(
        prompt=f"""
        Analyze the legal arguments for case {case_id}:

        Legal Issues: {legal_issues}
        Supporting Precedents: {supporting_precedents}
        Opposing Precedents: {opposing_precedents}

        Provide:
        1. Argument strength score (0.0-1.0)
        2. Key risk factors
        3. Mitigation strategies
        4. Distinguishing factors for opposing precedents

        Return JSON format.
        """,
        model="qwen3-vl-thinking-256k"  # Use thinking model for analysis
    )

    # 3. Query historical judge rulings
    judge_patterns = await query_judge_rulings(
        judge_name=assigned_judge,
        legal_issues=legal_issues
    )

    # 4. Find similar case outcomes
    similar_outcomes = await find_similar_cases(
        legal_issues=legal_issues,
        jurisdiction=jurisdiction
    )

    # 5. Build WHY context
    return WhyContext(
        case_id=case_id,
        legal_theories=extract_theories(legal_analysis),
        supporting_precedents=filter_precedents(precedents, favorable=True),
        opposing_precedents=filter_precedents(precedents, favorable=False),
        argument_strength=legal_analysis['strength'],
        risk_factors=legal_analysis['risks'],
        mitigation_strategies=legal_analysis['mitigations'],
        judge_ruling_patterns=judge_patterns,
        similar_case_outcomes=similar_outcomes
    )
```

### Quality Scoring

```python
def score_why_dimension(why_context: WhyContext) -> float:
    """
    Score WHY dimension quality (0.0-1.0)

    Scoring factors:
    - Legal theories = 0.20
    - Supporting precedents = 0.30
    - Risk analysis = 0.20
    - Judge patterns = 0.15
    - Similar outcomes = 0.15
    """
    score = 0.0

    # Legal theories (20%)
    if len(why_context.legal_theories) >= 2:
        score += 0.20
    elif len(why_context.legal_theories) >= 1:
        score += 0.10

    # Supporting precedents (30%)
    precedent_count = len(why_context.supporting_precedents)
    if precedent_count >= 10:
        score += 0.30
    elif precedent_count >= 1:
        score += 0.30 * (precedent_count / 10)

    # Risk analysis (20%)
    if why_context.risk_factors and why_context.mitigation_strategies:
        score += 0.20
    elif why_context.risk_factors or why_context.mitigation_strategies:
        score += 0.10

    # Judge patterns (15%)
    if why_context.judge_ruling_patterns:
        score += 0.15

    # Similar outcomes (15%)
    if why_context.similar_case_outcomes:
        score += 0.15

    return min(1.0, score)
```

### Usage Examples

**Python Example - Strategic Analysis:**
```python
async def perform_strategic_analysis(client_id: str, case_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://10.10.0.87:8015/api/v1/context/dimension/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "dimension": "WHY"
            }
        )
        why_data = response.json()["data"]

        print(f"Argument Strength: {why_data['argument_strength']:.1%}")

        print(f"\nLegal Theories ({len(why_data['legal_theories'])}):")
        for theory in why_data["legal_theories"]:
            print(f"  - {theory['name']} (strength: {theory['strength']:.1%})")
            print(f"    {theory['description']}")

        print(f"\nSupporting Precedents ({len(why_data['supporting_precedents'])}):")
        for precedent in why_data["supporting_precedents"][:3]:  # Top 3
            print(f"  - {precedent['case_name']}")
            print(f"    Citation: {precedent['citation']}")
            print(f"    Relevance: {precedent['relevance_score']:.1%}")

        print(f"\nRisk Factors:")
        for risk in why_data["risk_factors"]:
            print(f"  ⚠️  {risk}")

        print(f"\nMitigation Strategies:")
        for strategy in why_data["mitigation_strategies"]:
            print(f"  ✓ {strategy}")

        # Strategic recommendation
        if why_data["argument_strength"] > 0.7:
            print("\n✅ Strong case - recommend proceeding")
        elif why_data["argument_strength"] > 0.5:
            print("\n⚖️  Moderate case - consider settlement")
        else:
            print("\n❌ Weak case - recommend settlement or dismissal")

        return why_data
```

**TypeScript Example - Precedent Comparison:**
```typescript
async function comparePrecedents(clientId: string, caseId: string) {
    const response = await fetch('http://10.10.0.87:8015/api/v1/context/dimension/retrieve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            client_id: clientId,
            case_id: caseId,
            dimension: 'WHY'
        })
    });

    const { data: whyData } = await response.json();

    // Calculate precedent balance
    const precedentAnalysis = {
        supporting: {
            count: whyData.supporting_precedents.length,
            avgRelevance: whyData.supporting_precedents.reduce(
                (sum, p) => sum + p.relevance_score, 0
            ) / whyData.supporting_precedents.length,
            topCases: whyData.supporting_precedents
                .sort((a, b) => b.relevance_score - a.relevance_score)
                .slice(0, 5)
        },
        opposing: {
            count: whyData.opposing_precedents.length,
            avgRelevance: whyData.opposing_precedents.reduce(
                (sum, p) => sum + p.relevance_score, 0
            ) / whyData.opposing_precedents.length,
            topCases: whyData.opposing_precedents
                .sort((a, b) => b.relevance_score - a.relevance_score)
                .slice(0, 5)
        },
        balance: whyData.supporting_precedents.length - whyData.opposing_precedents.length,
        distinguishingFactors: whyData.distinguishing_factors
    };

    console.log('Precedent Analysis:', precedentAnalysis);

    // Determine precedent strength
    if (precedentAnalysis.balance > 5) {
        console.log('✅ Strong precedent support');
    } else if (precedentAnalysis.balance < -5) {
        console.log('❌ Weak precedent support');
    } else {
        console.log('⚖️  Balanced precedents');
    }

    return precedentAnalysis;
}
```

---

## Dimension Interactions

### Multi-Dimensional Queries

Dimensions are designed to work together, providing richer context through interaction:

#### WHO + WHAT: Party-Claim Analysis
```python
async def analyze_party_claims(context: ContextResponse):
    """Correlate parties with their specific claims"""

    party_claims = {}

    for party in context.who.parties:
        # Find claims asserted by this party
        claims = [
            coa for coa in context.what.causes_of_action
            if party.role in ['plaintiff', 'petitioner']
        ]

        party_claims[party.name] = {
            'role': party.role,
            'claims': claims,
            'attorneys': [
                atty for atty in context.who.attorneys
                if party.id in atty.representing
            ]
        }

    return party_claims
```

#### WHAT + WHY: Issue-Precedent Mapping
```python
async def map_issues_to_precedents(context: ContextResponse):
    """Map legal issues to relevant precedents"""

    issue_precedent_map = {}

    for issue in context.what.legal_issues:
        # Find precedents addressing this issue
        relevant_precedents = [
            prec for prec in context.why.supporting_precedents
            if issue.lower() in prec.holding.lower()
        ]

        issue_precedent_map[issue] = {
            'supporting_count': len(relevant_precedents),
            'top_precedent': max(
                relevant_precedents,
                key=lambda p: p.relevance_score
            ) if relevant_precedents else None
        }

    return issue_precedent_map
```

#### WHEN + WHY: Temporal Strategy
```python
async def analyze_temporal_strategy(context: ContextResponse):
    """Analyze how timing affects strategy"""

    # Check if statute of limitations is approaching
    sol_approaching = (
        context.when.statute_of_limitations and
        (context.when.statute_of_limitations - datetime.now()).days < 90
    )

    # Adjust strategy based on urgency
    if sol_approaching:
        strategy = {
            'priority': 'HIGH',
            'recommendation': 'File immediately to preserve claims',
            'risk_factors': [
                *context.why.risk_factors,
                'Statute of limitations approaching'
            ]
        }
    elif context.when.urgency_score > 0.7:
        strategy = {
            'priority': 'MEDIUM',
            'recommendation': 'Proceed promptly but allow time for thorough preparation',
            'risk_factors': context.why.risk_factors
        }
    else:
        strategy = {
            'priority': 'LOW',
            'recommendation': 'Take time for comprehensive research and preparation',
            'risk_factors': context.why.risk_factors
        }

    return strategy
```

#### WHERE + WHAT: Jurisdictional Compliance
```python
async def check_jurisdictional_compliance(context: ContextResponse):
    """Verify citations and procedures match jurisdiction"""

    jurisdiction = context.where.primary_jurisdiction

    # Check if citations match jurisdiction
    mismatched_citations = [
        cite for cite in context.what.statutes
        if cite.jurisdiction != jurisdiction
    ]

    # Check if procedures match court
    court_specific_rules = [
        rule for rule in context.where.local_rules
        if rule.jurisdiction == jurisdiction
    ]

    compliance = {
        'jurisdiction': jurisdiction,
        'court': context.where.court,
        'citation_matches': len(mismatched_citations) == 0,
        'mismatched_citations': mismatched_citations,
        'applicable_local_rules': court_specific_rules,
        'compliance_score': 1.0 if len(mismatched_citations) == 0 else 0.7
    }

    return compliance
```

### Complete Multi-Dimensional Analysis Example

```python
async def perform_comprehensive_analysis(client_id: str, case_id: str):
    """Perform complete 5-dimensional analysis with interactions"""

    # 1. Retrieve all dimensions
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://10.10.0.87:8015/api/v1/context/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "scope": "comprehensive"
            }
        )
        context = ContextResponse(**response.json())

    # 2. Analyze dimension interactions
    party_claims = await analyze_party_claims(context)
    issue_precedents = await map_issues_to_precedents(context)
    temporal_strategy = await analyze_temporal_strategy(context)
    jurisdictional_compliance = await check_jurisdictional_compliance(context)

    # 3. Generate comprehensive report
    report = {
        'case_id': case_id,
        'overall_quality': context.context_score,
        'is_complete': context.is_complete,

        'party_analysis': party_claims,
        'issue_precedent_map': issue_precedents,
        'strategy': temporal_strategy,
        'compliance': jurisdictional_compliance,

        'dimension_scores': {
            'WHO': score_who_dimension(context.who),
            'WHAT': score_what_dimension(context.what),
            'WHERE': score_where_dimension(context.where),
            'WHEN': score_when_dimension(context.when),
            'WHY': score_why_dimension(context.why)
        },

        'recommendations': generate_recommendations(
            context,
            party_claims,
            temporal_strategy,
            jurisdictional_compliance
        )
    }

    return report
```

---

## Scope Levels

The Context Engine supports three scope levels for performance optimization:

### Minimal Scope

**Dimensions**: WHO + WHERE
**Performance Target**: <100ms
**Use Cases**: Quick party lookup, jurisdiction check

```python
# Minimal scope - fastest
response = await client.post(
    "/api/v1/context/retrieve",
    json={
        "client_id": "client-abc",
        "case_id": "case-123",
        "scope": "minimal"  # Only WHO + WHERE
    }
)

# Results: Parties, attorneys, court, jurisdiction
# Missing: Legal issues, deadlines, precedents
```

### Standard Scope

**Dimensions**: WHO + WHAT + WHERE + WHEN
**Performance Target**: 100-500ms
**Use Cases**: Most document processing workflows

```python
# Standard scope - balanced
response = await client.post(
    "/api/v1/context/retrieve",
    json={
        "client_id": "client-abc",
        "case_id": "case-123",
        "scope": "standard"  # WHO + WHAT + WHERE + WHEN
    }
)

# Results: Parties, legal issues, jurisdiction, deadlines
# Missing: Precedent analysis (WHY)
```

### Comprehensive Scope

**Dimensions**: All 5 (WHO + WHAT + WHERE + WHEN + WHY)
**Performance Target**: 500-2000ms
**Use Cases**: Deep analysis, brief writing, strategic planning

```python
# Comprehensive scope - complete analysis
response = await client.post(
    "/api/v1/context/retrieve",
    json={
        "client_id": "client-abc",
        "case_id": "case-123",
        "scope": "comprehensive"  # All 5 dimensions
    }
)

# Results: Complete context including precedent analysis
```

### Custom Dimension Selection

For maximum flexibility, override scope with explicit dimension list:

```python
# Custom: Only WHO + WHEN (party deadlines)
response = await client.post(
    "/api/v1/context/retrieve",
    json={
        "client_id": "client-abc",
        "case_id": "case-123",
        "include_dimensions": ["WHO", "WHEN"]  # Custom selection
    }
)

# Custom: Only WHAT + WHY (legal analysis)
response = await client.post(
    "/api/v1/context/retrieve",
    json={
        "client_id": "client-abc",
        "case_id": "case-123",
        "include_dimensions": ["WHAT", "WHY"]  # Issues + precedents
    }
)
```

---

## Quality Scoring

### Overall Context Quality Score

The overall `context_score` is calculated as:

```python
def calculate_overall_score(dimension_results: Dict[str, Any]) -> float:
    """
    Calculate overall context quality score (0.0-1.0)

    Formula:
        context_score = (Σ dimension_scores / num_dimensions) * completeness_ratio

    Where:
        dimension_scores = Individual scores for each dimension
        num_dimensions = Total dimensions requested
        completeness_ratio = dimensions_found / dimensions_requested
    """

    # Calculate individual dimension scores
    dimension_scores = []
    for dimension_name, context in dimension_results.items():
        score = score_dimension(dimension_name, context)
        dimension_scores.append(score)

    # Average dimension scores
    avg_score = sum(dimension_scores) / len(dimension_scores)

    # Apply completeness penalty
    successful_dimensions = sum(1 for score in dimension_scores if score > 0.0)
    completeness_ratio = successful_dimensions / len(dimension_scores)

    # Final score
    final_score = avg_score * completeness_ratio

    return min(1.0, max(0.0, final_score))
```

### Completeness Threshold

**Threshold**: ≥0.85
**Interpretation**:
- **≥0.85**: Complete context (green) - ready for use
- **0.70-0.84**: Good context (yellow) - usable with gaps
- **<0.70**: Incomplete context (red) - needs improvement

```python
is_complete = context_score >= 0.85
```

### Quality Metrics by Dimension

Each dimension reports quality metrics:

```json
{
  "dimension_name": "WHO",
  "completeness_score": 0.87,
  "data_points": 12,
  "confidence_avg": 0.91,
  "is_sufficient": true
}
```

---

## Performance Optimization

### Caching Strategy

Three-tier caching for optimal performance:

#### Tier 1: In-Memory Cache
- **TTL**: 10 minutes
- **Access Time**: <10ms
- **Use**: Hot cases currently being processed

#### Tier 2: Redis Cache (future)
- **TTL**: 1 hour (active cases), 24 hours (closed cases)
- **Access Time**: <50ms
- **Use**: Recently accessed cases across instances

#### Tier 3: Database Cache (future)
- **TTL**: Persistent
- **Access Time**: <200ms
- **Use**: Long-term storage, cold cases

### Performance Targets

| Scope | Cache Hit | Cache Miss |
|-------|-----------|------------|
| Minimal | <10ms | <100ms |
| Standard | <10ms | 100-500ms |
| Comprehensive | <10ms | 500-2000ms |

### Optimization Techniques

#### 1. Selective Dimension Retrieval
```python
# Only retrieve needed dimensions
response = await client.post(
    "/api/v1/context/retrieve",
    json={
        "client_id": "client-abc",
        "case_id": "case-123",
        "include_dimensions": ["WHO", "WHEN"]  # Skip expensive WHY analysis
    }
)
```

#### 2. Cache Warming
```python
# Pre-warm cache for high-traffic cases
await client.post(
    "/api/v1/cache/warmup",
    json={
        "client_id": "client-abc",
        "case_ids": ["case-1", "case-2", "case-3"],
        "scope": "standard"
    }
)
```

#### 3. Batch Processing
```python
# Process multiple cases in one request
results = await client.post(
    "/api/v1/context/batch/retrieve",
    json={
        "client_id": "client-abc",
        "case_ids": ["case-1", "case-2", "case-3"],
        "scope": "minimal"
    }
)
```

---

## Best Practices

### 1. Always Start with Minimal Scope

```python
# Start minimal
minimal_context = await get_context(scope="minimal")

# Upgrade if needed
if requires_legal_analysis:
    full_context = await get_context(scope="comprehensive")
```

### 2. Monitor Quality Scores

```python
context = await get_context(scope="comprehensive")

if context["context_score"] < 0.85:
    logger.warning(f"Low quality context: {context['context_score']}")

    # Check individual dimensions
    for dimension in ["WHO", "WHAT", "WHERE", "WHEN", "WHY"]:
        quality = await get_dimension_quality(dimension)
        if not quality["is_sufficient"]:
            logger.error(f"{dimension} dimension insufficient")
```

### 3. Use Caching Strategically

```python
# First request: cache miss
context1 = await get_context(case_id="case-123", use_cache=True)
# execution_time_ms: 1200ms, cached: false

# Subsequent requests: cache hit
context2 = await get_context(case_id="case-123", use_cache=True)
# execution_time_ms: 8ms, cached: true

# After case update: refresh cache
await refresh_context(case_id="case-123")
```

### 4. Handle Dimension Failures Gracefully

```python
context = await get_context(scope="comprehensive")

# Check if WHY dimension available
if context["why"] is None:
    logger.warning("WHY dimension unavailable - proceeding without precedent analysis")
    # Use partial context
else:
    # Full analysis available
    analyze_precedents(context["why"])
```

### 5. Leverage Dimension Interactions

```python
# Don't just use dimensions in isolation
if context["who"] and context["what"]:
    party_claims = correlate_parties_with_claims(
        parties=context["who"]["parties"],
        claims=context["what"]["causes_of_action"]
    )

if context["when"] and context["why"]:
    temporal_strategy = adjust_strategy_for_deadlines(
        deadlines=context["when"]["upcoming_deadlines"],
        strength=context["why"]["argument_strength"]
    )
```

---

**Version**: 1.0.0
**Last Updated**: 2025-01-22
**Related Documentation**:
- [API Documentation](api.md)
- [Error Handling Guide](ERROR_HANDLING.md)
- [Advanced Usage](ADVANCED_USAGE.md)
