"""Database connections and ORM models.

The :mod:`src.database` package centralizes all database access for the
project. It exposes :class:`~src.database.connection.DatabaseConnection`
for creating sessions and houses the SQLAlchemy models that define the
schema. See ``README.md`` in this directory for an overview of table
relationships and migration workflow.
"""