import os
import sys
import psycopg2
import pandas as pd

def get_connection():
    hosts = ['postgres', 'localhost', '127.0.0.1']
    for host in hosts:
        try:
            conn = psycopg2.connect(
                host=host,
                database='fifa_dw',
                user='postgres',
                password='postgres',
                port=5432,
                connect_timeout=3
            )
            return conn
        except Exception as e:
            print(f"Connection to host {host} failed: {e}")
            continue
    raise Exception("Unable to connect to PostgreSQL database.")

def log_to_audit(run_id, step_name, table_name, processed, inserted, updated, rejected, status, error_msg=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO metadata.audit_logs 
            (run_id, step_name, table_name, records_processed, records_inserted, records_updated, records_rejected, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (run_id, step_name, table_name, processed, inserted, updated, rejected, status, error_msg)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error writing audit log: {e}")
    finally:
        cur.close()
        conn.close()

def main():
    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not run_id:
        print("Error: run_id must be provided to load_to_gold.py")
        sys.exit(1)
        
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("BEGIN;")
        
        # =====================================================================
        # 1. LOAD DIM_TEAMS (Customer Dimension equivalent)
        # =====================================================================
        # Join active SCD2 team records with confederation lookup names
        print("Loading gold.dim_teams...")
        
        # Clear gold teams and reload from active silver dim teams
        cur.execute("TRUNCATE TABLE gold.dim_teams RESTART IDENTITY CASCADE;")
        
        cur.execute(
            """
            INSERT INTO gold.dim_teams (
                team_name, confederation, confederation_full_name, debut_2026,
                best_wc_result, current_coach, current_fifa_rank, is_active
            )
            SELECT 
                t.team_name,
                t.confederation,
                COALESCE(l.full_name, t.confederation) as confederation_full_name,
                t.debut_2026,
                t.best_wc_result,
                t.coach as current_coach,
                t.fifa_rank as current_fifa_rank,
                t.current_flag as is_active
            FROM silver.dim_teams_scd2 t
            LEFT JOIN silver.lkp_confederations l ON t.confederation = l.confederation
            WHERE t.current_flag = TRUE;
            """
        )
        teams_loaded = cur.rowcount
        print(f"Loaded {teams_loaded} teams to gold.dim_teams.")
        log_to_audit(run_id, "GOLD", "gold.dim_teams", teams_loaded, teams_loaded, 0, 0, "SUCCESS")

        # =====================================================================
        # 2. LOAD DIM_EDITIONS (Product Dimension equivalent)
        # =====================================================================
        print("Loading gold.dim_editions...")
        cur.execute("TRUNCATE TABLE gold.dim_editions RESTART IDENTITY CASCADE;")
        
        cur.execute(
            """
            INSERT INTO gold.dim_editions (
                edition_id, year, host, champion, runner_up, third_place,
                teams_count, matches_count, goals_count, attendance, host_won
            )
            SELECT 
                edition_id, year, host, champion, runner_up, third_place,
                teams_count, matches_count, goals_count, attendance, host_won
            FROM silver.editions;
            """
        )
        editions_loaded = cur.rowcount
        print(f"Loaded {editions_loaded} editions to gold.dim_editions.")
        log_to_audit(run_id, "GOLD", "gold.dim_editions", editions_loaded, editions_loaded, 0, 0, "SUCCESS")

        # =====================================================================
        # 3. LOAD FACT_MATCHES (Sales Fact equivalent)
        # =====================================================================
        # Derived columns: goal_difference, match_winner
        print("Loading gold.fact_matches...")
        cur.execute("TRUNCATE TABLE gold.fact_matches RESTART IDENTITY CASCADE;")
        
        cur.execute(
            """
            INSERT INTO gold.fact_matches (
                edition_year, stage, team1_name, team2_name, score1, score2,
                goal_difference, match_winner, venue, city, country, match_date, notes
            )
            SELECT 
                year as edition_year,
                stage,
                team1 as team1_name,
                team2 as team2_name,
                score1,
                score2,
                ABS(score1 - score2) as goal_difference,
                CASE 
                    WHEN score1 > score2 THEN team1
                    WHEN score2 > score1 THEN team2
                    ELSE 'Draw'
                END as match_winner,
                venue,
                city,
                country,
                match_date,
                notes
            FROM silver.matches;
            """
        )
        matches_loaded = cur.rowcount
        print(f"Loaded {matches_loaded} matches to gold.fact_matches.")
        log_to_audit(run_id, "GOLD", "gold.fact_matches", matches_loaded, matches_loaded, 0, 0, "SUCCESS")

        # =====================================================================
        # 4. LOAD MART_WORLD_CUP_STATS (Revenue Mart equivalent)
        # =====================================================================
        # Derived columns: avg_attendance_per_match, avg_ticket_price_usd, estimated_revenue_usd
        print("Loading gold.mart_world_cup_stats...")
        cur.execute("TRUNCATE TABLE gold.mart_world_cup_stats CASCADE;")
        
        cur.execute(
            """
            INSERT INTO gold.mart_world_cup_stats (
                year, host, champion, total_matches, total_goals, goals_per_match,
                total_attendance, avg_attendance_per_match, avg_ticket_price_usd, estimated_revenue_usd
            )
            SELECT 
                year,
                host,
                champion,
                matches_count as total_matches,
                goals_count as total_goals,
                goals_per_match,
                attendance as total_attendance,
                CASE 
                    WHEN matches_count > 0 THEN ROUND((attendance::float / matches_count)::numeric, 2)
                    ELSE 0
                END as avg_attendance_per_match,
                -- Derived ticket price: rises over time starting at $15 in 1930 up to ~$150 in 2026
                ROUND((15.0 + (year - 1930) * 1.45)::numeric, 2) as avg_ticket_price_usd,
                -- Estimated revenue = total attendance * avg ticket price
                CASE
                    WHEN attendance IS NOT NULL THEN ROUND((attendance * (15.0 + (year - 1930) * 1.45))::numeric, 2)
                    ELSE 0
                END as estimated_revenue_usd
            FROM silver.editions;
            """
        )
        mart_loaded = cur.rowcount
        print(f"Loaded {mart_loaded} rows to gold.mart_world_cup_stats.")
        log_to_audit(run_id, "GOLD", "gold.mart_world_cup_stats", mart_loaded, mart_loaded, 0, 0, "SUCCESS")

        # =====================================================================
        # 5. CREATE WINDOW FUNCTION SCORER VIEW
        # =====================================================================
        print("Creating gold.dim_top_scorers_ranked view (Window Functions)...")
        cur.execute(
            """
            CREATE OR REPLACE VIEW gold.dim_top_scorers_ranked AS
            SELECT 
                edition_id,
                year,
                player,
                country,
                position,
                goals,
                assists,
                penalties,
                matches_played,
                host,
                team_result,
                RANK() OVER (PARTITION BY year ORDER BY goals DESC, assists DESC) as scorer_rank,
                DENSE_RANK() OVER (PARTITION BY year ORDER BY goals DESC) as goals_rank
            FROM silver.top_scorers;
            """
        )

        # =====================================================================
        # 6. LOAD KPI_SUMMARY (KPI Summary equivalent)
        # =====================================================================
        print("Loading gold.kpi_summary...")
        cur.execute("DROP TABLE IF EXISTS gold.kpi_summary CASCADE;")
        cur.execute(
            """
            CREATE TABLE gold.kpi_summary AS
            WITH champion_counts AS (
                SELECT champion, COUNT(*) as titles
                FROM silver.editions
                WHERE champion IS NOT NULL AND champion != '' AND champion != 'nan'
                GROUP BY champion
                ORDER BY titles DESC
                LIMIT 1
            )
            SELECT 
                (SELECT COUNT(DISTINCT edition_id) FROM silver.editions) as total_editions,
                (SELECT SUM(goals_count) FROM silver.editions) as total_goals_scored,
                (SELECT SUM(matches_count) FROM silver.editions) as total_matches_played,
                (SELECT SUM(attendance::bigint) FROM silver.editions WHERE attendance IS NOT NULL) as total_attendance,
                (SELECT COUNT(*) FROM silver.editions WHERE host_won = TRUE) as host_won_count,
                (SELECT champion FROM champion_counts) as most_successful_team,
                (SELECT titles FROM champion_counts) as most_successful_titles;
            """
        )
        print("Loaded KPI summary.")
        log_to_audit(run_id, "GOLD", "gold.kpi_summary", 1, 1, 0, 0, "SUCCESS")

        # Export Gold tables to local CSV files to show the Gold Layer in the workspace
        base_dir = os.environ.get("AIRFLOW_HOME", r"D:\UserFiles\Desktop\FIFA World Cup Pipeline PoC")
        gold_dir = os.path.join(base_dir, "data", "gold")
        os.makedirs(gold_dir, exist_ok=True)
        gold_tables = ["dim_teams", "dim_editions", "fact_matches", "mart_world_cup_stats", "kpi_summary"]
        for tbl in gold_tables:
            try:
                gdf = pd.read_sql_query(f"SELECT * FROM gold.{tbl};", conn)
                gdf.to_csv(os.path.join(gold_dir, f"{tbl}.csv"), index=False, encoding='utf-8')
                print(f"Exported local backup for gold.{tbl} to {gold_dir}")
            except Exception as ex:
                print(f"Warning: could not export local backup for gold.{tbl}: {ex}")
        
        # Also export the view dim_top_scorers_ranked
        try:
            gdf = pd.read_sql_query("SELECT * FROM gold.dim_top_scorers_ranked;", conn)
            gdf.to_csv(os.path.join(gold_dir, "dim_top_scorers_ranked.csv"), index=False, encoding='utf-8')
            print(f"Exported local backup for gold.dim_top_scorers_ranked to {gold_dir}")
        except Exception as ex:
            print(f"Warning: could not export local backup for gold.dim_top_scorers_ranked: {ex}")

        conn.commit()
        print("\nGold layer load completed successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"Gold load failed: {e}")
        log_to_audit(run_id, "GOLD", "all_tables", 0, 0, 0, 0, "FAILED", str(e))
        cur.close()
        conn.close()
        sys.exit(1)
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
