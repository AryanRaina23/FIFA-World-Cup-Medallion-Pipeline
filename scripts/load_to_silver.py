import os
import sys
import datetime
import pandas as pd
import psycopg2

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
        except Exception:
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

def parse_edition_dates(row):
    # Parses start_date/end_date and combines with year. E.g. "July 13" + 1930 -> 1930-07-13
    year = row['year']
    start_str = row['start_date'].strip()
    end_str = row['end_date'].strip()
    
    # helper to convert month-day to date
    def to_date_str(md_str):
        try:
            dt = pd.to_datetime(f"{md_str}, {year}", format='%B %d, %Y')
            return dt.date()
        except Exception:
            try:
                # Try format like 'July 13, 1930'
                dt = pd.to_datetime(md_str)
                return dt.date()
            except Exception:
                return None
                
    return to_date_str(start_str), to_date_str(end_str)

def main():
    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not run_id:
        print("Error: run_id must be provided to load_to_silver.py")
        sys.exit(1)
        
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        today = datetime.date.today()
        
        # =====================================================================
        # 1. PROCESS EDITIONS
        # =====================================================================
        print("Processing editions...")
        cur.execute(
            """
            SELECT r.* FROM bronze.editions_raw r
            JOIN bronze.valid_records v ON r._ingestion_id = v.ingestion_id
            WHERE r._run_id = %s AND v.run_id = %s;
            """,
            (run_id, run_id)
        )
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        ed_inserted, ed_updated = 0, 0
        if rows:
            df = pd.DataFrame(rows, columns=colnames)
            for _, r in df.iterrows():
                # Casts
                ed_id = int(float(r['edition']))
                year = int(float(r['year']))
                teams_count = int(float(r['teams'])) if r['teams'] else None
                matches_count = int(float(r['matches'])) if r['matches'] else None
                goals_count = int(float(r['goals'])) if r['goals'] else None
                goals_per = float(r['goals_per_match']) if r['goals_per_match'] else None
                att = int(float(r['attendance'].replace(',', '').strip())) if r['attendance'] and r['attendance'] != 'nan' else None
                top_goals = int(float(r['top_scorer_goals'])) if r['top_scorer_goals'] and r['top_scorer_goals'] != 'nan' else None
                host_won = True if str(r['host_won']).strip().lower() == 'yes' else False
                
                # Parse dates
                start_dt, end_dt = parse_edition_dates({
                    'year': year,
                    'start_date': r['start_date'],
                    'end_date': r['end_date']
                })
                
                # Upsert into silver.editions
                cur.execute(
                    """
                    INSERT INTO silver.editions (
                        edition_id, year, host, champion, runner_up, third_place, fourth_place,
                        teams_count, matches_count, goals_count, goals_per_match, attendance,
                        top_scorer, top_scorer_country, top_scorer_goals, start_date, end_date,
                        final_city, host_won, format
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (edition_id) DO UPDATE SET
                        year = EXCLUDED.year, host = EXCLUDED.host, champion = EXCLUDED.champion,
                        runner_up = EXCLUDED.runner_up, third_place = EXCLUDED.third_place,
                        fourth_place = EXCLUDED.fourth_place, teams_count = EXCLUDED.teams_count,
                        matches_count = EXCLUDED.matches_count, goals_count = EXCLUDED.goals_count,
                        goals_per_match = EXCLUDED.goals_per_match, attendance = EXCLUDED.attendance,
                        top_scorer = EXCLUDED.top_scorer, top_scorer_country = EXCLUDED.top_scorer_country,
                        top_scorer_goals = EXCLUDED.top_scorer_goals, start_date = EXCLUDED.start_date,
                        end_date = EXCLUDED.end_date, final_city = EXCLUDED.final_city,
                        host_won = EXCLUDED.host_won, format = EXCLUDED.format;
                    """,
                    (
                        ed_id, year, r['host'].strip(), r['champion'].strip(), r['runner_up'].strip(),
                        r['third_place'].strip(), r['fourth_place'].strip(), teams_count, matches_count,
                        goals_count, goals_per, att, r['top_scorer'].strip(), r['top_scorer_country'].strip(),
                        top_goals, start_dt, end_dt, r['final_city'].strip(), host_won, r['format'].strip()
                    )
                )
                
                # Check if it was insert or update
                if cur.statusmessage.startswith("INSERT 0 1"):
                    ed_inserted += 1
                else:
                    ed_updated += 1
            print(f"Editions: {ed_inserted} inserted, {ed_updated} updated.")
            log_to_audit(run_id, "SILVER", "silver.editions", len(df), ed_inserted, ed_updated, 0, "SUCCESS")

        # =====================================================================
        # 2. PROCESS MATCHES
        # =====================================================================
        print("Processing matches...")
        cur.execute(
            """
            SELECT r.* FROM bronze.matches_raw r
            JOIN bronze.valid_records v ON r._ingestion_id = v.ingestion_id
            WHERE r._run_id = %s AND v.run_id = %s;
            """,
            (run_id, run_id)
        )
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        m_inserted, m_updated = 0, 0
        if rows:
            df = pd.DataFrame(rows, columns=colnames)
            for _, r in df.iterrows():
                # Casts
                year = int(float(r['year']))
                s1 = int(float(r['score1'])) if r['score1'] and r['score1'] != 'nan' else 0
                s2 = int(float(r['score2'])) if r['score2'] and r['score2'] != 'nan' else 0
                match_dt = pd.to_datetime(r['date'].strip()).date() if r['date'] and r['date'] != 'nan' else None
                notes = r['notes'].strip() if r['notes'] and r['notes'] != 'nan' else None
                
                # Check for existing record to decide insert/update
                cur.execute(
                    """
                    SELECT match_id FROM silver.matches 
                    WHERE year = %s AND match_date = %s AND team1 = %s AND team2 = %s;
                    """,
                    (year, match_dt, r['team1'].strip(), r['team2'].strip())
                )
                exist_row = cur.fetchone()
                if exist_row:
                    cur.execute(
                        """
                        UPDATE silver.matches SET
                            stage = %s, score1 = %s, score2 = %s, venue = %s, city = %s,
                            country = %s, notes = %s
                        WHERE match_id = %s;
                        """,
                        (r['stage'].strip(), s1, s2, r['venue'].strip(), r['city'].strip(), r['country'].strip(), notes, exist_row[0])
                    )
                    m_updated += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO silver.matches (
                            year, stage, team1, score1, score2, team2, venue, city, country, match_date, notes
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            year, r['stage'].strip(), r['team1'].strip(), s1, s2, r['team2'].strip(),
                            r['venue'].strip(), r['city'].strip(), r['country'].strip(), match_dt, notes
                        )
                    )
                    m_inserted += 1
            print(f"Matches: {m_inserted} inserted, {m_updated} updated.")
            log_to_audit(run_id, "SILVER", "silver.matches", len(df), m_inserted, m_updated, 0, "SUCCESS")

        # =====================================================================
        # 3. PROCESS FIXTURES
        # =====================================================================
        print("Processing fixtures...")
        cur.execute(
            """
            SELECT r.* FROM bronze.fixtures_raw r
            JOIN bronze.valid_records v ON r._ingestion_id = v.ingestion_id
            WHERE r._run_id = %s AND v.run_id = %s;
            """,
            (run_id, run_id)
        )
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        f_inserted, f_updated = 0, 0
        if rows:
            df = pd.DataFrame(rows, columns=colnames)
            for _, r in df.iterrows():
                f_date = pd.to_datetime(r['date'].strip()).date() if r['date'] and r['date'] != 'nan' else None
                t1_rank = int(float(r['team1_fifa_rank'])) if r['team1_fifa_rank'] and r['team1_fifa_rank'] != 'nan' else None
                t2_rank = int(float(r['team2_fifa_rank'])) if r['team2_fifa_rank'] and r['team2_fifa_rank'] != 'nan' else None
                
                # Check for existing record
                cur.execute(
                    """
                    SELECT fixture_id FROM silver.fixtures 
                    WHERE fixture_date = %s AND team1 = %s AND team2 = %s;
                    """,
                    (f_date, r['team1'].strip(), r['team2'].strip())
                )
                exist_row = cur.fetchone()
                if exist_row:
                    cur.execute(
                        """
                        UPDATE silver.fixtures SET
                            group_letter = %s, stage = %s, venue = %s, city = %s, country = %s,
                            kickoff_et = %s, team1_confederation = %s, team1_fifa_rank = %s,
                            team1_coach = %s, team2_confederation = %s, team2_fifa_rank = %s,
                            team2_coach = %s
                        WHERE fixture_id = %s;
                        """,
                        (
                            r['group'].strip(), r['stage'].strip(), r['venue'].strip(), r['city'].strip(), r['country'].strip(),
                            r['kickoff_et'].strip(), r['team1_confederation'].strip(), t1_rank, r['team1_coach'].strip(),
                            r['team2_confederation'].strip(), t2_rank, r['team2_coach'].strip(), exist_row[0]
                        )
                    )
                    f_updated += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO silver.fixtures (
                            group_letter, stage, team1, team2, venue, city, country, fixture_date, kickoff_et,
                            team1_confederation, team1_fifa_rank, team1_coach, team2_confederation, team2_fifa_rank, team2_coach
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            r['group'].strip(), r['stage'].strip(), r['team1'].strip(), r['team2'].strip(),
                            r['venue'].strip(), r['city'].strip(), r['country'].strip(), f_date, r['kickoff_et'].strip(),
                            r['team1_confederation'].strip(), t1_rank, r['team1_coach'].strip(),
                            r['team2_confederation'].strip(), t2_rank, r['team2_coach'].strip()
                        )
                    )
                    f_inserted += 1
            print(f"Fixtures: {f_inserted} inserted, {f_updated} updated.")
            log_to_audit(run_id, "SILVER", "silver.fixtures", len(df), f_inserted, f_updated, 0, "SUCCESS")

        # =====================================================================
        # 4. PROCESS TOP SCORERS
        # =====================================================================
        print("Processing top scorers...")
        cur.execute(
            """
            SELECT r.* FROM bronze.top_scorers_raw r
            JOIN bronze.valid_records v ON r._ingestion_id = v.ingestion_id
            WHERE r._run_id = %s AND v.run_id = %s;
            """,
            (run_id, run_id)
        )
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        ts_inserted, ts_updated = 0, 0
        if rows:
            df = pd.DataFrame(rows, columns=colnames)
            for _, r in df.iterrows():
                ed_id = int(float(r['edition']))
                year = int(float(r['year']))
                goals = int(float(r['goals']))
                assists = int(float(r['assists'])) if r['assists'] and r['assists'] != 'nan' else 0
                pens = int(float(r['penalties'])) if r['penalties'] and r['penalties'] != 'nan' else 0
                matches_pl = int(float(r['matches_played'])) if r['matches_played'] and r['matches_played'] != 'nan' else None
                
                # Check for existing record
                cur.execute(
                    """
                    SELECT scorer_id FROM silver.top_scorers 
                    WHERE edition_id = %s AND player = %s;
                    """,
                    (ed_id, r['player'].strip())
                )
                exist_row = cur.fetchone()
                if exist_row:
                    cur.execute(
                        """
                        UPDATE silver.top_scorers SET
                            year = %s, country = %s, position = %s, goals = %s, assists = %s,
                            penalties = %s, matches_played = %s, host = %s, team_result = %s
                        WHERE scorer_id = %s;
                        """,
                        (
                            year, r['country'].strip(), r['position'].strip(), goals, assists,
                            pens, matches_pl, r['host'].strip(), r['team_result'].strip(), exist_row[0]
                        )
                    )
                    ts_updated += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO silver.top_scorers (
                            edition_id, year, player, country, position, goals, assists, penalties, matches_played, host, team_result
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            ed_id, year, r['player'].strip(), r['country'].strip(), r['position'].strip(), goals, assists,
                            pens, matches_pl, r['host'].strip(), r['team_result'].strip()
                        )
                    )
                    ts_inserted += 1
            print(f"Top Scorers: {ts_inserted} inserted, {ts_updated} updated.")
            log_to_audit(run_id, "SILVER", "silver.top_scorers", len(df), ts_inserted, ts_updated, 0, "SUCCESS")

        # =====================================================================
        # 5. PROCESS TEAMS WITH SCD TYPE 2
        # =====================================================================
        print("Processing teams (SCD Type 2)...")
        cur.execute(
            """
            SELECT r.* FROM bronze.teams_raw r
            JOIN bronze.valid_records v ON r._ingestion_id = v.ingestion_id
            WHERE r._run_id = %s AND v.run_id = %s;
            """,
            (run_id, run_id)
        )
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        scd_inserted, scd_updated = 0, 0
        if rows:
            df = pd.DataFrame(rows, columns=colnames)
            for _, r in df.iterrows():
                team_name = r['team'].strip()
                group_let = r['group'].strip() if r['group'] and r['group'] != 'nan' else None
                confed = r['confederation'].strip() if r['confederation'] and r['confederation'] != 'nan' else None
                rank = int(float(r['fifa_rank'])) if r['fifa_rank'] and r['fifa_rank'] != 'nan' else None
                coach = r['coach'].strip() if r['coach'] and r['coach'] != 'nan' else None
                best_res = r['best_wc_result'].strip() if r['best_wc_result'] and r['best_wc_result'] != 'nan' else None
                debut = True if str(r['debut_2026']).strip().lower() == 'yes' else False
                
                # Look up existing active record
                cur.execute(
                    """
                    SELECT team_key, fifa_rank, coach, version_number, group_letter, confederation, best_wc_result, debut_2026
                    FROM silver.dim_teams_scd2
                    WHERE team_name = %s AND current_flag = TRUE;
                    """,
                    (team_name,)
                )
                active_record = cur.fetchone()
                
                if active_record is None:
                    # New team: insert version 1
                    cur.execute(
                        """
                        INSERT INTO silver.dim_teams_scd2 (
                            team_name, group_letter, confederation, fifa_rank, coach, best_wc_result, debut_2026,
                            effective_start_date, effective_end_date, current_flag, version_number
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '9999-12-31', TRUE, 1);
                        """,
                        (team_name, group_let, confed, rank, coach, best_res, debut, today)
                    )
                    scd_inserted += 1
                else:
                    t_key, old_rank, old_coach, old_ver, old_group, old_conf, old_best, old_debut = active_record
                    
                    # SCD Type 2 Attributes: fifa_rank, coach
                    if old_rank != rank or old_coach != coach:
                        print(f"SCD2 CHANGE DETECTED for {team_name}: Rank {old_rank}->{rank}, Coach '{old_coach}'->'{coach}'")
                        # 1. Close current record
                        cur.execute(
                            """
                            UPDATE silver.dim_teams_scd2 SET
                                effective_end_date = %s,
                                current_flag = FALSE
                            WHERE team_key = %s;
                            """,
                            (today - datetime.timedelta(days=1), t_key)
                        )
                        
                        # 2. Insert new record
                        cur.execute(
                            """
                            INSERT INTO silver.dim_teams_scd2 (
                                team_name, group_letter, confederation, fifa_rank, coach, best_wc_result, debut_2026,
                                effective_start_date, effective_end_date, current_flag, version_number
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '9999-12-31', TRUE, %s);
                            """,
                            (team_name, group_let, confed, rank, coach, best_res, debut, today, old_ver + 1)
                        )
                        scd_updated += 1
                    else:
                        # SCD Type 1 attributes change only (non-SCD2, like group) or no change
                        if old_group != group_let or old_conf != confed or old_best != best_res or old_debut != debut:
                            cur.execute(
                                """
                                UPDATE silver.dim_teams_scd2 SET
                                    group_letter = %s,
                                    confederation = %s,
                                    best_wc_result = %s,
                                    debut_2026 = %s
                                WHERE team_key = %s;
                                """,
                                (group_let, confed, best_res, debut, t_key)
                            )
                            # Simple update in place
                            scd_updated += 1
            print(f"Teams SCD2: {scd_inserted} versions inserted, {scd_updated} closed & updated.")
            log_to_audit(run_id, "SILVER", "silver.dim_teams_scd2", len(df), scd_inserted, scd_updated, 0, "SUCCESS")

        # Export Silver tables to local CSV files to show the Silver Layer in the workspace
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        base_dir = os.environ.get("AIRFLOW_HOME", project_root)
        silver_dir = os.path.join(base_dir, "data", "silver")
        os.makedirs(silver_dir, exist_ok=True)
        silver_tables = ["editions", "matches", "fixtures", "top_scorers", "dim_teams_scd2", "lkp_confederations"]
        for tbl in silver_tables:
            try:
                sdf = pd.read_sql_query(f"SELECT * FROM silver.{tbl};", conn)
                sdf.to_csv(os.path.join(silver_dir, f"{tbl}.csv"), index=False, encoding='utf-8')
                print(f"Exported local backup for silver.{tbl} to {silver_dir}")
            except Exception as ex:
                print(f"Warning: could not export local backup for silver.{tbl}: {ex}")

        conn.commit()
        print("\nSilver layer load completed successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"Silver load failed: {e}")
        log_to_audit(run_id, "SILVER", "all_tables", 0, 0, 0, 0, "FAILED", str(e))
        cur.close()
        conn.close()
        sys.exit(1)
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
