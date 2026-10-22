"""Deletes EVERY table of the DATABASE_URL database and creates them again with the current schema.

Only for a schema change that migrate_to_english.py cannot handle: create_all only creates missing tables,
it never changes existing ones. It deletes all the data.

Usage:  python reset_db.py --si      (without --si it only shows what it would do)
"""
import sys

from sqlalchemy import inspect, text

import models  # noqa: F401  (registers every table)
from database import Base, engine

# Tables of older versions that are no longer in the models
OLD_TABLES = ["clientes"]


def main() -> None:
    existing = inspect(engine).get_table_names()
    print(f"Base: {engine.url.render_as_string(hide_password=True)}")
    print(f"Tablas actuales: {', '.join(sorted(existing)) or '(ninguna)'}")
    if "--si" not in sys.argv:
        print("No se borró nada. Ejecuta 'python reset_db.py --si' para borrar todo y recrear las tablas.")
        return

    cascade = " CASCADE" if engine.dialect.name == "postgresql" else ""  # SQLite does not support it
    with engine.begin() as connection:
        for table in existing:
            if table in OLD_TABLES or table in Base.metadata.tables:
                connection.execute(text(f'DROP TABLE IF EXISTS "{table}"{cascade}'))
    Base.metadata.create_all(bind=engine)
    print(f"Listo. Tablas nuevas: {', '.join(sorted(inspect(engine).get_table_names()))}")


if __name__ == "__main__":
    main()
