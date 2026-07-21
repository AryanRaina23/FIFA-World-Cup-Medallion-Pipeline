import os
import sys
import json
import uuid
import datetime
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

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

def main():
    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not run_id:
        print("Error: run_id must be provided to validate_bronze.py")
        sys.exit(1)
        
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Create tracking table for valid record keys
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bronze.valid_records (
                run_id VARCHAR(50),
                table_name VARCHAR(100),
                ingestion_id VARCHAR(50),
                PRIMARY KEY (run_id, table_name, ingestion_id)
            );
            """
        )
        conn.commit()
        
        tables = ["teams", "fixtures", "editions", "matches", "top_scorers"]
        
        for table in tables:
            print(f"\nValidating bronze.{table}_raw records for run {run_id}")
            
            # Fetch raw data for current run
            cur.execute(f"SELECT * FROM bronze.{table}_raw WHERE _run_id = %s;", (run_id,))
            colnames = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            if not rows:
                print(f"No records found for table {table} with run_id {run_id}")
                continue
                
            df = pd.DataFrame(rows, columns=colnames)
            total_records = len(df)
            
            valid_ids = []
            rejected_records = [] # tuple of (run_id, table_name, record_json, reason)
            
            # Set to track duplicates for this batch
            seen_pks = set()
            
            for index, row in df.iterrows():
                row_dict = row.to_dict()
                ingest_id = row_dict.get('_ingestion_id')
                reasons = []
                
                # Table-specific validations
                if table == "teams":
                    # PK Null check
                    team_name = row_dict.get('team', '').strip()
                    if not team_name or team_name.lower() == 'none' or team_name.lower() == 'nan':
                        reasons.append("Primary key 'team' is null or empty.")
                    
                    # Duplicate check
                    elif team_name.lower() in seen_pks:
                        reasons.append(f"Duplicate team '{team_name}' detected in current batch.")
                    else:
                        seen_pks.add(team_name.lower())
                    
                    # Data type check: fifa_rank
                    fifa_rank_str = row_dict.get('fifa_rank', '').strip()
                    if fifa_rank_str and fifa_rank_str.lower() != 'none' and fifa_rank_str.lower() != 'nan':
                        try:
                            rank = int(float(fifa_rank_str))
                            if rank < 1:
                                reasons.append(f"FIFA Rank must be positive: {fifa_rank_str}")
                        except ValueError:
                            reasons.append(f"FIFA Rank is not a valid integer: '{fifa_rank_str}'")
                            
                elif table == "fixtures":
                    t1 = row_dict.get('team1', '').strip()
                    t2 = row_dict.get('team2', '').strip()
                    date_str = row_dict.get('date', '').strip()
                    
                    if not t1 or t1.lower() == 'nan':
                        reasons.append("Field 'team1' is null or empty.")
                    if not t2 or t2.lower() == 'nan':
                        reasons.append("Field 'team2' is null or empty.")
                    if not date_str or date_str.lower() == 'nan':
                        reasons.append("Field 'date' is null or empty.")
                        
                    # Duplicate check: date + team1 + team2
                    fixture_key = (date_str, t1.lower(), t2.lower())
                    if fixture_key in seen_pks:
                        reasons.append(f"Duplicate fixture for teams {t1} vs {t2} on {date_str}.")
                    else:
                        seen_pks.add(fixture_key)
                        
                elif table == "editions":
                    ed_str = row_dict.get('edition', '').strip()
                    yr_str = row_dict.get('year', '').strip()
                    
                    if not ed_str or ed_str.lower() == 'nan':
                        reasons.append("Primary key 'edition' is null or empty.")
                    if not yr_str or yr_str.lower() == 'nan':
                        reasons.append("Primary key 'year' is null or empty.")
                    else:
                        try:
                            yr = int(float(yr_str))
                            if yr < 1930 or yr > 2030:
                                reasons.append(f"Year {yr} is outside valid World Cup timeframe (1930-2030).")
                        except ValueError:
                            reasons.append(f"Year is not a valid integer: '{yr_str}'")
                            
                    # Duplicate check
                    if ed_str.lower() in seen_pks:
                        reasons.append(f"Duplicate edition number '{ed_str}' detected.")
                    else:
                        seen_pks.add(ed_str.lower())
                        
                elif table == "matches":
                    yr_str = row_dict.get('year', '').strip()
                    t1 = row_dict.get('team1', '').strip()
                    t2 = row_dict.get('team2', '').strip()
                    score1_str = row_dict.get('score1', '').strip()
                    score2_str = row_dict.get('score2', '').strip()
                    date_str = row_dict.get('date', '').strip()
                    
                    if not yr_str or yr_str.lower() == 'nan':
                        reasons.append("Field 'year' is null or empty.")
                    if not t1 or t1.lower() == 'nan':
                        reasons.append("Field 'team1' is null or empty.")
                    if not t2 or t2.lower() == 'nan':
                        reasons.append("Field 'team2' is null or empty.")
                        
                    # Score validations
                    try:
                        s1 = int(float(score1_str)) if score1_str and score1_str.lower() != 'nan' else 0
                        if s1 < 0:
                            reasons.append(f"Score1 cannot be negative: {s1}")
                    except ValueError:
                        reasons.append(f"Score1 is not a valid integer: '{score1_str}'")
                        
                    try:
                        s2 = int(float(score2_str)) if score2_str and score2_str.lower() != 'nan' else 0
                        if s2 < 0:
                            reasons.append(f"Score2 cannot be negative: {s2}")
                    except ValueError:
                        reasons.append(f"Score2 is not a valid integer: '{score2_str}'")
                        
                    # Duplicate check
                    match_key = (yr_str, date_str, t1.lower(), t2.lower())
                    if match_key in seen_pks:
                        reasons.append(f"Duplicate match record for {t1} vs {t2} on {date_str} ({yr_str}).")
                    else:
                        seen_pks.add(match_key)
                        
                elif table == "top_scorers":
                    ed_str = row_dict.get('edition', '').strip()
                    player = row_dict.get('player', '').strip()
                    goals_str = row_dict.get('goals', '').strip()
                    
                    if not ed_str or ed_str.lower() == 'nan':
                        reasons.append("Field 'edition' is null or empty.")
                    if not player or player.lower() == 'nan':
                        reasons.append("Field 'player' is null or empty.")
                        
                    try:
                        goals = int(float(goals_str)) if goals_str and goals_str.lower() != 'nan' else 0
                        if goals <= 0:
                            reasons.append(f"Top scorer must have positive goals count: {goals}")
                    except ValueError:
                        reasons.append(f"Goals count is not a valid integer: '{goals_str}'")
                        
                    # Duplicate check
                    scorer_key = (ed_str, player.lower())
                    if scorer_key in seen_pks:
                        reasons.append(f"Duplicate top scorer '{player}' in edition '{ed_str}'.")
                    else:
                        seen_pks.add(scorer_key)
                
                # Check outcome
                if reasons:
                    # Write to rejected records list
                    rejection_reason = " | ".join(reasons)
                    
                    # Remove DB metadata columns from JSON representation for cleaner logging
                    cleaned_row = {k: v for k, v in row_dict.items() if not k.startswith('_')}
                    record_json = json.dumps(cleaned_row)
                    
                    rejected_records.append((run_id, f"bronze.{table}_raw", record_json, rejection_reason))
                else:
                    valid_ids.append((run_id, f"bronze.{table}_raw", ingest_id))
            
            # Write to database (valid records list & rejected records)
            if valid_ids:
                cur.execute("BEGIN;")
                execute_values(
                    cur,
                    "INSERT INTO bronze.valid_records (run_id, table_name, ingestion_id) VALUES %s ON CONFLICT DO NOTHING;",
                    valid_ids
                )
                conn.commit()
                
            if rejected_records:
                cur.execute("BEGIN;")
                execute_values(
                    cur,
                    "INSERT INTO bronze.rejected_records (run_id, table_name, record_data, rejection_reason) VALUES %s;",
                    rejected_records
                )
                conn.commit()
                
            valid_count = len(valid_ids)
            rejected_count = len(rejected_records)
            print(f"Validation summary for {table}: {valid_count} Valid, {rejected_count} Rejected.")
            log_to_audit(run_id, "VALIDATION", f"bronze.{table}_raw", total_records, valid_count, 0, rejected_count, "SUCCESS")
            
    except Exception as e:
        conn.rollback()
        print(f"Validation failed: {e}")
        log_to_audit(run_id, "VALIDATION", "all_tables", 0, 0, 0, 0, "FAILED", str(e))
        cur.close()
        conn.close()
        sys.exit(1)
        
    cur.close()
    conn.close()
    print("\nData validation step completed successfully.")

if __name__ == "__main__":
    main()
