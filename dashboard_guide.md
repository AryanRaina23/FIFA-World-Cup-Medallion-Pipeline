# Power BI Dashboard Report Walkthrough

This document provides a walkthrough of the 3-page interactive Power BI dashboard report designed for the **FIFA World Cup Data Pipeline & AI Chatbot** project. It outlines the purpose of each page, the specific visualizations present, and the interactive analytical features built for end-users.

---

## 📊 Dashboard Page Structure

### Page 1: FIFA World Cup History (Sales/Volume Page)
This page provides a macro, historical analysis of the tournament's evolution from its inception in 1930 to 2026.

*   **Header Section**: Contains the title banner **"FIFA World Cup History"** and two page navigation buttons linking to Page 2 and Page 3.
*   **KPI Cards**:
    *   **Total Matches**: `1K` matches played.
    *   **Total Attendance**: `50M` global ticketed attendance.
    *   **Total Goals**: `3K` total goals scored.
*   **Visualizations**:
    *   **World Cup Titles by Nation (Donut Chart)**: Visualizes the proportion of championships won by each country (e.g. Brazil with 5, Italy with 4, Germany with 4, Argentina with 3).
    *   **Attendance & Goals Trend Over Time (Combo Line & Column Chart)**: Compares total ticket sales (columns) against goals scored (line) across tournament editions, highlighting historical expansion trends.
    *   **Goal Scoring History by Champion (Stacked Column Chart)**: Displays total goals scored over time, colored by the winning nation.
    *   **World Cup Hosts (Treemap)**: Compares bubble-sizes representing the frequency of countries hosting the World Cup.

---

### Page 2: Squad Intel & Golden Boot (Profit/Efficiency Page)
This page provides a micro-level drill down to analyze team performances, coaching parameters, and player-level goal scoring efficiency.

*   **Interactive Slicer**: A **"Team Name"** dropdown filter allowing users to focus on a single participating country (e.g., Brazil, France, England).
*   **Squad KPI Cards**:
    *   **Current Coach**: Displays the conformed coach name (or `--` when multiple teams are selected).
    *   **FIFA Rank**: Displays the team's current rank (or `--` when multiple teams are selected).
    *   **Best WC Finish**: Displays the team's best historical result (or `--` when multiple teams are selected).
*   **Visualizations**:
    *   **All-Time Top Goal Scorers (Horizontal Bar Chart)**: Lists the tournament's all-time goals leaders (e.g. Mbappé, Messi, Klose, Ronaldo) sorted descending.
    *   **Participating Teams by Confederation (Funnel Chart)**: Displays the representation of squads grouped by continental confederations (UEFA, CAF, AFC, etc.).
    *   **Goal Differential by Tournament Stage (Column Chart)**: Bridges goals scored in Group Stages vs. Quarter-finals, Semi-finals, and Finals.
    *   **Q&A Prompt Visual**: A native natural language query prompt box allowing users to ask questions and see charts generate instantly.

---

### Page 3: World Cup Honors & Commercial Forecasts (Forecast Page)
Exhibits the tournament's commercial revenue forecasts, historical accolades, and links directly to the AI Agent.

*   **AI Agent Hyperlink**: A clickable **"Chatbot 💬"** link in the header pointing to the live serverless React chatbot application.
*   **Visualizations**:
    *   **Ballon d'Or Winners (Horizontal Bar Chart)**: Tracks player accolades by the number of awards won (e.g. Lionel Messi leading with 8, Cristiano Ronaldo with 5).
    *   **Tournament Award Winners List (Table)**: A tabular registry recording the Year, Award Type (e.g. Golden Ball, Golden Glove), Winner, and Country.
    *   **Goals Scored Over Time (Line Chart)**: Tracks the progression of total goals scored per edition.
    *   **Attendance vs Ticket Price Trends (Combo Line & Column Chart)**: Visualizes historical ticket prices (line) against total attendance (columns) to show commercial growth.

---

## ⚡ Interactive & Data Engineering Features

1.  **Page Navigation**: Action-bound buttons in the headers allow smooth navigation across the three report pages.
2.  **Synced Slicers**: The year selection filter is synchronized between Page 1 and Page 3 to maintain user context.
3.  **Drill Down/Up**: Interactive drill down is enabled on the Page 1 combo chart to let users expand from confederation-level summaries down to individual team attendance.
4.  **Drill Through**: Users can right-click any team name on Page 1, select *Drill through*, and jump directly to the Page 2 *Squad Intel* dashboard pre-filtered to that country.
5.  **Data Quality Alert Card**: A conditional-formatting KPI card displaying the count of quarantined rows. It remains green when zero, and flashes bright **Red** if any corrupt data is rejected.
