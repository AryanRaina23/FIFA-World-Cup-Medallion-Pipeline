-- Create Schemas
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS metadata;

-- ============================================================================
-- METADATA SCHEMA TABLES
-- ============================================================================
CREATE TABLE IF NOT EXISTS metadata.pipeline_runs (
    run_id VARCHAR(50) PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- 'SUCCESS', 'FAILED', 'RUNNING'
    execution_time_seconds FLOAT
);

CREATE TABLE IF NOT EXISTS metadata.audit_logs (
    log_id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) REFERENCES metadata.pipeline_runs(run_id) ON DELETE CASCADE,
    step_name VARCHAR(100) NOT NULL, -- 'INGESTION', 'VALIDATION', 'SILVER', 'GOLD'
    table_name VARCHAR(100) NOT NULL,
    records_processed INT DEFAULT 0,
    records_inserted INT DEFAULT 0,
    records_updated INT DEFAULT 0,
    records_rejected INT DEFAULT 0,
    status VARCHAR(20) NOT NULL, -- 'SUCCESS', 'FAILED'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- BRONZE SCHEMA TABLES (Raw ingestion tables, everything text/varchar)
-- ============================================================================
CREATE TABLE IF NOT EXISTS bronze.teams_raw (
    team VARCHAR(255),
    "group" VARCHAR(10),
    confederation VARCHAR(50),
    fifa_rank VARCHAR(50),
    coach VARCHAR(255),
    best_wc_result VARCHAR(255),
    debut_2026 VARCHAR(10),
    _ingestion_id VARCHAR(50),
    _ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255),
    _source_format VARCHAR(10),
    _run_id VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS bronze.fixtures_raw (
    "group" VARCHAR(10),
    stage VARCHAR(100),
    team1 VARCHAR(255),
    team2 VARCHAR(255),
    venue VARCHAR(255),
    city VARCHAR(255),
    country VARCHAR(255),
    date VARCHAR(50),
    kickoff_et VARCHAR(50),
    team1_confederation VARCHAR(50),
    team1_fifa_rank VARCHAR(50),
    team1_coach VARCHAR(255),
    team2_confederation VARCHAR(50),
    team2_fifa_rank VARCHAR(50),
    team2_coach VARCHAR(255),
    _ingestion_id VARCHAR(50),
    _ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255),
    _source_format VARCHAR(10),
    _run_id VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS bronze.editions_raw (
    edition VARCHAR(50),
    year VARCHAR(50),
    host VARCHAR(255),
    champion VARCHAR(255),
    runner_up VARCHAR(255),
    third_place VARCHAR(255),
    fourth_place VARCHAR(255),
    teams VARCHAR(50),
    matches VARCHAR(50),
    goals VARCHAR(50),
    goals_per_match VARCHAR(50),
    attendance VARCHAR(50),
    top_scorer TEXT,
    top_scorer_country VARCHAR(255),
    top_scorer_goals VARCHAR(50),
    start_date VARCHAR(50),
    end_date VARCHAR(50),
    final_city VARCHAR(255),
    host_won VARCHAR(50),
    format VARCHAR(100),
    _ingestion_id VARCHAR(50),
    _ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255),
    _source_format VARCHAR(10),
    _run_id VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS bronze.matches_raw (
    year VARCHAR(50),
    stage VARCHAR(100),
    team1 VARCHAR(255),
    score1 VARCHAR(50),
    score2 VARCHAR(50),
    team2 VARCHAR(255),
    venue VARCHAR(255),
    city VARCHAR(255),
    country VARCHAR(255),
    date VARCHAR(50),
    notes TEXT,
    _ingestion_id VARCHAR(50),
    _ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255),
    _source_format VARCHAR(10),
    _run_id VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS bronze.top_scorers_raw (
    edition VARCHAR(50),
    year VARCHAR(50),
    player VARCHAR(255),
    country VARCHAR(255),
    position VARCHAR(50),
    goals VARCHAR(50),
    assists VARCHAR(50),
    penalties VARCHAR(50),
    matches_played VARCHAR(50),
    host VARCHAR(255),
    team_result VARCHAR(255),
    _ingestion_id VARCHAR(50),
    _ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255),
    _source_format VARCHAR(10),
    _run_id VARCHAR(50)
);

