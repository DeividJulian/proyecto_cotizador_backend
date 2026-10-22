"""Example quotes so a new user can see how the app works with real data."""
from sqlalchemy.orm import Session

from models.quote import Quote
from models.user import User
from services.proposal import build_proposal
from services.quoting import apply_analysis, recalculate

# (who it is for, company, title, scope, final status)
EXAMPLES = [
    ("Marcela Duarte", "Café Andino S.A.S.", "Tienda en línea de café",
     "Necesitamos una tienda en línea con catálogo de productos, carrito de compras y pagos en línea con tarjeta y PSE. "
     "Debe tener un panel de administración para gestionar pedidos, facturación electrónica y reportes de ventas. "
     "Los clientes deben iniciar sesión y recibir notificaciones por correo de cada pedido.",
     "accepted"),
    ("Julián Vargas", "Clínica Dental Sonríe", "Sistema de citas para clínica",
     "Sistema de reservas de citas con calendario, usuarios y roles para recepcionistas y doctores, "
     "notificaciones por WhatsApp y correo, y reportes mensuales. Un sitio web informativo.",
     "sent"),
    ("Paola Restrepo", "Boutique Aurora", "App móvil y catálogo para boutique",
     "Aplicación móvil para mostrar el catálogo de productos, con login de clientes, carrito de compras, "
     "pagos en línea y un panel de administración. Integraciones con redes sociales.",
     "rejected"),
    (None, None, "Plataforma de reportes y chat con clientes",
     "Un portal avanzado de reportes con tablero de indicadores en tiempo real y chat de soporte con clientes. "
     "Autenticación con roles y permisos, y carga de archivos.",
     "draft"),
]


def has_quotes(db: Session, user_id: int) -> bool:
    return db.query(Quote).filter(Quote.user_id == user_id).first() is not None


def delete_quotes(db: Session, user_id: int) -> None:
    for quote in db.query(Quote).filter(Quote.user_id == user_id).all():
        db.delete(quote)
    db.flush()


def load_examples(db: Session, user: User) -> dict:
    """Creates the example quotes with the user's rates. Raises MissingRate if the user deleted one."""
    for name, company, title, scope, status in EXAMPLES:
        quote = Quote(user_id=user.id, title=title, scope_description=scope, client_name=name, client_company=company)
        db.add(quote)
        db.flush()
        apply_analysis(quote)
        recalculate(db, quote)
        if status != "draft":
            db.flush()
            quote.proposal = build_proposal(quote)
            quote.status = status
    db.commit()
    return {"quotes": len(EXAMPLES)}
