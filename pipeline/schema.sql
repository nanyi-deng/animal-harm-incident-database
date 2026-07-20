-- AHID pilot database schema
-- Mirrors docs/data_dictionary.csv (the authoritative field definitions).
-- SQLite for the research MVP (PRD v1.2 C3); types kept plain enough to
-- port to Postgres later without rewriting.

CREATE TABLE IF NOT EXISTS incidents_public (
    incident_id TEXT PRIMARY KEY,              -- AHID-CN-YYYY-NNNN, encodes no geography (PRD v1.2 C1)
    seed_candidate_no INTEGER,                 -- internal only: row # in docs/pipeline/candidate_incidents_seed.md, not part of the public export
    first_detected_at TEXT,
    last_updated_at TEXT,
    event_date_start TEXT,
    event_date_end TEXT,
    date_precision TEXT CHECK (date_precision IN ('day','month','quarter','year','unknown')),
    date_status TEXT CHECK (date_status IN ('metadata_supported','officially_reported','multiple_sources_supported','claimed_only','unknown','contradicted')),
    province TEXT,
    city TEXT,
    location_precision TEXT CHECK (location_precision IN ('district','city','province','unknown')),
    location_status TEXT CHECK (location_status IN ('exact_location_supported','district_supported','city_supported','province_supported','claimed_only','unknown','contradicted')),
    animal_category TEXT CHECK (animal_category IN ('dog','cat','other_companion','livestock','wildlife','captive_wildlife','multiple','other','unknown')),
    species TEXT,
    estimated_animal_count TEXT,
    juvenile_animal TEXT CHECK (juvenile_animal IN ('yes','no','unknown')),
    injury_status TEXT CHECK (injury_status IN ('injured','uninjured','unknown')),
    mortality_status TEXT CHECK (mortality_status IN ('dead','alive','partial','unknown')),
    rescue_status TEXT CHECK (rescue_status IN ('rescued','not_rescued','partial','unknown')),
    harm_categories TEXT,                      -- pipe-separated, see data_dictionary.csv enum list
    minor_involvement TEXT CHECK (minor_involvement IN ('yes','no','unknown')),
    institutional_involvement TEXT CHECK (institutional_involvement IN ('yes','no','unknown')),
    commercial_involvement TEXT CHECK (commercial_involvement IN ('yes','no','unknown')),
    group_involvement TEXT CHECK (group_involvement IN ('yes','no','unknown')),
    content_creation_involvement TEXT CHECK (content_creation_involvement IN ('yes','no','unknown')),
    official_response_found INTEGER,           -- boolean; NULL until Response extraction stage runs
    police_response_found INTEGER,
    school_response_found INTEGER,
    ngo_response_found INTEGER,
    rescue_response_found INTEGER,
    legal_outcome_found INTEGER,
    policy_response_found INTEGER,
    automation_status TEXT CHECK (automation_status IN ('A1','A2','A3','A4','AX','AF')),  -- NULL = not yet classified (pre-A1); A0 never appears here
    evidence_sufficiency_score INTEGER CHECK (evidence_sufficiency_score BETWEEN 0 AND 100),
    score_version TEXT,
    ruleset_version TEXT,
    model_version TEXT,
    independent_source_cluster_count INTEGER,
    official_source_count INTEGER,
    contradiction_count INTEGER,
    disputed_flag INTEGER,
    misattribution_flag INTEGER,
    is_test_case INTEGER DEFAULT 0,            -- internal only: 1 for #15-style pipeline test fixtures; never exported publicly
    inclusion_note TEXT                        -- internal only: PI review rationale from human_review_log
);

CREATE TABLE IF NOT EXISTS sources_public (
    source_id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents_public(incident_id),
    source_type TEXT CHECK (source_type IN ('government','court','police','news','ngo','social_post','blog','petition','other')),
    source_tier TEXT CHECK (source_tier IN ('1','2','3','4')),
    platform TEXT,
    source_name TEXT,
    original_url TEXT NOT NULL,
    archived_url TEXT,
    publication_date TEXT,
    first_collected_at TEXT,                   -- NULL until the archiving stage actually fetches the page
    language TEXT CHECK (language IN ('zh-Hans','zh-Hant','en','ja','ko','es','other')),
    primary_source_status TEXT CHECK (primary_source_status IN ('primary','near_primary','secondary','unknown')),
    independence_status TEXT CHECK (independence_status IN ('independent','dependent','unknown')),
    independent_cluster_id TEXT,
    cites_source_id TEXT REFERENCES sources_public(source_id),
    availability_status TEXT CHECK (availability_status IN ('available','removed','private','modified','unknown')),
    needs_primary_source_verification INTEGER DEFAULT 0  -- internal only: from HRL-007 review notes
);

CREATE TABLE IF NOT EXISTS claims_public (
    claim_id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents_public(incident_id),
    claim_type TEXT CHECK (claim_type IN ('event_occurred','event_date','event_location','animal_species','animal_count','harm_method','animal_death','minor_involvement','institutional_involvement','official_response','rescue_outcome','legal_outcome','policy_response')),
    claim_value TEXT,
    support_status TEXT CHECK (support_status IN ('supported','partially_supported','claimed_only','contradicted','unknown')),
    supporting_source_count INTEGER,
    independent_supporting_count INTEGER,
    contradicting_source_count INTEGER,
    confidence_category TEXT CHECK (confidence_category IN ('high','medium','low'))
);

CREATE TABLE IF NOT EXISTS responses_public (
    response_id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents_public(incident_id),
    responder_type TEXT CHECK (responder_type IN ('government','police','court','school','company','ngo','rescue_group','platform','other')),
    responder_name_public TEXT,
    response_type TEXT CHECK (response_type IN ('statement','investigation','filing','penalty','rescue','policy','denial','other')),
    response_date TEXT,
    source_id TEXT NOT NULL REFERENCES sources_public(source_id),
    summary_zh TEXT,
    summary_en TEXT
);
