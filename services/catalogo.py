"""Catálogo de módulos típicos de software, con horas base y reparto por rol."""

ROL_BACKEND = "Backend"
ROL_FRONTEND = "Frontend"
ROL_DISENO = "UX/UI Design"
ROL_QA = "QA"
ROL_DEVOPS = "DevOps"
ROL_GESTION = "Project Management"

ROLES = [ROL_BACKEND, ROL_FRONTEND, ROL_DISENO, ROL_QA, ROL_DEVOPS, ROL_GESTION]

# Multiplicador de horas según la complejidad detectada
FACTORES_COMPLEJIDAD = {"baja": 0.7, "media": 1.0, "alta": 1.6}

# Multiplicadores (optimista, pesimista) sobre las horas probables: base de la estimación PERT
RANGO_PERT = {"baja": (0.85, 1.30), "media": (0.80, 1.50), "alta": (0.75, 1.90)}

SENALES_ALTA = [
    "complejo", "compleja", "avanzado", "avanzada", "tiempo real", "alta concurrencia", "miles de usuarios",
    "varios sistemas", "multiempresa", "escalable", "alto volumen", "a gran escala",
]
SENALES_BAJA = ["sencillo", "sencilla", "basico", "basica", "simple", "prototipo", "mvp", "minimo viable"]

DISTRIBUCION_ESTANDAR = {ROL_BACKEND: 0.5, ROL_FRONTEND: 0.4, ROL_DISENO: 0.1}

# Trabajo transversal: porcentaje de las horas de desarrollo y mínimo de horas
TRANSVERSALES = [
    {"nombre": "Testing and quality assurance", "rol": ROL_QA, "porcentaje": 0.20, "minimo": 8},
    {"nombre": "Project management", "rol": ROL_GESTION, "porcentaje": 0.12, "minimo": 8},
    {"nombre": "Deployment and go-live", "rol": ROL_DEVOPS, "porcentaje": 0.08, "minimo": 8},
]

