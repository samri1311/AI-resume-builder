#update_ats_table.py
import sqlite3

DB_PATH = "resumes.db"  # change if your DB name is different


def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table});")
    columns = [col[1] for col in cursor.fetchall()]
    return column in columns


def add_column(cursor, table, column_def):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def};")
        print(f"✅ Added column: {column_def}")
    except Exception as e:
        print(f"⚠️ Skipped {column_def} → {e}")


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    table = "ats_scores"

    # 🔥 Columns to add
    new_columns = {
        "ats_score": "FLOAT",
        "similarity_score": "FLOAT",
        "skill_match_score": "FLOAT",
        "matched_skills": "JSON"
    }

    for col, col_type in new_columns.items():
        if not column_exists(cursor, table, col):
            add_column(cursor, table, f"{col} {col_type}")
        else:
            print(f"✔ Column already exists: {col}")

    conn.commit()
    conn.close()

    print("\n🚀 Table updated successfully!")


if __name__ == "__main__":
    main()