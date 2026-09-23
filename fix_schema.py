# fix_schema.py
"""One-off repair script: brings resumes.db in line with
backend/database/models.py without re-running CREATE TABLE on anything
that already exists.

Why this is needed: this database was never fully under Alembic's control -
some of migration 0002's changes (the certifications/awards tables) were
already applied by hand at some point, but others (users.website,
resumes.title, education.details) were not. That mismatch is why both
`alembic upgrade head` (tried to recreate existing tables) and
`alembic stamp 0001` + `upgrade head` (same problem, one step later) failed.

This script checks each expected column/table individually via SQLite's
own introspection (PRAGMA table_info / sqlite_master) and only adds what's
actually missing - safe to run more than once. It finishes by stamping
Alembic's version table to '0002' (head) directly, so `alembic upgrade
head` will correctly report "already up to date" afterward instead of
tripping over the same tables again.

Run once from the project root, with your venv active:
    python fix_schema.py
"""
import sqlite3

DB_PATH = "resumes.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()


def existing_columns(table):
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def table_exists(table):
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


# --- users.website ---
if "website" not in existing_columns("users"):
    print("Adding users.website ...")
    cur.execute("ALTER TABLE users ADD COLUMN website VARCHAR")
else:
    print("users.website already present, skipping.")

# --- resumes.title ---
if "title" not in existing_columns("resumes"):
    print("Adding resumes.title ...")
    cur.execute("ALTER TABLE resumes ADD COLUMN title VARCHAR")
else:
    print("resumes.title already present, skipping.")

# --- education.details ---
if "details" not in existing_columns("education"):
    print("Adding education.details ...")
    cur.execute("ALTER TABLE education ADD COLUMN details TEXT")
else:
    print("education.details already present, skipping.")

# --- certifications table ---
if not table_exists("certifications"):
    print("Creating certifications table ...")
    cur.execute("""
        CREATE TABLE certifications (
            id INTEGER NOT NULL PRIMARY KEY,
            resume_id INTEGER,
            name VARCHAR NOT NULL,
            issuing_organization VARCHAR,
            year VARCHAR,
            FOREIGN KEY(resume_id) REFERENCES resumes (id)
        )
    """)
else:
    print("certifications table already present, skipping.")

# --- awards table ---
if not table_exists("awards"):
    print("Creating awards table ...")
    cur.execute("""
        CREATE TABLE awards (
            id INTEGER NOT NULL PRIMARY KEY,
            resume_id INTEGER,
            title VARCHAR NOT NULL,
            year VARCHAR,
            FOREIGN KEY(resume_id) REFERENCES resumes (id)
        )
    """)
else:
    print("awards table already present, skipping.")

conn.commit()

# --- make sure Alembic agrees the DB is now at head (0002) ---
if not table_exists("alembic_version"):
    cur.execute(
        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, "
        "PRIMARY KEY (version_num))"
    )
    cur.execute("INSERT INTO alembic_version (version_num) VALUES ('0002')")
    print("Created alembic_version table, stamped at 0002.")
else:
    cur.execute("DELETE FROM alembic_version")
    cur.execute("INSERT INTO alembic_version (version_num) VALUES ('0002')")
    print("Stamped alembic_version at 0002.")

conn.commit()
conn.close()

print("Done - resumes.db schema is now in sync with backend/database/models.py.")