-- Quarantine table for data validation failures
CREATE TABLE IF NOT EXISTS bronze.rejected_records (
    rejected_id SERIAL PRIMARY KEY,
    run_id VARCHAR(50),
    table_name VARCHAR(100) NOT NULL,
    record_data JSONB NOT NULL,
    rejection_reason TEXT NOT NULL,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SILVER SCHEMA TABLES (Cleansed, typed, structured data)
-- ============================================================================

-- Lookup tables
CREATE TABLE IF NOT EXISTS silver.lkp_confederations (
    confederation VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL
);

-- Populate lookup static data
INSERT INTO silver.lkp_confederations (confederation, full_name) VALUES
('UEFA', 'Union of European Football Associations'),
('CONMEBOL', 'Confederación Sudamericana de Fútbol'),
('CONCACAF', 'Confederation of North, Central America and Caribbean Association Football'),
('CAF', 'Confédération Africaine de Football'),
('AFC', 'Asian Football Confederation'),
('OFC', 'Oceania Football Confederation')
ON CONFLICT (confederation) DO NOTHING;

-- Slowly Changing Dimension Type 2 for Teams (tracking ranks & coaches)
CREATE TABLE IF NOT EXISTS silver.dim_teams_scd2 (
    team_key SERIAL PRIMARY KEY,
    team_name VARCHAR(255) NOT NULL,
    group_letter VARCHAR(10),
    confederation VARCHAR(50),
    fifa_rank INT,
    coach VARCHAR(255),
    best_wc_result VARCHAR(255),
    debut_2026 BOOLEAN,
    effective_start_date DATE NOT NULL,
    effective_end_date DATE NOT NULL DEFAULT '9999-12-31',
    current_flag BOOLEAN NOT NULL DEFAULT TRUE,
    version_number INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.editions (
    edition_id INT PRIMARY KEY,
    year INT NOT NULL,
    host VARCHAR(255) NOT NULL,
    champion VARCHAR(255),
    runner_up VARCHAR(255),
    third_place VARCHAR(255),
    fourth_place VARCHAR(255),
    teams_count INT,
    matches_count INT,
    goals_count INT,
    goals_per_match FLOAT,
    attendance INT,
    top_scorer VARCHAR(255),
    top_scorer_country VARCHAR(255),
    top_scorer_goals INT,
    start_date DATE,
    end_date DATE,
    final_city VARCHAR(255),
    host_won BOOLEAN,
    format VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS silver.matches (
    match_id SERIAL PRIMARY KEY,
    year INT NOT NULL,
    stage VARCHAR(100),
    team1 VARCHAR(255) NOT NULL,
    score1 INT,
    score2 INT,
    team2 VARCHAR(255) NOT NULL,
    venue VARCHAR(255),
    city VARCHAR(255),
    country VARCHAR(255),
    match_date DATE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS silver.fixtures (
    fixture_id SERIAL PRIMARY KEY,
    group_letter VARCHAR(10),
    stage VARCHAR(100),
    team1 VARCHAR(255) NOT NULL,
    team2 VARCHAR(255) NOT NULL,
    venue VARCHAR(255),
    city VARCHAR(255),
    country VARCHAR(255),
    fixture_date DATE,
    kickoff_et VARCHAR(50),
    team1_confederation VARCHAR(50),
    team1_fifa_rank INT,
    team1_coach VARCHAR(255),
    team2_confederation VARCHAR(50),
    team2_fifa_rank INT,
    team2_coach VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS silver.top_scorers (
    scorer_id SERIAL PRIMARY KEY,
    edition_id INT,
    year INT NOT NULL,
    player VARCHAR(255) NOT NULL,
    country VARCHAR(255),
    position VARCHAR(50),
    goals INT,
    assists INT,
    penalties INT,
    matches_played INT,
    host VARCHAR(255),
    team_result VARCHAR(255)
);

-- ============================================================================
-- GOLD SCHEMA TABLES (Star Schema for reporting)
-- ============================================================================

-- dim_teams (Customer Dimension equivalent)
CREATE TABLE IF NOT EXISTS gold.dim_teams (
    team_id SERIAL PRIMARY KEY,
    team_name VARCHAR(255) NOT NULL UNIQUE,
    confederation VARCHAR(50),
    confederation_full_name VARCHAR(255),
    debut_2026 BOOLEAN,
    best_wc_result VARCHAR(255),
    current_coach VARCHAR(255),
    current_fifa_rank INT,
    is_active BOOLEAN DEFAULT TRUE,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- dim_editions (Product Dimension equivalent)
CREATE TABLE IF NOT EXISTS gold.dim_editions (
    edition_id INT PRIMARY KEY,
    year INT NOT NULL,
    host VARCHAR(255) NOT NULL,
    champion VARCHAR(255),
    runner_up VARCHAR(255),
    third_place VARCHAR(255),
    teams_count INT,
    matches_count INT,
    goals_count INT,
    attendance INT,
    host_won BOOLEAN
);

-- fact_matches (Sales Fact equivalent)
CREATE TABLE IF NOT EXISTS gold.fact_matches (
    match_id SERIAL PRIMARY KEY,
    edition_year INT NOT NULL,
    stage VARCHAR(100),
    team1_name VARCHAR(255) NOT NULL,
    team2_name VARCHAR(255) NOT NULL,
    score1 INT,
    score2 INT,
    goal_difference INT,
    match_winner VARCHAR(255),
    venue VARCHAR(255),
    city VARCHAR(255),
    country VARCHAR(255),
    match_date DATE,
    notes TEXT
);

-- mart_world_cup_stats (Revenue Mart equivalent)
CREATE TABLE IF NOT EXISTS gold.mart_world_cup_stats (
    year INT PRIMARY KEY,
    host VARCHAR(255) NOT NULL,
    champion VARCHAR(255),
    total_matches INT,
    total_goals INT,
    goals_per_match FLOAT,
    total_attendance INT,
    avg_attendance_per_match FLOAT,
    avg_ticket_price_usd FLOAT,
    estimated_revenue_usd FLOAT
);
