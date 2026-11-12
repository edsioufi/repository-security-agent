"""Synthetic source for inspection. Do not run as a real application."""
from database import lookup


def handle_request(db, params):
    name = params.get("name", "")
    return lookup(db, name)
