"""A deliberately unsafe query for a classroom code review."""


def lookup(db, name):
    query = f"SELECT name, email FROM members WHERE name = '{name}'"
    return db.execute(query).fetchall()
