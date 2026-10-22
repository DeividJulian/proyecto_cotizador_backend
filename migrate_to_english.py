"""One-time migration of the data saved before the code moved to English names (October 2026).

It keeps every account, rate and quote. It changes:
- code values to English: statuses (borrador -> draft...), complexities (baja -> low...), item source (ia -> ai);
- texts shown to the user back to Spanish: role names, categories, module names and reasons;
- the JSON of each quote: the analysis is run again and the estimate, the financials and the proposal are
  recalculated, so their keys follow the new names. The items and numbers chosen by the user are kept.

It can run more than once: already migrated rows stay as they are.
Usage:  python migrate_to_english.py        (shows what it would change)
        python migrate_to_english.py --yes  (applies the changes)
"""
import re
import sys

import models  # noqa: F401  (registers every table)
from database import Base, SessionLocal, engine
from models.quote import Quote, QuoteItem
from models.rate import Rate
from services.finance import MissingRate
from services.proposal import build_proposal
from services.quoting import recalculate
from services.scope import analyze_scope

STATUS = {"borrador": "draft", "enviada": "sent", "aceptada": "accepted", "rechazada": "rejected"}
COMPLEXITY = {"baja": "low", "media": "medium", "alta": "high"}
SOURCE = {"ia": "ai"}
ROLES = {"UX/UI Design": "Diseño UX/UI", "Project Management": "Gestión de proyecto"}
CATEGORIES = {
    "Core": "Núcleo", "Business": "Negocio", "Analytics": "Análisis", "Communication": "Comunicación",
    "Integration": "Integración", "Platforms": "Plataformas", "Intelligence": "Inteligencia", "Content": "Contenido",
    "Cross-cutting": "Transversal", "Custom": "Personalizado",
}
NAMES = {
    "Authentication and user management": "Autenticación y gestión de usuarios",
    "Admin panel": "Panel administrativo",
    "Product catalog and inventory": "Catálogo e inventario de productos",
    "Shopping cart and online payments": "Carrito de compras y pagos en línea",
    "Bookings and appointment scheduling": "Reservas y agenda de citas",
    "Electronic invoicing": "Facturación electrónica",
    "Reports and KPI dashboards": "Reportes y tableros de indicadores",
    "Email, SMS or WhatsApp notifications": "Notificaciones por correo, SMS o WhatsApp",
    "Real-time chat and messaging": "Chat y mensajería en tiempo real",
    "Integration with external systems": "Integración con sistemas externos",
    "Mobile app": "Aplicación móvil",
    "Artificial intelligence and recommendations": "Inteligencia artificial y recomendaciones",
    "Content management and blog": "Gestión de contenidos y blog",
    "File upload and management": "Carga y gestión de archivos",
    "Maps and geolocation": "Mapas y geolocalización",
    "Multi-language support": "Soporte de varios idiomas",
    "Advanced security and auditing": "Seguridad avanzada y auditoría",
    "Corporate website": "Sitio web institucional",
    "Data migration and import": "Migración e importación de datos",
    "Testing and quality assurance": "Pruebas y control de calidad",
    "Project management": "Gestión del proyecto",
    "Deployment and go-live": "Despliegue y puesta en producción",
}
REASONS = {
    "the description calls it complex or large-scale": "la descripción lo califica como complejo o de gran escala",
    "the description calls it simple or basic": "la descripción lo califica como sencillo o básico",
    "it is mentioned in several parts of the scope": "se menciona en varias partes del alcance",
    "the project as a whole is described as complex": "el proyecto en general se describe como complejo",
    "the project as a whole is described as simple or a prototype": "el proyecto en general se describe como sencillo o un prototipo",
    "no signs of special complexity": "sin indicios de complejidad especial",
    "Added manually": "Agregado manualmente",
    "Adjusted manually": "Ajustado manualmente",
}
_SHARE = re.compile(r"^(\d+)% of development hours \(minimum (\d+) h\)$")


def _reasons(text: str) -> str:
    match = _SHARE.match(text or "")
    if match:
        return f"{match.group(1)} % de las horas de desarrollo (mínimo {match.group(2)} h)"
    return "; ".join(REASONS.get(part.strip(), part.strip()) for part in (text or "").split(";")) if text else text


def migrate(db) -> list[str]:
    changes: list[str] = []

    for rate in db.query(Rate).all():
        new_role = ROLES.get(rate.role)
        if new_role and not db.query(Rate).filter(Rate.user_id == rate.user_id, Rate.role == new_role).first():
            changes.append(f"rate {rate.id}: {rate.role} -> {new_role}")
            rate.role = new_role
    db.flush()

    for item in db.query(QuoteItem).all():
        before = (item.name, item.category, item.complexity, item.source, item.reasons, dict(item.split or {}))
        item.name = NAMES.get(item.name, item.name)
        item.category = CATEGORIES.get(item.category, item.category)
        item.complexity = COMPLEXITY.get(item.complexity, item.complexity)
        item.source = SOURCE.get(item.source, item.source)
        item.reasons = _reasons(item.reasons)
        item.split = {ROLES.get(role, role): share for role, share in (item.split or {}).items()}
        if before != (item.name, item.category, item.complexity, item.source, item.reasons, item.split):
            changes.append(f"item {item.id}: {before[0]} -> {item.name}")
    db.flush()

    for quote in db.query(Quote).all():
        old_status = quote.status
        quote.status = STATUS.get(quote.status, quote.status)
        if "modules" not in (quote.analysis or {}):
            quote.analysis = analyze_scope(quote.scope_description)
        try:
            recalculate(db, quote)
        except MissingRate as e:
            changes.append(f"quote {quote.id}: not recalculated ({e})")
            continue
        if quote.proposal and quote.items:
            db.flush()
            quote.proposal = build_proposal(quote)
        changes.append(f"quote {quote.id}: status {old_status} -> {quote.status}, analysis and totals recalculated")
    return changes


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print(f"Database: {engine.url.render_as_string(hide_password=True)}")
    with SessionLocal() as db:
        changes = migrate(db)
        for line in changes:
            print(" -", line)
        if "--yes" in sys.argv:
            db.commit()
            print(f"Done: {len(changes)} changes saved.")
        else:
            db.rollback()
            print(f"{len(changes)} changes found. Nothing was saved: run 'python migrate_to_english.py --yes'.")


if __name__ == "__main__":
    main()
