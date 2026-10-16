"""Borra TODAS las tablas de la base de DATABASE_URL y las crea de nuevo con el esquema actual.

Sirve cuando el esquema cambió (por ejemplo, al pasar de clientes y roles a cuentas de Google) y la base todavía
tiene las tablas viejas, porque create_all solo crea tablas que no existen: no modifica las existentes.

Uso:  python reset_db.py --si      (sin --si solo muestra qué haría)
"""
import sys

from sqlalchemy import inspect, text

import models  # noqa: F401  (registra todas las tablas)
from database import Base, engine

# Tablas de versiones anteriores que ya no existen en los modelos
TABLAS_VIEJAS = ["codigos_verificacion", "clientes"]


def main() -> None:
    existentes = inspect(engine).get_table_names()
    print(f"Base: {engine.url.render_as_string(hide_password=True)}")
    print(f"Tablas actuales: {', '.join(sorted(existentes)) or '(ninguna)'}")
    if "--si" not in sys.argv:
        print("No se borró nada. Ejecuta 'python reset_db.py --si' para borrar todo y recrear las tablas.")
        return

    with engine.begin() as conexion:
        for tabla in existentes:
            if tabla in TABLAS_VIEJAS or tabla in Base.metadata.tables:
                conexion.execute(text(f'DROP TABLE IF EXISTS "{tabla}" CASCADE'))
    Base.metadata.create_all(bind=engine)
    print(f"Listo. Tablas nuevas: {', '.join(sorted(inspect(engine).get_table_names()))}")


if __name__ == "__main__":
    main()
