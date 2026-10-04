from sqlalchemy.orm import Session

from models.cliente import Cliente
from models.cotizacion import Cotizacion
from models.tarifa import Tarifa
from services.catalogo import ROLES
from services.cotizador import aplicar_analisis, recalcular
from services.propuesta import generar_propuesta

# Costo interno por hora (COP) de cada rol
TARIFAS = dict(zip(ROLES, [55_000, 50_000, 45_000, 40_000, 60_000, 65_000]))

CLIENTES = [
    ("Marcela Duarte", "Café Andino S.A.S.", "marcela@cafeandino.example.com", "3001234567"),
    ("Julián Vargas", "Clínica Dental Sonríe", "julian@sonrie.example.com", "3109876543"),
    ("Paola Restrepo", "Boutique Aurora", "paola@aurora.example.com", None),
]

# (índice de cliente, título, alcance, estado final)
COTIZACIONES = [
    (0, "Tienda en línea de café",
     "Necesitamos una tienda en línea con catálogo de productos, carrito de compras y pagos en línea con tarjeta y PSE. "
     "Debe tener un panel de administración para gestionar pedidos, facturación electrónica y reportes de ventas. "
     "Los clientes deben iniciar sesión y recibir notificaciones por correo de cada pedido.",
     "aceptada"),
    (1, "Sistema de citas para clínica",
     "Sistema de reservas de citas con calendario, usuarios y roles para recepcionistas y doctores, "
     "notificaciones por WhatsApp y correo, y reportes mensuales. Un sitio web informativo.",
     "enviada"),
    (2, "App móvil y catálogo para boutique",
     "Aplicación móvil para mostrar el catálogo de productos, con login de clientes, carrito de compras, "
     "pagos en línea y un panel de administración. Integraciones con redes sociales.",
     "rechazada"),
    (0, "Plataforma de reportes y chat con clientes",
     "Un portal avanzado de reportes con tablero de indicadores en tiempo real y chat de soporte con clientes. "
     "Autenticación con roles y permisos, y carga de archivos.",
     "borrador"),
]


def hay_datos(db: Session) -> bool:
    return any(db.query(m).first() for m in (Cliente, Tarifa, Cotizacion))


def borrar_todo(db: Session) -> None:
    for c in db.query(Cotizacion).all():
        db.delete(c)
    db.flush()
    db.query(Cliente).delete()
    db.query(Tarifa).delete()
    db.commit()


def cargar_datos_demo(db: Session) -> dict:
    for rol, valor in TARIFAS.items():
        db.add(Tarifa(rol=rol, valor_hora=valor))
    clientes = [Cliente(nombre=n, empresa=e, email=m, telefono=t) for n, e, m, t in CLIENTES]
    db.add_all(clientes)
    db.flush()

    for indice, titulo, alcance, estado in COTIZACIONES:
        cot = Cotizacion(cliente_id=clientes[indice].id, titulo=titulo, descripcion_alcance=alcance)
        db.add(cot)
        db.flush()
        aplicar_analisis(cot)
        recalcular(db, cot)
        if estado != "borrador":
            db.flush()
            cot.propuesta = generar_propuesta(cot)
            cot.estado = estado
    db.commit()
    return {"tarifas": len(TARIFAS), "clientes": len(CLIENTES), "cotizaciones": len(COTIZACIONES)}
