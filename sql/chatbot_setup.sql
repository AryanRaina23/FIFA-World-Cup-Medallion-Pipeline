DO $$
BEGIN
IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'chatbot_readonly') THEN
    CREATE ROLE chatbot_readonly WITH LOGIN PASSWORD 'chatbot_readonly_pw';
END IF;
END
$$;

GRANT USAGE ON SCHEMA gold, silver TO chatbot_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO chatbot_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA silver TO chatbot_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO chatbot_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA silver GRANT SELECT ON TABLES TO chatbot_readonly;

CREATE TABLE IF NOT EXISTS metadata.chat_queries (
    query_id SERIAL PRIMARY KEY,
    session_id VARCHAR(50),
    user_question TEXT NOT NULL,
    generated_sql TEXT,
    sql_result JSONB,
    final_answer TEXT,
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

GRANT USAGE ON SCHEMA metadata TO chatbot_readonly;
GRANT SELECT, INSERT ON TABLE metadata.chat_queries TO chatbot_readonly;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA metadata TO chatbot_readonly;
