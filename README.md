# Proyecto de Datos — Grupo ANC

Migración del flujo actual (Power BI: extracción + Power Query + visualización) a un stack open source / gratuito, dividido en dos etapas independientes.

## Motivación

Power BI funciona bien para la transformación y el análisis propio, pero la distribución es el problema: los socios no tienen licencia Pro/PPU, así que no pueden ver los dashboards compartidos. Se busca desacoplar la parte de **datos** (ETL) de la parte de **distribución/visualización**, usando herramientas sin costo de licencia.

## Etapa 1 — ETL (Extract, Transform, Load)

Pipeline en Python que reemplaza la extracción y Power Query actuales:

- **Extract**: Google Sheets, Excel, APIs (las mismas fuentes que hoy).
- **Transform**: lógica de negocio equivalente a las consultas actuales de Power Query (limpieza, joins, cálculos de estados financieros).
- **Load**: carga en una base de datos analítica local con **DuckDB**.

Objetivo: que el pipeline se pueda ejecutar de forma repetible (manual o programada) y deje los datos limpios y modelados en DuckDB, listos para consumo.

## Etapa 2 — Distribución / Visualización

**Decisión (2026-08-13): Google Sheets con tabla dinámica**, alimentada automáticamente por el pipeline — no Metabase.

Razón: el requisito real es ver información ya lista para decidir ("mirar y decidir"), no explorar datos en tiempo real ni filtrar libremente. Todo el personal ya sabe usar Sheets — cero curva de aprendizaje. Esto elimina la necesidad de un servidor siempre encendido para Etapa 2 (Metabase queda descartado por ahora; se reconsideraría solo si en el futuro se necesita interactividad real).

Mecánica: el pipeline escribe `gold.fct_ventas_items` / `gold.dim_producto` en una pestaña de una Google Sheet (vía la misma service account que se usa para leer fuentes Sheets/Excel); una tabla dinámica armada una vez sobre esos datos se actualiza sola. Los socios reciben el link en modo lectura.

## Alcance y enfoque de trabajo

- Se avanza paso a paso, no se genera todo el código de una vez.
- Prioridad: bajo presupuesto, sin dependencias de pago, viable desde Bolivia (limitaciones para pagos en USD).
- Este README se actualiza a medida que se toman decisiones (fuentes de datos, estructura, herramientas elegidas).

## Estado actual

✅ Entorno de desarrollo listo: `uv` instalado, Python 3.12 gestionado por `uv`, proyecto inicializado (`pyproject.toml`, `.venv`, `git` local) y esqueleto de carpetas creado. VS Code conectado (extensión Claude Code + Python + Jupyter), con `notebooks/explorar_datos.ipynb` para inspeccionar cualquier tabla del warehouse.

✅ **Arquitectura de datos definida: RAW + GOLD, ambos esquemas dentro de `data/warehouse.duckdb`** (no bases separadas):
- **`raw`**: tablas tal cual llegan de la fuente, sin filtrar (`raw.izi_facturas`, `raw.izi_items_inventario`).
- **`gold`**: tablas de hechos y dimensiones listas para análisis (`gold.fct_ventas_items`, `gold.dim_producto`).

✅ **Fuente iZi migrada completa, ambos negocios**, replicando la lógica de las Power Queries existentes:
- `src/extract/izi.py` — login + `fetch_facturas` + `fetch_items_inventario`.
- `src/load/raw_izi.py` — carga ambos negocios (Ancestral, omuH — mismo `contribuyente` 79818, distinto `sucursal`) en una sola lectura JSON (`union_by_name=true`, evita conflictos de tipo entre negocios); negocio derivado del campo `sucursal`.
- `src/transform/gold_izi.py` — construye `fct_ventas_items` (78,754 filas) y `dim_producto` (799 productos) con SQL directo en DuckDB.
- `src/pipeline.py` — orquesta extract → raw → gold para ambos negocios.
- Nota de negocio preservada: la exclusión del código `AN000046` solo aplica a Ancestral (así estaba en su Power Query original; omuH no la tenía).
- Pendiente menor: 377 de 78,754 líneas de venta (0.5%) no matchean con `dim_producto` — a investigar cuando se use ese join en serio.

