# Cotizador IA · backend

API en **FastAPI** para freelancers que no saben cuánto cobrar por un proyecto de software: el usuario describe su
proyecto y la app lo convierte en una cotización completa. Detecta los módulos, estima las horas con **PERT**,
calcula el precio con las tarifas del usuario y redacta la propuesta comercial.
Base de datos **PostgreSQL en Neon** · inicio de sesión con **código por correo** (sin contraseña) · desplegado en **Render**.

Convención: el código, las rutas y los campos JSON están en inglés; todo lo que ve el usuario (mensajes de error,
nombres de módulos y roles, propuesta) está en español.

## ¿Qué hace la IA?
Las cifras (módulos, horas, precio, hitos) siempre las calcula código propio en Python. Un modelo de lenguaje
(**Groq**, opcional) solo lee esos resultados y escribe texto: nunca cambia horas, precios ni hitos por su cuenta.

| Paso | Quién lo hace | Técnica |
|---|---|---|
| Análisis del alcance | Código propio | Normalización sin acentos, catálogo de 19 módulos con palabras clave en español e inglés y señales de complejidad por oración |
| Estimación | Código propio | PERT de tres puntos: (optimista + 4·probable + pesimista) / 6, con rangos según la complejidad |
| Reparto del trabajo | Código propio | Cada módulo se reparte entre Backend, Frontend y Diseño UX/UI; QA, gestión y despliegue son un % del desarrollo |
| Cálculo financiero | Código propio | Costo directo → contingencia → margen → descuento → IVA, cronograma e hitos de pago 40/30/30 |
| Cotizaciones parecidas | Código propio | TF-IDF y similitud del coseno implementados desde cero (solo entre las cotizaciones del usuario) |
| Propuesta | Código propio | Documento Markdown con 8 secciones y formato de pesos colombianos |
| Segunda opinión del alcance | Groq | Sugiere módulos **del catálogo** que la descripción pide y el análisis no detectó; el usuario decide si los agrega (como módulo manual, con las horas del catálogo) |
| Explicación del precio | Groq | Explica en palabras sencillas las cifras ya calculadas y cómo podría bajar el precio |
| Preguntas y riesgos | Groq | Preguntas para el cliente y riesgos que podrían aumentar las horas |
| Redacción de la propuesta | Groq | Reescribe el resumen, el alcance y los supuestos; si cambia una sola cifra la sugerencia se descarta, y solo se guarda lo que el usuario aplica |

Reglas de la IA (`services/llm.py`, `services/privacy.py`, `services/ai.py`):
- Respuestas con **salidas estructuradas** (`json_schema` estricto) validadas con Pydantic.
- **Privacidad:** el nombre del cliente, la empresa, el nombre y el correo del usuario, y cualquier correo o teléfono se
  reemplazan por marcadores (`[cliente]`, `[correo 1]`…) antes de salir del servidor, y se restauran en la respuesta.
- Solo sobre las cotizaciones propias y con sesión iniciada.
- Errores claros, nunca un 500: **503** si no está configurada, **429** con `Retry-After` si se alcanzó el límite de uso,
  **502** si el proveedor falla, tarda más de 30 s o responde algo inválido. Un 5xx se reintenta una vez.
