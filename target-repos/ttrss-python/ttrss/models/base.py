"""
SQLAlchemy DeclarativeBase for all TT-RSS models.

New: no PHP equivalent — SQLAlchemy 2.0 DeclarativeBase infrastructure for ADR-0006.
Single authoritative Base (A-NC-02/03): all model files import from here.
Flask-SQLAlchemy is constructed with model_class=Base so Alembic sees all tables (CG-06).
"""
from sqlalchemy.orm import DeclarativeBase


# New: no PHP equivalent (SQLAlchemy 2.0 DeclarativeBase, ADR-0006)
# Inferred from: ttrss/classes/db/stmt.php (Db_Stmt — query result iteration replaced by SQLAlchemy Result/Row)
class Base(DeclarativeBase):
    pass