✅ **Landing page construida** (proyecto hermano `../Pagina Web Ancestral/`) — HTML/CSS/JS plano, línea gráfica y logo reales del restaurante, contenido del menú real. Lista para publicar, pendiente de desplegar en AWS (S3 + CloudFront).

▶️ Próximo paso: crear la cuenta de servicio de Google Cloud (Sheets API) — necesaria tanto para leer fuentes Sheets/Excel como para escribir el dashboard de Etapa 2 — y armar el paso del pipeline que publica `gold.fct_ventas_items`/`gold.dim_producto` a una Google Sheet. En paralelo sigue pendiente: crear la cuenta de AWS y publicar la landing (S3 + CloudFront).

---

## Decisiones tomadas

### Fuentes de datos
- ~10 fuentes en total, acceso propio a todas:
  - Excel en Google Drive — se actualizan **manualmente**.
  - Google Sheets — nativo.
  - API del sistema **iZi** — requiere autenticación; el usuario ya tiene código propio de lectura (pendiente de compartir).
- Actualización de datos: **diaria**, y algunas tablas se actualizan **varias veces al día**.
- Aún no existe una cuenta de servicio (service account) de Google Cloud — hay que crearla desde cero para leer Sheets y Excel en Drive vía API.

### Entorno técnico
- No hay Python instalado — se instalará como parte del setup.
- Desarrollo desde la computadora del usuario, pero se necesita que el pipeline corra **automáticamente en la nube todos los días** (equivalente al refresh diario de Power BI online). No hay servidor propio hoy, pero hay interés en conseguir uno.
- Ejecución deseada: manual para empezar → luego programada, con corrida diaria (ej. 3am) y algunas tablas con corridas más frecuentes.

### Audiencia / Etapa 2
- ~5 personas, sin conocimientos técnicos.
- Necesitan un dashboard terminado y claro ("nada más que mirar para decidir") — descarta exportes crudos a Excel/Sheets como solución principal; apunta a una herramienta tipo Metabase con dashboards ya armados.
- No hay hosting propio todavía, pero hay interés en conseguirlo — pendiente de definir dónde correrá Etapa 2.

### Hosting / infraestructura
- El usuario ya compró el dominio **www.ancestralbolivia.com** (registrado en Namecheap). La landing page (proyecto hermano `../Pagina Web Ancestral/`) ya está construida en HTML/CSS/JS plano, lista para publicar.
- Método de pago **resuelto**: el usuario tiene tarjeta de crédito/débito internacional en USD.
- **Decisión (reemplaza el plan anterior de "un solo VPS compartido"):** se elige **AWS** en vez de DigitalOcean/Vultr/Hetzner, por dos razones: (1) da mejor latencia desde Bolivia usando la región **São Paulo (sa-east-1)**, y (2) el usuario quiere aprovechar el proyecto para aprender AWS de cara a necesidades futuras de analítica avanzada (ver "Roadmap futuro" abajo) — todo vive bajo la misma cuenta/IAM/billing, así que no hay que migrar nada cuando se sumen esos servicios.
- Arquitectura por carga de trabajo (no todo en una sola máquina):
  - **Landing page** → **S3 + CloudFront** (hosting estático, casi gratis, no compite por recursos con nada más).
  - **Cron del ETL (Python/uv)** → ⚠️ **por reconciliar entre sesiones**: el plan original de esta sección asumía Lightsail para correr Metabase + el cron juntos. Con la decisión de Etapa 2 de 2026-08-13 (Sheets en vez de Metabase), ya no hace falta un servidor siempre encendido — el cron diario que escribe en Sheets es liviano y podría correr en GitHub Actions (gratis) o una función Lambda (centavos/mes), sin necesitar Lightsail. Falta decidir si de todas formas se monta Lightsail (ej. por los ítems del roadmap futuro) o se usa la opción serverless mientras tanto.
  - **DNS**: por definir si se mueve a **Route 53** (más cómodo si se suman subdominios como `app.`, `analytics.`, `pagos.`) o se queda en Namecheap con registros sueltos apuntando a los recursos de AWS. No es bloqueante.
