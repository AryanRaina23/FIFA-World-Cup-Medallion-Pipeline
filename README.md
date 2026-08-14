# ⚽ FIFA World Cup End-to-End Data Engineering Pipeline & Power BI Analytics Framework

An end-to-end, production-grade **Data Engineering & Business Intelligence PoC** built using open-source technologies (**Docker, Apache Airflow, PostgreSQL, Python, Pandas**) and **Power BI**. 

This project demonstrates modern ETL/ELT data processing concepts, a **Medallion Architecture (Bronze $\rightarrow$ Silver $\rightarrow$ Gold)**, automated data quality validation with error quarantining, **Slowly Changing Dimensions (SCD Type 2)**, business intelligence transformations, and interactive analytical dashboards.

---

## 🏗️ System Architecture & Data Flow

```text
                                  +-----------------------+
                                  |  MULTI-SOURCE DATA    |
                                  | CSV / JSON / XML      |
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------------------+
                                  | INGESTION & METADATA  |
                                  | (Full & Incremental)  |
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------------------+
                                  |     BRONZE LAYER      |
                                  | Immutable Raw Storage |
                                  | Local Partitioned CSV |
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------------------+
                                  | DATA VALIDATION ENGINE|
                                  | Nulls/Dupes/Types     |
                                  +-----+-----------+-----+
                                        |           |
                           (Passed)     |           | (Rejected)
                                        v           v
                            +---------------+   +-------------------+
                            |  SILVER LAYER |   | REJECTED RECORDS  |
                            | Cleansed Data |   |  Quarantine Table |
                            | Lookup Mapping|   +-------------------+
                            | SCD 1 & SCD 2 |
                            +-------+-------+
                                    |
                                    v
                            +---------------+
                            |   GOLD LAYER  |
                            | Star Schema   |
                            | Marts & Views |
                            +-------+-------+
                                    |
                                    v
                            +---------------+
                            |  POWER BI UI  |
                            | 2-Page Portal |
                            +---------------+
```

---

## 🌟 Key Features & Implementation Breakdown

### 1. Multi-Source Ingestion & Metadata Capture
- **Multi-Format Support**: Ingests dataset inputs in **CSV** (`wc_2026_fixtures.csv`, `wc_all_matches.csv`), **JSON** (`wc_2026_teams.json`, `wc_top_scorers.json`), and **XML** (`wc_all_editions.xml`).
- **Metadata Capture**: Every record is enriched with execution metadata: `_ingested_at`, `_source_file`, `_source_format`, `_ingestion_id`, and `_run_id`.
- **Batch & Incremental Modes**: Handles full historical loads and incremental match/team updates seamlessly.

### 2. Medallion Architecture Implementation

#### 🥉 Bronze Layer (Immutable Raw Storage)
- Stores un-manipulated raw data in staging tables (`bronze.*_raw`).
- Automatically backs up immutable raw files under `data/bronze/{table}/ingest_date={YYYY-MM-DD}/run_{run_id}.csv`.

#### 🥈 Silver Layer (Data Quality & SCD Type 2)
- **Data Validation & Quarantine Engine**: Validates primary keys, checks for nulls, verifies schemas, and detects duplicate rows.
  - Passed records move to `bronze.valid_records`.
  - Failed/duplicate records are quarantined in `bronze.rejected_records` with detailed rejection reasons.
- **Data Cleansing & Standardization**: Normalizes dates, fills missing attributes, and maps confederations using `silver.lkp_confederations` (UEFA, CONMEBOL, CAF, CONCACAF, AFC, OFC).
- **Slowly Changing Dimensions (SCD Type 2)**: Tracks historical changes to team FIFA rankings and coaches in `silver.dim_teams_scd2`. Maintains versioning via:
  - `version_number`
  - `effective_start_date`
  - `effective_end_date` (active records defaulted to `9999-12-31`)
  - `current_flag` (`TRUE`/`FALSE`)

#### 🥇 Gold Layer (Star Schema & Business Marts)
Compiles clean analytics-ready models exposed in the `gold` database schema and exported to `data/gold/`:
- **Customer Dimension** $\rightarrow$ `gold.dim_teams`: Enriched team dimension linked with confederations.
- **Product Dimension** $\rightarrow$ `gold.dim_editions`: Tournament metadata across all 22 historical World Cups.
- **Sales Fact** $\rightarrow$ `gold.fact_matches`: Individual match results, scores, derived goal differences, and match winners.
- **Revenue Mart** $\rightarrow$ `gold.mart_world_cup_stats`: Computes derived ticket pricing scaling over time (`avg_ticket_price_usd`) and total estimated ticket revenue (`estimated_revenue_usd`).
- **KPI Summary** $\rightarrow$ `gold.kpi_summary`: Consolidated executive metrics (total goals, matches, attendance, host win counts).
- **Window Functions View** $\rightarrow$ `gold.dim_top_scorers_ranked`: SQL View utilizing `RANK()` and `DENSE_RANK()` over tournament editions to rank top goal scorers.

---

## 📊 Interactive Power BI Dashboard Overview

The project includes a 2-page dashboard connected live to the PostgreSQL `gold` analytics schema, styled with a **Sports Command Center / Dark Glassmorphism aesthetic**:

