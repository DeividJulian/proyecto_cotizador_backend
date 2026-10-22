"""Catalog of typical software modules, with base hours and the split of work by role.

Module and role names are shown to the user, so they are in Spanish. Keywords cover Spanish and English
descriptions (they are compared without accents and in lower case).
"""

ROLE_BACKEND = "Backend"
ROLE_FRONTEND = "Frontend"
ROLE_DESIGN = "Diseño UX/UI"
ROLE_QA = "QA"
ROLE_DEVOPS = "DevOps"
ROLE_PM = "Gestión de proyecto"

ROLES = [ROLE_BACKEND, ROLE_FRONTEND, ROLE_DESIGN, ROLE_QA, ROLE_DEVOPS, ROLE_PM]

# Category of the work that is calculated as a percentage of development (QA, management, deployment)
CROSS_CUTTING = "Transversal"
# Category of the items the user adds by hand
CUSTOM = "Personalizado"

# Hours multiplier by detected complexity
COMPLEXITY_FACTORS = {"low": 0.7, "medium": 1.0, "high": 1.6}

# (optimistic, pessimistic) multipliers over the most likely hours: the basis of the PERT estimate
PERT_RANGE = {"low": (0.85, 1.30), "medium": (0.80, 1.50), "high": (0.75, 1.90)}

HIGH_SIGNALS = [
    "complejo", "compleja", "avanzado", "avanzada", "tiempo real", "alta concurrencia", "miles de usuarios",
    "varios sistemas", "multiempresa", "escalable", "alto volumen", "a gran escala",
    "complex", "advanced", "real time", "real-time", "high concurrency", "thousands of users", "multiple systems",
    "multi-tenant", "scalable", "high volume", "large scale",
]
LOW_SIGNALS = [
    "sencillo", "sencilla", "basico", "basica", "simple", "prototipo", "mvp", "minimo viable",
    "basic", "prototype", "minimum viable", "small",
]

DEFAULT_SPLIT = {ROLE_BACKEND: 0.5, ROLE_FRONTEND: 0.4, ROLE_DESIGN: 0.1}

# Cross-cutting work: percentage of the development hours and a minimum of hours
CROSS_CUTTING_WORK = [
    {"name": "Pruebas y control de calidad", "role": ROLE_QA, "share": 0.20, "minimum": 8},
    {"name": "Gestión del proyecto", "role": ROLE_PM, "share": 0.12, "minimum": 8},
    {"name": "Despliegue y puesta en producción", "role": ROLE_DEVOPS, "share": 0.08, "minimum": 8},
]

