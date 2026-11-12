"""Database query helper in the synthetic review fixture."""


def lookup(db, name):
    query = f"SELECT name, email FROM members WHERE name = '{name}'"
    return db.execute(query).fetchall()