### 📄 Page 1: FIFA World Cup History (Tournament Chronicle)
- **Header & Navigation**: Features a gold banner title, quick slicers, and interactive Page Navigation buttons.
- **KPI Cards**: Real-time summary metrics for **Total Matches (964)**, **Total Attendance (44M)**, and **Total Goals (2,548)**.
- **Champions Share (Donut Chart)**: Displays championship distribution by country (highlighting 5-time winner Brazil, Italy, Germany, Argentina, etc.).
- **Attendance & Goals Trend (Combo Chart)**: Visualizes historical visitor growth alongside goal scoring trends from 1930 to 2026.
- **Goals by Year & Champion (Clustered Column Chart)**: Deep dives into scoring distribution by champion country across editions.
- **World Cup Hosts (Treemap Grid)**: Modern grid displaying host nations sized by frequency of hosting.

### 📄 Page 2: Squad Intel & Golden Boot Tracker (Player & Team Analytics)
- **Interactive Team Slicer**: Filterable dropdown pane to inspect specific national squads.
- **Squad Profile Badge**: Dynamic cards showing the selected country's **Current Coach**, **FIFA Rank**, and **Best World Cup Result**.
- **Golden Boot Leaderboard (Clustered Bar Chart)**: Ranks historical top scorers (Just Fontaine, Gerd Müller, Pelé, Messi, Mbappé) filtered to the Top 10.
- **Confederation Team Distribution (Funnel Chart)**: Visualizes team representation across UEFA, CAF, AFC, CONCACAF, and CONMEBOL.
- **Goal Difference by Stage (Column Chart)**: Analyzes match intensity and goal margins across Group Stage, Knockouts, Semi-Finals, and Finals.
- **Match Outcome Distribution (Donut Chart)**: Displays global breakdown of Home Wins, Away Wins, and Draws across all historical matches.

---

## ⚙️ Audit, Metadata & Error Handling Framework
- **Pipeline History**: Logged in `metadata.pipeline_runs` (`pipeline_name`, `status`, `start_time`, `end_time`, `duration_seconds`).
- **Audit Logs**: Logged in `metadata.audit_logs` tracking `records_processed`, `records_inserted`, `records_updated`, and `records_rejected` for every single pipeline step.
- **Quarantine Audit**: Any malformed or duplicate record is captured in `bronze.rejected_records` without breaking pipeline execution.

---

## 🛠️ Technology Stack & Prerequisites

| Component | Tool / Technology |
| :--- | :--- |
| **Containerization** | Docker & Docker Compose |
| **Database** | PostgreSQL 15 (Alpine) |
| **Workflow Orchestration** | Apache Airflow 2.7.2 |
| **Processing Engine** | Python 3.10 / Pandas |
| **Data Quality** | Custom Validation & Quarantine Engine |
| **Analytics & BI** | Power BI Desktop |

---

## 🚀 Step-by-Step Execution Guide

### 1. Start Infrastructure via Docker Compose
From the project root directory (`D:\Kanini Projects\FIFA World Cup Pipeline PoC`):
```bash
docker compose up -d
```
Verify running services:
```bash
docker ps
```
*(Confirms `postgres_fifa` on port `5432` and `airflow_webserver` on port `8080` are active).*

### 2. Initialize & Convert Data Sources
```bash
python scripts/setup_sources.py
```

### 3. Run the End-to-End Pipeline CLI
```bash
python scripts/run_pipeline.py
```

### 4. Test Incremental Loads & SCD Type 2
```bash
python scripts/simulate_incremental.py
```

### 5. Access Apache Airflow UI
- **URL**: [http://localhost:8080](http://localhost:8080)
- **Credentials**: `admin` / `admin`
- Unpause **`fifa_world_cup_pipeline`** and click **Trigger DAG** to watch the 4 sequential tasks execute (`ingest_to_bronze` $\rightarrow$ `validate_bronze` $\rightarrow$ `load_to_silver` $\rightarrow$ `load_to_gold`).

### 6. View Quarantined Data in PostgreSQL
```bash
docker exec -it postgres_fifa psql -U postgres -d fifa_dw -c "SELECT table_name, rejection_reason, record_data FROM bronze.rejected_records;"
```

### 7. Launch Power BI Dashboard
Open **`FIFA_World_Cup_Dashboard.pbix`** in Power BI Desktop to interact with the live report.

---

## 📁 Repository Structure

```text
FIFA World Cup Pipeline PoC/
├── dags/
│   └── fifa_pipeline_dag.py          # Airflow DAG definition
├── data/
│   ├── bronze/                        # Partitioned raw local backups
│   ├── silver/                        # Cleansed silver CSV exports & SCD2
│   ├── gold/                          # Gold star schema CSV exports
│   └── sources/                       # Multi-source datasets (CSV/JSON/XML)
├── scripts/
│   ├── setup_sources.py              # Multi-source format conversion
│   ├── ingest_to_bronze.py           # Raw ingestion & metadata tagging
│   ├── validate_bronze.py            # Data quality & quarantine engine
│   ├── load_to_silver.py             # Data cleansing, lookups & SCD Type 2
│   ├── load_to_gold.py               # Star schema, marts & window views
│   ├── run_pipeline.py               # Standalone pipeline CLI orchestrator
│   └── simulate_incremental.py       # Incremental & SCD2 simulation test
├── sql/
│   └── init_db.sql                   # Database bootstrap & lookup seeds
├── docker-compose.yml                 # Postgres & Airflow stack definition
├── instructions_power_bi.md          # Power BI connection & modeling guide
├── FIFA_World_Cup_Dashboard.pbix     # Power BI report file
└── README.md                         # Project documentation
```