MODULOS = {
    "autenticacion": {
        "nombre": "Authentication and user management", "categoria": "Core", "horas": 40,
        "palabras": ["login", "inicio de sesion", "iniciar sesion", "inicien sesion", "cuentas de usuario",
                     "registro de usuarios", "usuarios y roles", "roles y permisos", "autenticacion",
                     "perfiles de usuario", "permisos"],
        "distribucion": {ROL_BACKEND: 0.5, ROL_FRONTEND: 0.35, ROL_DISENO: 0.15},
    },
    "panel_admin": {
        "nombre": "Admin panel", "categoria": "Core", "horas": 60,
        "palabras": ["panel administrativo", "panel de administracion", "backoffice", "back office",
                     "dashboard administrativo", "administrador del sistema", "modulo administrativo"],
        "distribucion": {ROL_BACKEND: 0.4, ROL_FRONTEND: 0.45, ROL_DISENO: 0.15},
    },
    "catalogo": {
        "nombre": "Product catalog and inventory", "categoria": "Business", "horas": 50,
        "palabras": ["catalogo", "inventario", "productos y categorias", "gestion de productos", "stock"],
        "distribucion": {ROL_BACKEND: 0.45, ROL_FRONTEND: 0.4, ROL_DISENO: 0.15},
    },
    "pagos": {
        "nombre": "Shopping cart and online payments", "categoria": "Business", "horas": 70,
        "palabras": ["pasarela de pagos", "pagos en linea", "pago en linea", "carrito de compras", "carrito",
                     "checkout", "pse", "wompi", "payu", "stripe", "mercadopago", "comercio electronico",
                     "tienda virtual", "e-commerce", "ecommerce"],
        "distribucion": {ROL_BACKEND: 0.55, ROL_FRONTEND: 0.35, ROL_DISENO: 0.10},
    },
    "reservas": {
        "nombre": "Bookings and appointment scheduling", "categoria": "Business", "horas": 55,
        "palabras": ["reservas", "reserva de", "citas", "agendamiento", "agenda", "calendario de", "turnos"],
        "distribucion": {ROL_BACKEND: 0.45, ROL_FRONTEND: 0.4, ROL_DISENO: 0.15},
    },
    "facturacion": {
        "nombre": "Electronic invoicing", "categoria": "Business", "horas": 80,
        "palabras": ["factura electronica", "facturacion electronica", "dian", "facturacion"],
        "distribucion": {ROL_BACKEND: 0.7, ROL_FRONTEND: 0.25, ROL_DISENO: 0.05},
    },
    "reportes": {
        "nombre": "Reports and KPI dashboards", "categoria": "Analytics", "horas": 45,
        "palabras": ["reportes", "informes", "estadisticas", "graficos", "indicadores", "dashboard",
                     "tablero de control", "analitica"],
        "distribucion": {ROL_BACKEND: 0.4, ROL_FRONTEND: 0.45, ROL_DISENO: 0.15},
    },
    "notificaciones": {
        "nombre": "Email, SMS or WhatsApp notifications", "categoria": "Communication", "horas": 30,
        "palabras": ["notificaciones", "correo electronico", "correos automaticos", "sms", "whatsapp", "push",
                     "alertas por correo", "recordatorios"],
        "distribucion": {ROL_BACKEND: 0.75, ROL_FRONTEND: 0.2, ROL_DISENO: 0.05},
    },
    "chat": {
        "nombre": "Real-time chat and messaging", "categoria": "Communication", "horas": 65,
        "palabras": ["chat", "mensajeria", "tiempo real", "websocket", "mensajes entre"],
        "distribucion": {ROL_BACKEND: 0.5, ROL_FRONTEND: 0.4, ROL_DISENO: 0.1},
    },
    "integraciones": {
        "nombre": "Integration with external systems", "categoria": "Integration", "horas": 50,
        "palabras": ["integracion con", "integrar con", "api externa", "apis externas", "erp", "crm",
                     "sistema contable", "servicios externos", "webhooks"],
        "distribucion": {ROL_BACKEND: 0.85, ROL_FRONTEND: 0.15},
    },
    "movil": {
        "nombre": "Mobile app", "categoria": "Platforms", "horas": 120,
        "palabras": ["app movil", "aplicacion movil", "android", "ios", "aplicacion para celular",
                     "app para celular", "movil"],
        "distribucion": {ROL_BACKEND: 0.25, ROL_FRONTEND: 0.6, ROL_DISENO: 0.15},
    },
    "ia": {
        "nombre": "Artificial intelligence and recommendations", "categoria": "Intelligence", "horas": 90,
        "palabras": ["inteligencia artificial", "chatbot", "machine learning", "aprendizaje automatico",
                     "recomendaciones", "recomendador", "prediccion", "clasificacion automatica", "reconocimiento"],
        "distribucion": {ROL_BACKEND: 0.8, ROL_FRONTEND: 0.15, ROL_DISENO: 0.05},
    },
    "cms": {
        "nombre": "Content management and blog", "categoria": "Content", "horas": 40,
        "palabras": ["blog", "cms", "gestor de contenidos", "gestion de contenidos", "noticias", "articulos"],
        "distribucion": {ROL_BACKEND: 0.4, ROL_FRONTEND: 0.4, ROL_DISENO: 0.2},
    },
    "archivos": {
        "nombre": "File upload and management", "categoria": "Content", "horas": 25,
        "palabras": ["subir archivos", "carga de archivos", "adjuntar", "documentos", "almacenamiento de archivos",
                     "imagenes", "pdf"],
        "distribucion": {ROL_BACKEND: 0.6, ROL_FRONTEND: 0.4},
    },
    "geo": {
        "nombre": "Maps and geolocation", "categoria": "Platforms", "horas": 50,
        "palabras": ["mapa", "mapas", "geolocalizacion", "gps", "rutas", "ubicacion", "domicilios",
                     "seguimiento de pedidos"],
        "distribucion": {ROL_BACKEND: 0.4, ROL_FRONTEND: 0.5, ROL_DISENO: 0.1},
    },
    "idiomas": {
        "nombre": "Multi-language support", "categoria": "Content", "horas": 20,
        "palabras": ["multiidioma", "varios idiomas", "multilenguaje", "traduccion", "ingles y espanol"],
        "distribucion": {ROL_BACKEND: 0.3, ROL_FRONTEND: 0.6, ROL_DISENO: 0.1},
    },
    "seguridad": {
        "nombre": "Advanced security and auditing", "categoria": "Core", "horas": 35,
        "palabras": ["doble factor", "autenticacion de dos factores", "2fa", "auditoria", "cifrado",
                     "trazabilidad", "logs de auditoria"],
        "distribucion": {ROL_BACKEND: 0.8, ROL_FRONTEND: 0.2},
    },
    "sitio_web": {
        "nombre": "Corporate website", "categoria": "Content", "horas": 35,
        "palabras": ["sitio web", "pagina web", "landing", "sitio institucional", "pagina institucional",
                     "portafolio", "pagina de inicio"],
        "distribucion": {ROL_BACKEND: 0.15, ROL_FRONTEND: 0.5, ROL_DISENO: 0.35},
    },
    "migracion": {
        "nombre": "Data migration and import", "categoria": "Integration", "horas": 30,
        "palabras": ["migracion", "migrar", "importar datos", "importacion de datos", "carga masiva",
                     "desde excel", "legado"],
        "distribucion": {ROL_BACKEND: 0.85, ROL_FRONTEND: 0.15},
    },
}
