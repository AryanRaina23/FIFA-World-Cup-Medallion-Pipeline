# Power BI Dashboard Visualizations & Configuration Guide

This guide details how to refine and configure your 3-page Power BI dashboard report using the conformed tables in your Neon cloud PostgreSQL database. It maps your pages to standard Data Analyst perspectives (Sales, Profit, and Forecast equivalents) and details the implementation of navigations, drills, and alerts.

---

## 📐 Report Design Structure (3 Pages)

| Page Name | Analyst Perspective | Purpose | Core Visuals |
| :--- | :--- | :--- | :--- |
| **Page 1: Historical Analysis** | **Sales Page (Volume)** | Tracks tournament growth, total attendance, match counts, and historical host distributions. | 3 KPI Cards, 1 Donut Chart, 1 Combo Chart, 1 Treemap. |
| **Page 2: Squad Intel & Golden Boot** | **Profit Page (Efficiency)** | Analyzes team-level performance, coach details, confederation stats, and goal scorer efficiency. | 3 KPI Cards, 1 Slicer, 1 Horizontal Bar Chart, 1 Funnel, 1 Stage Column Chart, 1 Q&A Prompt. |
| **Page 3: Honors & Commercials** | **Forecast Page (Commercial)** | Visualizes revenue trends, average ticket pricing, Ballon d'Or winners, and award distributions. | 1 Hyperlink, 2 Tables, 1 Line Chart, 1 Area/Bar Chart. |

---

## 🛠️ Step-by-Step Configuration Requirements

### 1. Headers & Page Navigation (All Pages)
*   **Header**: On the top of each page, add a clean dark banner (height ~80px) with the page title in gold (`#f59e0b`).
*   **Page Navigation (2 Navigations)**: 
    *   Insert two **Button** shapes (e.g. Left/Right arrows or blocks) at the top right of each header.
    *   In the **Format Button** pane, turn on **Action**.
    *   Set **Type** to **Page Navigation** and set **Destination** to the target page (e.g., on Page 1, set buttons to navigate to `Page 2` and `Page 3`).

### 2. Slicers & Synced Slicers
*   **1 Local Slicer**: On **Page 2 (Squad Intel)**, add a dropdown Slicer containing `dim_teams.team_name`.
*   **1 Synced Slicer**:
    *   Add a **Year Slicer** (from `dim_editions.year`) on **Page 1** and **Page 3**.
    *   On the top ribbon, go to **View** $\rightarrow$ select **Sync Slicers**.
    *   In the Sync Slicers pane on the right, check the **Sync** checkbox (the circular arrows icon) and the **Visible** checkbox (the eye icon) for both **Page 1** and **Page 3**.
    *   *Result*: Filtering the tournament year on Page 1 will automatically sync the year and filter the commercial revenue charts on Page 3.

### 3. Hyperlink (Page 3 Header)
*   Create a text box or button in the header of Page 3 with the text **`Chatbot 💬`**.
*   In the formatting pane:
    *   Turn on **Action**.
    *   Set **Type** to **Web URL**.
    *   Paste your live Vercel URL: **`https://fifa-world-cup-medallion-pipeline.vercel.app/`**
    *   *Result*: Mentors clicking this link will open your AI Chatbot immediately in their browser.

### 4. Visualizations (5 Core Charts)
*   **Line Chart (Page 3)**: "Goals Scored Over Time" (X-axis: `year`, Y-axis: `goals_count` from `gold.dim_editions`).
*   **Bar Chart (Page 2)**: "Top Scorers" (Y-axis: `player`, X-axis: `goals` from `gold.dim_top_scorers_ranked`).
*   **Pie/Donut Chart (Page 1)**: "Count of Year by Champion" (Legend: `champion`, Values: Count of `year` from `gold.dim_editions`).
*   **Funnel Chart (Page 2)**: "Team Name by Confederation" (Group: `confederation`, Values: Count of `team_name` from `gold.dim_teams`).
*   **Combo Chart (Page 1)**: "Sum of Attendance and Goals by Year" (X-axis: `year`, Column Y-axis: `attendance`, Line Y-axis: `goals_count`).

### 5. Natural Language Prompt Visual (Page 2)
*   Add a **Q&A Visual** (found in the Visualizations pane) to the bottom right of Page 2.
*   *Result*: This provides a natural language prompt box directly inside the report where mentors can ask questions like *"who won in 2010"* and see the chart render instantly.

### 6. Drill Operations (3 Drill Types)
*   **Drill Down & Drill Up (Page 1)**: 
    *   On the **Combo Chart**, add a hierarchy to the X-axis: `confederation` $\rightarrow$ `team_name`.
    *   Enable the drill-down icon (the single down arrow on the visual header). Mentors clicking on `UEFA` will drill down to see the individual European teams' attendance stats. Clicking the up arrow drills back up.
*   **Drill Through (Page 2 Target)**:
    *   Go to **Page 2 (Squad Intel)**. In the Visualizations pane under **Drillthrough**, drag `dim_teams.team_name` into the **"Add drill-through fields here"** box.
    *   *Result*: Now, mentors can go to Page 1, right-click on any team in a table or chart, select **Drill through** $\rightarrow$ **Page 2**, and Power BI will navigate to Page 2 automatically filtered to that specific team.

### 7. Alert Mechanisms (2 Alerts)
*   **Alert 1: Data Quarantine warning (Data Quality)**:
    *   Create a **Card Visual** on Page 1 or Page 3 showing the count of quarantined/rejected records (e.g. `Count of rejected_id` from `bronze.rejected_records`).
    *   Select the card, go to **Format Visual** $\rightarrow$ **Callout value** $\rightarrow$ click the **fx** button next to Color.
    *   Set conditional formatting: If value is `0`, color is green. If value is `> 0`, color is bright **Red**, alerting viewers that corrupt data has been quarantined.
*   **Alert 2: Low-Performance/Low-Ranking alert**:
    *   In the "Ballon d'Or Winners" table on Page 3, select the `year` or `player` column.
    *   Go to **Cell elements** in the Visualizations pane $\rightarrow$ turn on **Icons**.
    *   Configure rules: Add a yellow warning triangle or red circle next to any row where `year` matches a cancellation milestone (such as 2020 where it says *"COVID-19 pandemic cancellation"*).

---

## 🔍 Specific Fixes for your Dashboard (Based on Screenshots)

### 🚨 Fix 1: Page 2 KPI Card displaying "25K FIFA Rank"
*   **The Issue**: In Screenshot 3, the card for **FIFA Rank** displays **"25K"**. This is because Power BI is summing the FIFA rank values of all teams since the slicer is set to "All".
*   **The Fix**:
    1.  Select the **FIFA Rank Card** visual on Page 2.
    2.  In the Fields well, click the dropdown arrow next to the `current_fifa_rank` field.
    3.  Change the aggregation from **Sum** to **Average** (or **Minimum**).
    4.  Go to the formatting pane $\rightarrow$ **Callout value** $\rightarrow$ set **Display units** from *Auto* to **None**.
    *   *Result*: It will now display as a clean single number (e.g., `25`) when a team is selected, or a reasonable average rank when looking at all teams.

### 🚨 Fix 2: Clean up the Slicer Title on Page 2
*   **The Issue**: The slicer on Page 2 is labeled **"Team Name"** but is currently filtered by the table column `team_name` under an unformatted heading.
*   **The Fix**: Select the slicer, go to the formatting pane $\rightarrow$ **Slicer settings** $\rightarrow$ **Slicer header**, and set the text size to `10pt` and style to semi-bold to match the dark background theme.
