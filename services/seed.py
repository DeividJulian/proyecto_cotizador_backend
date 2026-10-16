"""Cotizaciones de ejemplo para que un usuario nuevo vea cómo funciona la app con datos reales."""
from sqlalchemy.orm import Session

from models.cotizacion import Cotizacion
from models.usuario import Usuario
from services.cotizador import aplicar_analisis, recalcular
from services.propuesta import generar_propuesta

# (para quién es, empresa, título, alcance, estado final)
EJEMPLOS = [
    ("Marcela Duarte", "Café Andino S.A.S.", "Tienda en línea de café",
     "Necesitamos una tienda en línea con catálogo de productos, carrito de compras y pagos en línea con tarjeta y PSE. "
     "Debe tener un panel de administración para gestionar pedidos, facturación electrónica y reportes de ventas. "
     "Los clientes deben iniciar sesión y recibir notificaciones por correo de cada pedido.",
     "aceptada"),
    ("Julián Vargas", "Clínica Dental Sonríe", "Sistema de citas para clínica",
     "Sistema de reservas de citas con calendario, usuarios y roles para recepcionistas y doctores, "
     "notificaciones por WhatsApp y correo, y reportes mensuales. Un sitio web informativo.",
     "enviada"),
    ("Paola Restrepo", "Boutique Aurora", "App móvil y catálogo para boutique",
     "Aplicación móvil para mostrar el catálogo de productos, con login de clientes, carrito de compras, "
     "pagos en línea y un panel de administración. Integraciones con redes sociales.",
     "rechazada"),
    (None, None, "Plataforma de reportes y chat con clientes",
     "Un portal avanzado de reportes con tablero de indicadores en tiempo real y chat de soporte con clientes. "
     "Autenticación con roles y permisos, y carga de archivos.",
     "borrador"),
]


def tiene_cotizaciones(db: Session, usuario_id: int) -> bool:
    return db.query(Cotizacion).filter(Cotizacion.usuario_id == usuario_id).first() is not None


def borrar_cotizaciones(db: Session, usuario_id: int) -> None:
    for c in db.query(Cotizacion).filter(Cotizacion.usuario_id == usuario_id).all():
        db.delete(c)
    db.flush()


def cargar_ejemplos(db: Session, usuario: Usuario) -> dict:
    """Crea las cotizaciones de ejemplo con las tarifas del usuario. Lanza TarifaFaltante si borró alguna."""
    for nombre, empresa, titulo, alcance, estado in EJEMPLOS:
        cot = Cotizacion(
            usuario_id=usuario.id, titulo=titulo, descripcion_alcance=alcance, cliente_nombre=nombre, cliente_empresa=empresa
        )
        db.add(cot)
        db.flush()
        aplicar_analisis(cot)
        recalcular(db, cot)
        if estado != "borrador":
            db.flush()
            cot.propuesta = generar_propuesta(cot)
            cot.estado = estado
    db.commit()
    return {"cotizaciones": len(EJEMPLOS)}