- Estado: cuenta de AWS **aún no creada** — próximo paso es que el usuario la cree (requiere tarjeta + verificación de teléfono), luego se arranca por S3 + CloudFront para la landing.

### Roadmap futuro (fuera del alcance actual, pero condiciona decisiones de infraestructura de hoy)
- **Plataforma de reservas**: sistema propio con backend (candidatos: ECS/Fargate o EC2) + **RDS Postgres** — DuckDB/Metabase quedan para analítica, no sirven como base transaccional de un sistema de reservas en vivo.
- **Pagos para reservas especiales**: integración con una pasarela de pago desde el backend (nunca se maneja el número de tarjeta directamente, se usa un formulario hospedado del proveedor). Pendiente investigar qué pasarela opera pagos/depósitos en Bolivia — Stripe no tiene payouts a cuentas bancarias bolivianas.
- **Correo del dominio**: se va a configurar `@ancestralbolivia.com` (probable **Google Workspace**, dado que el equipo ya usa Gmail/Drive extensivamente — alternativas más baratas: Zoho Mail, Namecheap Private Email). Pendiente definir cantidad de casillas antes de elegir proveedor. Requiere agregar registros MX en el DNS del dominio (independiente de dónde viva el hosting web).
- Cuando DuckDB/Metabase se queden cortos en volumen o interactividad: evaluar **Redshift Serverless** (warehouse) + **Athena/Glue** (consultas serverless sobre S3) + **QuickSight** (BI nativo AWS) + **SageMaker** (modelos predictivos, ej. forecasting de demanda).

### Entorno de desarrollo
- `uv` (gestor de Python y entornos virtuales) instalado en la máquina del usuario.
- Python 3.12 instalado y gestionado por `uv` (no se instaló Python por separado desde python.org).
- Proyecto inicializado con `uv init` (`pyproject.toml`, `.venv`, `git` local, `main.py` placeholder).
- Estructura de carpetas creada según lo definido más abajo, incluyendo `credentials/` (gitignored) para la futura clave de la service account de Google, y `.env.example` con las variables previstas (`GOOGLE_SERVICE_ACCOUNT_FILE`, `IZI_API_BASE_URL`, `IZI_API_KEY`, `DUCKDB_PATH`).
- `.gitignore` ajustado para excluir `.env`, `credentials/` y `data/` (contienen secretos e información financiera sensible).

## Preguntas abiertas

- ⚠️ La carpeta `../Pagina Web Ancestral/` (landing page) mencionada arriba no existe en este equipo al momento de escribir esto (2026-08-13) — verificar si es una ruta distinta, otro dispositivo, o si ese trabajo aún no se guardó.
- Reconciliar el plan de hosting del cron/ETL: ¿Lightsail igual (por el roadmap futuro) o serverless (GitHub Actions / Lambda) ahora que no hay Metabase?
- Crear la cuenta de AWS (usuario, requiere tarjeta + verificación) y arrancar por S3 + CloudFront para la landing page.
- Definir si el DNS se mueve a Route 53 o se queda en Namecheap.
- Definir cantidad de casillas de correo (`@ancestralbolivia.com`) para elegir entre Google Workspace / Zoho / Namecheap Private Email.
- Investigar qué pasarela de pagos opera en Bolivia (para la futura plataforma de reservas con pagos especiales).
- Identificar qué es el sistema **iZi** (ERP/contable) y revisar el código de autenticación que el usuario ya tiene.
- Crear la cuenta de servicio de Google Cloud (Sheets API + Drive API) — guiado paso a paso.
- Definir variables exactas que necesita la API de iZi una vez revisado el código existente.
