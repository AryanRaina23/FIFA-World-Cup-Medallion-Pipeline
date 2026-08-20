import os
import csv
import json
import uuid
import datetime
import subprocess
import sys
import psycopg2

def get_connection():
    hosts = ['postgres', 'localhost', '127.0.0.1']
    ports = [5433, 5432]
    for port in ports:
        for host in hosts:
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=host,
                    database='fifa_dw',
                    user='postgres',
                    password='postgres',
                    port=port,
                    connect_timeout=3
                )
                return conn
            except Exception:
                continue
    raise Exception("Unable to connect to PostgreSQL database.")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    teams_json_path = os.path.join(project_root, "data", "sources", "wc_2026_teams.json")
    fixtures_csv_path = os.path.join(project_root, "data", "sources", "wc_2026_fixtures.csv")
    
    print("Reading and modifying sources to simulate incremental data updates...")
    
    # 1. Update wc_2026_teams.json (SCD2 Updates)
    if os.path.exists(teams_json_path):
        with open(teams_json_path, 'r', encoding='utf-8') as f:
            teams = json.load(f)
            
        updated_germany = False
        updated_brazil = False
        
        for team in teams:
            if team['team'] == 'Germany':
                # Change coach (SCD2)
                team['coach'] = 'Jurgen Klopp'
                updated_germany = True
            elif team['team'] == 'Brazil':
                # Change FIFA rank (SCD2)
                team['fifa_rank'] = 3
                updated_brazil = True
                
        if updated_germany and updated_brazil:
            with open(teams_json_path, 'w', encoding='utf-8') as f:
                json.dump(teams, f, indent=4)
            print("Successfully updated Germany's coach to 'Jurgen Klopp' and Brazil's FIFA rank to 3.")
        else:
            print("Could not find Germany or Brazil in teams list.")
    else:
        print(f"Error: {teams_json_path} not found.")

    # 2. Reset and append a new fixture to wc_2026_fixtures.csv (Incremental Ingestion)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    src_fixtures = os.path.join(project_root, "FIFA Dataset", "wc_2026_fixtures.csv")
    if os.path.exists(src_fixtures):
        with open(src_fixtures, 'r', encoding='utf-8') as f_in:
            content = f_in.read()
        
        ends_with_newline = content.endswith('\n') or content.endswith('\r')
        
        with open(fixtures_csv_path, 'w', encoding='utf-8', newline='') as f_out:
            f_out.write(content)
            if not ends_with_newline:
                f_out.write('\n')
                
        new_fixture = [
            "A", "Group Stage", "Mexico", "Canada", "Estadio Azteca", "Mexico City", 
            "Mexico", "2026-06-30", "20:00 ET", "CONCACAF", "15", "Javier Aguirre", 
            "CONCACAF", "30", "Jesse Marsch"
        ]
        with open(fixtures_csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(new_fixture)
        print("Successfully reset and appended new fixture (Mexico vs Canada on 2026-06-30) to wc_2026_fixtures.csv.")
    else:
        print(f"Error: {src_fixtures} not found.")
        
    # 3. Trigger run_pipeline.py for a second run to apply updates
    new_run_id = str(uuid.uuid4())
    print(f"\nTriggering incremental run (Run ID: {new_run_id})...")
    
    script_path = os.path.join(project_root, "scripts", "run_pipeline.py")
    result = subprocess.run([sys.executable, script_path, new_run_id], capture_output=False)
    
    if result.returncode == 0:
        print("\nIncremental run completed successfully!")
        
        # Query DB to show the SCD Type 2 results
        conn = get_connection()
        cur = conn.cursor()
        try:
            print("\n=======================================================")
            print("VERIFYING SCD TYPE 2 IN DATABASE FOR GERMANY & BRAZIL")
            print("=======================================================")
            cur.execute(
                """
                SELECT team_name, fifa_rank, coach, version_number, effective_start_date, effective_end_date, current_flag
                FROM silver.dim_teams_scd2
                WHERE team_name IN ('Germany', 'Brazil')
                ORDER BY team_name, version_number;
                """
            )
            rows = cur.fetchall()
            for r in rows:
                print(f"Team: {r[0]} | Rank: {r[1]} | Coach: {r[2]} | Ver: {r[3]} | Start: {r[4]} | End: {r[5]} | Active: {r[6]}")
                
            print("\n=======================================================")
            print("VERIFYING NEW FIXTURE IN DATABASE")
            print("=======================================================")
            cur.execute(
                """
                SELECT group_letter, stage, team1, team2, venue, fixture_date 
                FROM silver.fixtures
                WHERE team1 = 'Mexico' AND team2 = 'Canada' AND fixture_date = '2026-06-30';
                """
            )
            row = cur.fetchone()
            if row:
                print(f"Fixture: Group {row[0]} | Stage: {row[1]} | Match: {row[2]} vs {row[3]} | Venue: {row[4]} | Date: {row[5]}")
            else:
                print("New fixture was not found in database!")
                
        except Exception as e:
            print(f"Database query failed: {e}")
        finally:
            cur.close()
            conn.close()
    else:
        print("\nIncremental run failed.")

if __name__ == "__main__":
    main()