MODULES = {
    "authentication": {
        "name": "Autenticación y gestión de usuarios", "category": "Núcleo", "hours": 40,
        "keywords": ["login", "inicio de sesion", "iniciar sesion", "inicien sesion", "cuentas de usuario",
                     "registro de usuarios", "usuarios y roles", "roles y permisos", "autenticacion",
                     "perfiles de usuario", "permisos",
                     "log in", "sign in", "sign up", "user accounts", "authentication", "user registration",
                     "roles and permissions", "user profiles", "permissions"],
        "split": {ROLE_BACKEND: 0.5, ROLE_FRONTEND: 0.35, ROLE_DESIGN: 0.15},
    },
    "admin_panel": {
        "name": "Panel administrativo", "category": "Núcleo", "hours": 60,
        "keywords": ["panel administrativo", "panel de administracion", "backoffice", "back office",
                     "dashboard administrativo", "administrador del sistema", "modulo administrativo",
                     "admin panel", "admin dashboard", "administration panel", "admin area"],
        "split": {ROLE_BACKEND: 0.4, ROLE_FRONTEND: 0.45, ROLE_DESIGN: 0.15},
    },
    "catalog": {
        "name": "Catálogo e inventario de productos", "category": "Negocio", "hours": 50,
        "keywords": ["catalogo", "inventario", "productos y categorias", "gestion de productos", "stock",
                     "catalog", "catalogue", "inventory", "product management", "products and categories"],
        "split": {ROLE_BACKEND: 0.45, ROLE_FRONTEND: 0.4, ROLE_DESIGN: 0.15},
    },
    "payments": {
        "name": "Carrito de compras y pagos en línea", "category": "Negocio", "hours": 70,
        "keywords": ["pasarela de pagos", "pagos en linea", "pago en linea", "carrito de compras", "carrito",
                     "checkout", "pse", "wompi", "payu", "stripe", "mercadopago", "comercio electronico",
                     "tienda virtual", "e-commerce", "ecommerce",
                     "payment gateway", "online payments", "online payment", "payments", "shopping cart", "cart",
                     "online store", "paypal"],
        "split": {ROLE_BACKEND: 0.55, ROLE_FRONTEND: 0.35, ROLE_DESIGN: 0.10},
    },
    "bookings": {
        "name": "Reservas y agenda de citas", "category": "Negocio", "hours": 55,
        "keywords": ["reservas", "reserva de", "citas", "agendamiento", "agenda", "calendario de", "turnos",
                     "booking", "bookings", "reservations", "appointments", "scheduling", "calendar"],
        "split": {ROLE_BACKEND: 0.45, ROLE_FRONTEND: 0.4, ROLE_DESIGN: 0.15},
    },
    "invoicing": {
        "name": "Facturación electrónica", "category": "Negocio", "hours": 80,
        "keywords": ["factura electronica", "facturacion electronica", "dian", "facturacion",
                     "electronic invoicing", "e-invoicing", "invoicing", "invoices", "billing"],
        "split": {ROLE_BACKEND: 0.7, ROLE_FRONTEND: 0.25, ROLE_DESIGN: 0.05},
    },
    "reports": {
        "name": "Reportes y tableros de indicadores", "category": "Análisis", "hours": 45,
        "keywords": ["reportes", "informes", "estadisticas", "graficos", "indicadores", "dashboard",
                     "tablero de control", "analitica",
                     "reports", "reporting", "statistics", "charts", "kpis", "kpi", "analytics"],
        "split": {ROLE_BACKEND: 0.4, ROLE_FRONTEND: 0.45, ROLE_DESIGN: 0.15},
    },
    "notifications": {
        "name": "Notificaciones por correo, SMS o WhatsApp", "category": "Comunicación", "hours": 30,
        "keywords": ["notificaciones", "correo electronico", "correos automaticos", "sms", "whatsapp", "push",
                     "alertas por correo", "recordatorios",
                     "notifications", "email notifications", "emails", "reminders", "email alerts"],
        "split": {ROLE_BACKEND: 0.75, ROLE_FRONTEND: 0.2, ROLE_DESIGN: 0.05},
    },
    "chat": {
        "name": "Chat y mensajería en tiempo real", "category": "Comunicación", "hours": 65,
        "keywords": ["chat", "mensajeria", "tiempo real", "websocket", "mensajes entre",
                     "messaging", "real time", "real-time", "live chat", "messages between"],
        "split": {ROLE_BACKEND: 0.5, ROLE_FRONTEND: 0.4, ROLE_DESIGN: 0.1},
    },
    "integrations": {
        "name": "Integración con sistemas externos", "category": "Integración", "hours": 50,
        "keywords": ["integracion con", "integrar con", "api externa", "apis externas", "erp", "crm",
                     "sistema contable", "servicios externos", "webhooks",
                     "integration with", "integrate with", "external api", "external apis", "third-party",
                     "accounting system", "external services"],
        "split": {ROLE_BACKEND: 0.85, ROLE_FRONTEND: 0.15},
    },
    "mobile": {
        "name": "Aplicación móvil", "category": "Plataformas", "hours": 120,
        "keywords": ["app movil", "aplicacion movil", "android", "ios", "aplicacion para celular",
                     "app para celular", "movil",
                     "mobile app", "mobile application", "mobile", "smartphone app", "phone app"],
        "split": {ROLE_BACKEND: 0.25, ROLE_FRONTEND: 0.6, ROLE_DESIGN: 0.15},
    },
    "ai": {
        "name": "Inteligencia artificial y recomendaciones", "category": "Inteligencia", "hours": 90,
        "keywords": ["inteligencia artificial", "chatbot", "machine learning", "aprendizaje automatico",
                     "recomendaciones", "recomendador", "prediccion", "clasificacion automatica", "reconocimiento",
                     "artificial intelligence", "recommendations", "recommender", "prediction", "predictions",
                     "automatic classification", "recognition"],
        "split": {ROLE_BACKEND: 0.8, ROLE_FRONTEND: 0.15, ROLE_DESIGN: 0.05},
    },
    "cms": {
        "name": "Gestión de contenidos y blog", "category": "Contenido", "hours": 40,
        "keywords": ["blog", "cms", "gestor de contenidos", "gestion de contenidos", "noticias", "articulos",
                     "content management", "news", "articles", "posts"],
        "split": {ROLE_BACKEND: 0.4, ROLE_FRONTEND: 0.4, ROLE_DESIGN: 0.2},
    },
    "files": {
        "name": "Carga y gestión de archivos", "category": "Contenido", "hours": 25,
        "keywords": ["subir archivos", "carga de archivos", "adjuntar", "documentos", "almacenamiento de archivos",
                     "imagenes", "pdf",
                     "upload files", "file upload", "file uploads", "attachments", "documents", "file storage",
                     "images"],
        "split": {ROLE_BACKEND: 0.6, ROLE_FRONTEND: 0.4},
    },
    "maps": {
        "name": "Mapas y geolocalización", "category": "Plataformas", "hours": 50,
        "keywords": ["mapa", "mapas", "geolocalizacion", "gps", "rutas", "ubicacion", "domicilios",
                     "seguimiento de pedidos",
                     "map", "maps", "geolocation", "routes", "location", "deliveries", "order tracking"],
        "split": {ROLE_BACKEND: 0.4, ROLE_FRONTEND: 0.5, ROLE_DESIGN: 0.1},
    },
    "languages": {
        "name": "Soporte de varios idiomas", "category": "Contenido", "hours": 20,
        "keywords": ["multiidioma", "varios idiomas", "multilenguaje", "traduccion", "ingles y espanol",
                     "multilingual", "multi-language", "multiple languages", "translation", "english and spanish"],
        "split": {ROLE_BACKEND: 0.3, ROLE_FRONTEND: 0.6, ROLE_DESIGN: 0.1},
    },
    "security": {
        "name": "Seguridad avanzada y auditoría", "category": "Núcleo", "hours": 35,
        "keywords": ["doble factor", "autenticacion de dos factores", "2fa", "auditoria", "cifrado",
                     "trazabilidad", "logs de auditoria",
                     "two-factor", "two factor", "audit", "audit logs", "encryption", "traceability"],
        "split": {ROLE_BACKEND: 0.8, ROLE_FRONTEND: 0.2},
    },
    "website": {
        "name": "Sitio web institucional", "category": "Contenido", "hours": 35,
        "keywords": ["sitio web", "pagina web", "landing", "sitio institucional", "pagina institucional",
                     "portafolio", "pagina de inicio",
                     "website", "web site", "web page", "landing page", "corporate site", "portfolio", "home page"],
        "split": {ROLE_BACKEND: 0.15, ROLE_FRONTEND: 0.5, ROLE_DESIGN: 0.35},
    },
    "migration": {
        "name": "Migración e importación de datos", "category": "Integración", "hours": 30,
        "keywords": ["migracion", "migrar", "importar datos", "importacion de datos", "carga masiva",
                     "desde excel", "legado",
                     "data migration", "migrate", "import data", "data import", "bulk upload", "from excel",
                     "legacy"],
        "split": {ROLE_BACKEND: 0.85, ROLE_FRONTEND: 0.15},
    },
}
