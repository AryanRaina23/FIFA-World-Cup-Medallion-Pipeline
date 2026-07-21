import os
import sys
import uuid
import datetime
import subprocess
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

def update_run_status(run_id, status, duration=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        if duration is not None:
            cur.execute(
                """
                UPDATE metadata.pipeline_runs
                SET status = %s, end_time = %s, execution_time_seconds = %s
                WHERE run_id = %s;
                """,
                (status, datetime.datetime.now(), duration, run_id)
            )
        else:
            cur.execute(
                """
                UPDATE metadata.pipeline_runs
                SET status = %s
                WHERE run_id = %s;
                """,
                (status, run_id)
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error updating run status: {e}")
    finally:
        cur.close()
        conn.close()

def run_script(script_name, run_id):
    script_path = os.path.join("D:\\UserFiles\\Desktop\\FIFA World Cup Pipeline PoC\\scripts", script_name)
    
    # If running inside docker container, we can adjust paths
    if not os.path.exists(script_path):
        script_path = os.path.join("/opt/airflow/scripts", script_name)
        
    print(f"\n=======================================================")
    print(f"RUNNING STEP: {script_name} (Run ID: {run_id})")
    print(f"=======================================================")
    
    result = subprocess.run([sys.executable, script_path, run_id], capture_output=False)
    if result.returncode != 0:
        print(f"ERROR: {script_name} failed with return code {result.returncode}")
        return False
    return True

def main():
    run_id = sys.argv[1] if len(sys.argv) > 1 else str(uuid.uuid4())
    start_time = datetime.datetime.now()
    
    print(f"Starting FIFA Pipeline PoC. Run ID: {run_id}")
    
    steps = [
        "ingest_to_bronze.py",
        "validate_bronze.py",
        "load_to_silver.py",
        "load_to_gold.py"
    ]
    
    success = True
    for step in steps:
        if not run_script(step, run_id):
            success = False
            break
            
    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if success:
        print(f"\nPipeline execution SUCCESS! Duration: {duration:.2f} seconds.")
        update_run_status(run_id, "SUCCESS", duration)
    else:
        print(f"\nPipeline execution FAILED!")
        update_run_status(run_id, "FAILED", duration)
        sys.exit(1)

if __name__ == "__main__":
    main()