- Variables: `AI_PROVIDER=groq`, `AI_API_KEY` (clave `gsk_…` de https://console.groq.com/keys),
  `AI_MODEL=openai/gpt-oss-20b`; opcionales `AI_BASE_URL` y `AI_FALLBACK_MODEL`. Sin clave, todo lo demás funciona igual.

## Puesta en marcha
```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements-dev.txt
copy .env.example .env           # y pega tu cadena de Neon
uvicorn main:app --reload
```
Documentación interactiva en http://127.0.0.1:8000/docs (botón **Authorize** para pegar el token).

### Base de datos en Neon
1. Crea un proyecto en https://neon.tech y copia la *connection string*.
2. Cámbiale el inicio `postgresql://` por `postgresql+psycopg://` y deja solo `?sslmode=require` al final.
3. Pégala en `.env` como `DATABASE_URL`. Las tablas se crean solas al arrancar.

Neon duerme la base tras 5 minutos sin uso: la primera petición puede tardar un par de segundos.

Las tablas conservan sus nombres de columnas en español; el código los usa con nombres en inglés.
Para pasar datos guardados con la versión anterior (estados `borrador`, roles en inglés, etc.):
`python migrate_to_english.py` (muestra los cambios) y `python migrate_to_english.py --yes` (los guarda).
`python reset_db.py --si` borra todo y recrea las tablas (solo si de verdad hace falta).

## Inicio de sesión con código por correo
1. `POST /auth/register` (name, email) → envía un código de verificación.
2. `POST /auth/login` (email) → envía un código para entrar (cuentas que ya existen).
3. `POST /auth/verify` (email, code) → devuelve el token. Envíalo como `Authorization: Bearer <token>`.
   La primera verificación activa la cuenta y carga las **tarifas de referencia del mercado**.
4. `GET /auth/me` → usuario actual.

El código vence en 10 minutos, sirve una sola vez, permite 5 intentos y hay que esperar 30 segundos para pedir otro.
Solo se guarda un hash del código. No hay roles: cada usuario ve y edita **solo** sus cotizaciones, tarifas y
estadísticas (los datos de otro usuario responden 404).

### Envío de correos
`EMAIL_BACKEND`: `console` (muestra el código en la terminal; en local), `smtp` (por ejemplo Gmail, solo en local) o
`brevo` (API HTTP gratis; funciona en Render, cuyo plan gratis bloquea SMTP). Ver `.env.example`.

## Flujo de uso
1. Regístrate y verifica el código: tus tarifas ya vienen cargadas (ajústalas en `/rates` o restablécelas con
   `POST /rates/reset`). `POST /seed` carga cotizaciones de ejemplo.
2. `POST /quotes` con el alcance en texto libre (opcional: para quién es, `client_name` y `client_company`).
3. `POST /quotes/{id}/analyze`: módulos, horas y precio.
4. Ajustes: `PUT /quotes/{id}` (margen, descuento…) o `/quotes/{id}/items` (agregar, editar, quitar). Todo se recalcula solo.
5. `POST /quotes/{id}/proposal` y `GET /quotes/{id}/proposal/download`.
6. `POST /quotes/{id}/status` para el seguimiento: `draft` (borrador) → `sent` (enviada) → `accepted` (aceptada) | `rejected` (rechazada).

Una cotización enviada queda congelada; para editarla hay que devolverla a borrador.

## Endpoints
| Grupo | Rutas |
|---|---|
| Autenticación | `POST /auth/register`, `/auth/login`, `/auth/verify`, `GET /auth/me` |
| Alcance | `POST /scope/analyze`, `POST /scope/estimate` (no guardan nada) |
| Finanzas | `POST /finance/simulate` |
| Tarifas | CRUD en `/rates`, `POST /rates/reset`, `GET /rates/market` (pública) |
| Cotizaciones | CRUD en `/quotes`, `/analyze`, `/summary`, `/status`, `/similar` |
| Módulos | `/quotes/{id}/items` (GET, POST, PUT, DELETE) |
| Propuesta | `/quotes/{id}/proposal` y `/download` |
| Estadísticas | `GET /stats`, `POST /seed` |
| IA | `GET /ai/status`, `POST /ai/quotes/{id}/scope-review`, `/explain-price`, `/client-questions`, `/improve-proposal`; `PATCH /quotes/{id}/proposal` aplica las secciones aceptadas |

CORS: solo el front de Vercel y `localhost:4200` pueden llamar al API desde el navegador (`CORS_ORIGINS`).

## Contrato de la API (contract-first)
`openapi.json` es la **única fuente de verdad** de la API: rutas, parámetros, esquemas, códigos de error y la seguridad
JWT (`HTTPBearer`). Está versionado en el repo, el front genera sus tipos y su cliente desde ese archivo
(`npm run gen:api`) y una prueba falla si el archivo no coincide con lo que publica la app.

```bash
python scripts/export_openapi.py           # regenera openapi.json (usa SQLite en memoria, nunca Neon)
python scripts/export_openapi.py --check   # falla si está desactualizado
```

### Cómo agregar un endpoint
1. **Primero el contrato:** define los esquemas Pydantic de entrada y de salida en `schemas/` (nada de devolver
   diccionarios sueltos) y los errores con `errors(...)` de `schemas/common.py`.
2. Declara la ruta en `routers/` con `response_model=` y un `summary` en español, y deja la lógica en `services/`.
3. Corre `python scripts/export_openapi.py` y revisa el cambio de `openapi.json` en el diff: ese diff **es** el cambio
   de contrato.
4. Agrega las pruebas y haz commit del código junto con `openapi.json`.
5. En el front, `npm run gen:api` regenera los tipos: si cambió o desapareció un campo, el front deja de compilar
   donde lo usa.

`tests/test_openapi.py` exige que cada endpoint JSON tenga `response_model`, que los errores usen el esquema `Error`
y que las rutas protegidas declaren el JWT.

## Pruebas
```bash
pytest
```
160 pruebas sobre SQLite: nunca tocan la base de Neon, no envían correos reales (leen los códigos de una bandeja en
memoria) y nunca llaman a Groq (las respuestas del modelo se simulan a nivel HTTP).
