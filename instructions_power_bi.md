# Power BI Dashboard Connection and Design Guide

This guide provides step-by-step instructions on how to connect Microsoft Power BI Desktop to your FIFA World Cup Gold Data Warehouse and build an interactive, professional dashboard.

---

## 1. Prerequisites & Database Details
Your data warehouse is running locally inside a Docker container. When configuring the connection, use the following credentials:

- **Data Source Type**: PostgreSQL Database
- **Server**: `localhost` (or `127.0.0.1:5432` if standard porting is required)
- **Database**: `fifa_dw`
- **Authentication Method**: Database (Username/Password)
  - **Username**: `postgres`
  - **Password**: `postgres`
- **SSL / Encryption**: Disabled (uncheck "Encrypt Connection" in Power BI if prompted, since the local container does not use SSL certificates).

> [!NOTE]
> If Power BI prompts that it requires a data source developer library (e.g. Npgsql), you can install the **Npgsql GAC installation package** or configure a local **ODBC Connection** mapping to PostgreSQL.

---

## 2. Connecting Power BI to the Gold Warehouse

Follow these steps to import your analytics-ready datasets:

1. Open **Power BI Desktop**.
2. On the **Home** tab, click **Get Data** $\rightarrow$ **More...**
3. Select **Database** $\rightarrow$ **PostgreSQL database**, and click **Connect**.
4. In the dialog box:
   - **Server**: `localhost:5432`
   - **Database**: `fifa_dw`
   - **Data Connectivity Mode**: Select **Import** (recommended for performance and interactive filtering).
5. Click **OK**.
6. When prompted for credentials, select the **Database** tab on the left:
   - **User name**: `postgres`
   - **Password**: `postgres`
   - Click **Connect**.
7. In the **Navigator** window, expand the schemas. Look for the `gold` schema tables:
   - Check `dim_teams` (Customer equivalent)
   - Check `dim_editions` (Product equivalent)
   - Check `fact_matches` (Sales Fact equivalent)
   - Check `mart_world_cup_stats` (Revenue Mart equivalent)
   - Check `dim_top_scorers_ranked` (Ranked Scorers View)
   - Check `kpi_summary` (Summary Table)
8. Click **Load** to import the data into Power BI.

---

## 3. Data Modeling & Relationships

Once the tables are loaded, navigate to the **Model View** (the icon with three boxes on the left sidebar) to establish relationships. Create the following connections by dragging fields from one table to another:

| Active | Fact / Dimension | Join Column | Target Dimension | Target Column | Cardinality | Filter Direction |
|:---:|:---|:---|:---|:---|:---:|:---:|
| **Yes** | `fact_matches` | `edition_year` | `dim_editions` | `year` | Many-to-One (`* -> 1`) | Single |
| **Yes** | `dim_top_scorers_ranked` | `edition_id` | `dim_editions` | `edition_id` | Many-to-One (`* -> 1`) | Single |
| **Yes** | `mart_world_cup_stats` | `year` | `dim_editions` | `year` | One-to-One (`1 -> 1`) | Both |
| **Yes** | `fact_matches` | `team1_name` | `dim_teams` | `team_name` | Many-to-One (`* -> 1`) | Single |
| *No* | `fact_matches` | `team2_name` | `dim_teams` | `team_name` | Many-to-One (`* -> 1`) | Single |

> [!TIP]
> Since a match involves two teams (`team1_name` and `team2_name`), only one active relationship can exist between `fact_matches` and `dim_teams`. Keep the relationship with `team1_name` active, and the relationship with `team2_name` inactive. You can use the DAX function `USERELATIONSHIP` in measures to analyze team2 stats where needed.

---

## 4. Designing the Dashboard Pages

We recommend building a three-page interactive dashboard to showcase the data engineering results:

### Page 1: Historical World Cup Analysis (General Overview)
This page gives a macro view of the tournament's evolution from 1930 to 2022.

- **KPI Cards (using `kpi_summary`)**:
  - Total World Cup Editions: `total_editions`
  - Total Goals Scored: `total_goals_scored`
  - Total Matches Played: `total_matches_played`
  - Total Global Attendance: `total_attendance` (Format as Million/Billion)
- **Combo Chart (Line and Clustered Column)**:
  - **X-Axis**: `year` (from `mart_world_cup_stats`)
  - **Column y-axis**: `total_attendance`
  - **Line y-axis**: `total_goals`
  - *Insight*: Shows how the tournament expanded in size and goal count over time.
- **Geographic Map Visual**:
  - **Location**: `host` (from `dim_editions`)
  - **Bubble Size**: Count of `edition_id`
  - *Insight*: Displays which countries have hosted the World Cup most frequently.
- **Tree Map (Most Titles)**:
  - **Category**: `champion` (from `dim_editions`)
  - **Values**: Count of `year`
  - *Insight*: Visual comparison of title distribution (Brazil, Germany, Italy, Uruguay, etc.).

---

### Page 2: Team Performance & Goal Scorers (Sales & Product equivalent)
This page drills down into team performance and legendary top scorers.

- **Slicer (Filter)**:
  - Select World Cup Year (Dropdown selection from `dim_editions.year`).
- **Bar Chart (Top Goal Scorers)**:
  - **Y-Axis**: `player` (from `dim_top_scorers_ranked`)
  - **X-Axis**: `goals`
  - **Tooltip/Legend**: `country`, `position`
  - *Insight*: Shows who won the Golden Boot in each edition (e.g. Just Fontaine scoring 13 in 1958).
- **KPI Card (Top Goal Count)**:
  - Display the name and goals of the top scorer of the selected year.
- **Scatter Plot (FIFA Rank vs Best Result)**:
  - **X-Axis**: `current_fifa_rank` (from `dim_teams`)
  - **Y-Axis**: `best_wc_result`
  - *Insight*: Evaluates whether a team's current FIFA ranking correlates with their historically best finish.

---

### Page 3: Revenue & Match Statistics (Revenue Mart)
Demonstrates the business/financial insights of the World Cup.

- **KPI Cards**:
  - **Estimated Total Revenue**: Sum of `estimated_revenue_usd` from `mart_world_cup_stats` (Format as Currency in USD).
  - **Average Attendance per Match**: Sum of `avg_attendance_per_match`.
- **Area Chart (Revenue Growth)**:
  - **X-Axis**: `year`
  - **Y-Axis**: `estimated_revenue_usd`
  - *Insight*: Demonstrates the massive growth in tickets revenue from early days to the modern multi-million dollar business.
- **Heatmap Matrix (Match Matrix)**:
  - **Rows**: `team1_name`
  - **Columns**: `team2_name`
  - **Values**: Average of `goal_difference`
  - *Insight*: Visualizes matchups that historically result in high goal margins.

---

## 5. Connecting and Refreshing Data
Since the pipeline is fully orchestrated by Airflow and supports incremental loading:
1. Whenever the Airflow pipeline runs and ingests new data (e.g. 2026 fixtures updates), the `gold` tables are updated in PostgreSQL.
2. In Power BI Desktop, simply click the **Refresh** button on the Home ribbon.
3. Power BI will query the PostgreSQL container, fetch the updated fact/dimension tables, and update all visuals, charts, and metrics automatically.
