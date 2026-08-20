# Power BI Dashboard Connection and Design Guide

This guide provides step-by-step instructions on how to connect Microsoft Power BI Desktop to your FIFA World Cup Gold Data Warehouse and build an interactive, professional dashboard matching the finalized 3-page layout.

---

## 1. Connection Details
Your production data warehouse is running in the cloud on Neon. When configuring the connection in Power BI Desktop, use the following credentials:

*   **Data Source Type**: PostgreSQL Database
*   **Server**: `ep-withered-firefly-ay1mdau7-pooler.c-5.us-east-2.aws.neon.tech`
*   **Database**: `neondb`
*   **Authentication Method**: Database (Username/Password)
    *   **Username**: `neondb_owner`
    *   **Password**: `npg_JO5ASvYf7pIT`
*   **SSL / Encryption**: Enabled (Required by Neon).

---

## 2. Page-by-Page Visualization Design

### Page 1: FIFA World Cup History (General Overview)
This page gives a macro view of the tournament's evolution from 1930 to 2026.

*   **Header**: Add a yellow banner (`#f59e0b`) in the top center with the title **"FIFA World Cup History"**. Add navigation buttons next to it linking to `Page 2` and `Page 3`.
*   **KPI Cards (using `gold.kpi_summary`)**:
    *   **Total Matches**: `total_matches_played` (Format display unit as *None* $\rightarrow$ displays as `1K`).
    *   **Total Attendance**: `total_attendance` (Format display unit as *Millions* $\rightarrow$ displays as `50M`).
    *   **Total Goals**: `total_goals_scored` (Format display unit as *None* $\rightarrow$ displays as `3K`).
*   **Donut Chart: "World Cup Titles by Nation"**:
    *   **Legend**: `champion` (from `gold.dim_editions`)
    *   **Values**: Count of `year` (or your `Championships Won` measure)
*   **Line and Clustered Column Chart: "Attendance & Goals Trend Over Time"**:
    *   **X-Axis**: `year` (from `gold.dim_editions`)
    *   **Column Y-Axis**: `attendance` (Sum)
    *   **Line Y-Axis**: `goals_count` (Sum)
*   **Clustered Column Chart: "Goal Scoring History by Champion"**:
    *   **X-Axis**: `year`
    *   **Y-Axis**: `goals_count` (Sum)
    *   **Legend**: `champion`
*   **Treemap: "World Cup Hosts"**:
    *   **Category**: `host` (from `gold.dim_editions`)
    *   **Values**: Count of `year`

---

### Page 2: Squad Intel & Golden Boot (Performance Drilldown)
This page drills down into team-level parameters, squad coaches, and player efficiency.

*   **Slicer**: Add a Slicer visual for **"Team Name"** using `gold.dim_teams.team_name` configured as a dropdown.
*   **SCD2 KPI Cards (DAX fallback configuration)**:
    Create these three DAX measures in your model to display double-dashes (`--`) when no team is selected in the slicer:
    ```dax
    Display Coach = SELECTEDVALUE(dim_teams[current_coach], "--")
    Display Rank = SELECTEDVALUE(dim_teams[current_fifa_rank], "--")
    Display Best Finish = SELECTEDVALUE(dim_teams[best_wc_result], "--")
    ```
    *   **KPI Card 1**: Drag the `Display Coach` measure onto a card labeled **"Current Coach"**.
    *   **KPI Card 2**: Drag the `Display Rank` measure onto a card labeled **"FIFA Rank"** (Ensure display unit is set to *None*).
    *   **KPI Card 3**: Drag the `Display Best Finish` measure onto a card labeled **"Best WC Finish"**.
*   **Horizontal Bar Chart: "All-Time Top Goal Scorers"**:
    *   **Y-Axis**: `player` (from `gold.dim_top_scorers_ranked`)
    *   **X-Axis**: `goals` (Sum)
*   **Funnel Chart: "Participating Teams by Confederation"**:
    *   **Group**: `confederation` (from `gold.dim_teams`)
    *   **Values**: Count of `team_name`
*   **Clustered Column Chart: "Goal Differential by Tournament Stage"**:
    *   **X-Axis**: `stage` (from `gold.fact_matches`)
    *   **Y-Axis**: `goal_difference` (Sum)
*   **Q&A Prompt Visual**: Add a native **Q&A Visual** to the bottom right of the page to allow natural language prompt queries.

---

### Page 3: World Cup Honors & Commercial Forecasts (Commercials & Awards)
Demonstrates the financial forecasts, award list history, and links to the AI Agent.

*   **Chatbot Hyperlink Header**: Add a text block labeled **"Chatbot 💬"** at the top center. Turn on **Action** $\rightarrow$ set **Type** to **Web URL** $\rightarrow$ paste the live chatbot link: `https://fifa-world-cup-medallion-pipeline.vercel.app/`
*   **Clustered Bar Chart: "Ballon d'Or Winners"**:
    *   **Y-Axis**: `player` (from `gold.dim_ballon_dor`)
    *   **X-Axis**: Count of `award_id` (representing total awards won, e.g. Lionel Messi with 8)
    *   **Tooltips**: `country`, `club`
*   **Table: "Tournament Award Winners List"**:
    *   Add a Table visual with the columns: `year`, `award_type`, `winner`, `country` (from `gold.dim_world_cup_awards`).
*   **Line Chart: "Goals Scored Over Time"**:
    *   **X-Axis**: `year`
    *   **Y-Axis**: `goals_count` (from `gold.dim_editions`)
*   **Line and Clustered Column Chart: "Attendance vs Ticket Price Trends"**:
    *   **X-Axis**: `year` (from `gold.mart_world_cup_stats`)
    *   **Column Y-Axis**: `total_attendance` (Sum)
    *   **Line Y-Axis**: `avg_ticket_price_usd` (Average)

---

## 3. Drill and Synced Slicer Actions
1.  **Drill Down/Up**: Enabled on the Page 1 combo chart on the X-Axis (`confederation` $\rightarrow$ `team_name`).
2.  **Drill Through**: Configured on Page 2 targeting `dim_teams.team_name`.
3.  **Sync Slicers**: Sync the tournament year selection between Page 1 and Page 3.
