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
- **`raw`**: tablas tal cual llegan de la fuente, sin filtrar (`raw.izi_facturas`, `raw.izi_items_inventario`, `raw.matriz_relaciones_ancestral`).
- **`gold`**: tablas de hechos y dimensiones listas para análisis (`gold.fct_ventas_items`, `gold.dim_producto`, `gold.fct_movimiento_inventario`, `gold.dim_receta_ancestral`, `gold.fct_consumo_insumos_ancestral`).

✅ **Fuente iZi migrada completa, ambos negocios**, replicando la lógica de las Power Queries existentes:
- `src/extract/izi.py` — login + `fetch_facturas` + `fetch_items_inventario`.
- `src/load/raw_izi.py` — carga ambos negocios (Ancestral, omuH — mismo `contribuyente` 79818, distinto `sucursal`) en una sola lectura JSON (`union_by_name=true`, evita conflictos de tipo entre negocios); negocio derivado del campo `sucursal`.
- `src/transform/gold_izi.py` — construye `fct_ventas_items` (78,754 filas) y `dim_producto` (799 productos) con SQL directo en DuckDB.
- `src/pipeline.py` — orquesta extract → raw → gold para ambos negocios.
- Nota de negocio preservada: la exclusión del código `AN000046` solo aplica a Ancestral (así estaba en su Power Query original; omuH no la tenía).
- Pendiente menor: 377 de 78,754 líneas de venta (0.5%) no matchean con `dim_producto` — a investigar cuando se use ese join en serio.

✅ **Automatización diaria con GitHub Actions** (repo privado [github.com/frf88/GrupoANCetl](https://github.com/frf88/GrupoANCetl)) — `.github/workflows/pipeline.yml` corre el pipeline todos los días a las 3am hora Bolivia (`cron: "0 7 * * *"` UTC) y también permite disparo manual ("Run workflow") — sin necesitar ningún servidor propio. Credenciales guardadas como GitHub Secrets (`IZI_BASE_URL`, `IZI_EMAIL`, `IZI_PASSWORD`, `GOOGLE_SERVICE_ACCOUNT_JSON`).

✅ **Publicación a Google Sheets funcionando** (extensión `gsheets` de DuckDB, `src/load/publish_gsheets.py`) — probada con éxito escribiendo `gold.fct_ventas_items` y `gold.dim_producto` a una Sheet real. **Pausada a pedido del usuario (2026-08-14)** mientras se compilan más fuentes para el dashboard de Inventarios y se define el modelo de datos final — no se llama desde `pipeline.py` por ahora (ver ese archivo para reactivarla).

✅ **Migración completa de las 38 Power Queries del usuario (2026-08-15) — 28 tablas gold**, todas compiladas fuente por fuente, mismo patrón raw/gold, pipeline corriendo sin errores de punta a punta:
- **iZi (API)**: `fct_ventas_items`, `dim_producto`, `fct_movimiento_inventario`, `fct_mov_inv_omuh` / `fct_mov_inv_omuh_todos` (endpoint nuevo `/movimientos`).
- **Recetas/consumo**: `dim_receta_ancestral` / `dim_receta_omuh` (matriz insumo↔producto, con merma; estandarizado a usar siempre `Cantidad usada (kg o u)`, no existe una versión en gramos separada), `fct_consumo_insumos_ancestral` (generaliza el caso HUARI/Michelada a cualquier insumo con código propio — ej. futuro Negroni de 3 botellas), `pesos_platos_ancestral`.
- **Compras**: `fct_compras_insumos_ancestral` / `_omuh`, `fct_compras_totales_ancestral`, `dim_compras_precios_ancestral`, `dim_producto_izi`.
- **Inventario físico** (Sheets anchas, fecha por columna): `fct_inventario_fisico`, `fct_inventario_omuh`, `fct_inventario_unitarios_omuh`, `fct_inventario_unitarios_gs`, `fct_inventario_insumos_gs`.
- **Salidas/mermas**: `fct_salidas_mermas_ancestral` / `_omuh`, `fct_apertura_vinos_copa`.
- **PedidosYa**: `fct_pedidosya_items`, `fct_ventas_omuh_pedidosya`, `fct_extras_izi_omuh` (incluye la lógica de "Vegetarianas" como paso intermedio).
- **Copas de vino**: `dim_relacion_copa_vino`, `fct_copas_vino_ancestral` — se migró igual aunque la fuente estaba en "Pendientes a eliminar" del usuario; se revisará qué se usa realmente cuando se defina el modelo final.
- **Otros**: `dim_min_max_porciones` (tabla chica embebida en la Power Query original, decodificada de base64).
- Extractores genéricos reutilizables agregados: `src/extract/gsheet_csv.py` (Sheets publicadas como CSV), `src/extract/http.py` (bytes genéricos, ej. Excel), `src/load/raw_xlsx.py`, `src/load/raw_json_list` (JSON de la API iZi). `src/load/raw_csv.py` soporta `skip=N` para Sheets con filas basura antes del encabezado real.
- Bugs encontrados y corregidos en las Power Queries originales (documentados en el código con comentarios, aplicados sin confirmación final del usuario — ver abajo): `Compras Precios` eliminaba su propia columna calculada `Precio Compra`; `Matriz_de_Relaciones omuh` filtraba `= null` en vez de `<> null`; la hoja "Ventas Extras iZi" traía `Fecha` como texto sin parsear (bug nuestro, no de la Power Query original).

### Objetivo final del dashboard de Inventarios
Reconciliación semanal de stock por producto: Inv. inicial + Compras − Ventas − Ventas Ext − Cortesías − Salidas = Inv. calculado, comparado contra el conteo físico real = Diferencia. "Cortesías" se calcula en la capa de visualización (no en `gold`) a partir de `fct_mov_inv_omuh_todos` filtrando `tipoMovimiento IN ('interna','prod-venta')` menos las ventas.

✅ **Primera tabla de reconciliación construida y validada (2026-08-15): `gold.fct_reconciliacion_bebidas_ancestral`** — replica la tabla "Control Inventario: Bebidas" del dashboard real de Ancestral.
- `src/transform/gold_reconciliacion.py` — usa las fechas reales de conteo físico (vía `LAG()` sobre `fct_inventario_fisico`) como límites de cada semana, en vez de replicar la lógica de calendario/semana-ISO del modelo original (más simple y se ajusta sola a cuándo se cuenta en la realidad). Confirmado con el usuario: su semana corre lunes a domingo, y los conteos caen justo en domingo — coincide.
- **Validado contra datos reales**: para HUARI, semana del 19 al 26 de julio 2026, el modelo da Inv. inicial=81, Ventas=12 (directas + consumo vía Michelada), Inv. calculado=69, que coincide exacto con el conteo físico real (Cierre=69, Diferencia=0) — mismos números que el dashboard del usuario.
- Columna **Cortesías** queda en 0 (placeholder) — fórmula pendiente de confirmar (ver preguntas abiertas).
- Nota de calidad de datos: hay productos duplicados y filas con producto vacío en la Sheet de conteo físico — no se corrigieron, quedan tal cual vienen de la fuente.
- Pendiente: replicar la segunda tabla del dashboard (detalle diario) y el gráfico de ventas por semana; extender el patrón a otras categorías/negocios (hoy solo cubre bebidas de Ancestral).

✅ **Publicada a Google Sheets + formato armado (2026-08-15)**: `gold.fct_reconciliacion_bebidas_ancestral` se publica automáticamente (pestaña `reconciliacion_bebidas_ancestral`, misma Sheet de siempre) vía `src/pipeline.py` (la publicación del resto de las 29 tablas sigue pausada). `src/load/format_gsheets.py` (nuevo — usa `google-api-python-client` + `google-auth`, no DuckDB, porque formato condicional y slicers no están soportados por la extensión `gsheets`) le agrega formato condicional (gris si Diferencia=0, naranja si no) y 3 slicers (Diferencia, Producto, Semana).

⚠️ **Decisión (2026-08-15): la vista en Sheets no alcanza — se pasa a Looker Studio.** El usuario probó la Sheet con slicers y la encontró difícil de usar / lejos de la experiencia de Power BI (6,653 filas en una grilla, aunque tenga filtros, no se siente como un dashboard). Se decidió conectar **Looker Studio** (gratis, de Google) directo sobre esta misma Sheet como fuente — da controles de filtro reales (rango de fechas, desplegables) y formato condicional nativo en tablas, mucho más parecido a Power BI. Es 100% trabajo manual en la UI de Looker Studio (no hay API usada); se le pasó al usuario una guía paso a paso (crear informe → conectar Sheet → tabla con las métricas → control de rango de fechas sobre `fecha_cierre` → control de lista sobre `producto` → formato condicional en `diferencia`). **Pendiente: el usuario todavía no empezó este paso.**

### Preguntas abiertas (no bloquean nada, revisar cuando el usuario tenga tiempo)
1. Confirmar los 2 fixes de bugs de Power Query de arriba (Compras Precios, Matriz_de_Relaciones omuh) son el comportamiento correcto deseado.
2. Revisar, una vez armado el modelo final, qué tablas terminan sin usarse (ej. la rama de Copas de Vino) y limpiarlas.
3. Fórmula de "Cortesías" en la tabla de reconciliación (hoy en 0).

✅ **Landing page construida** (proyecto hermano `../Pagina Web Ancestral/`) — HTML/CSS/JS plano, línea gráfica y logo reales del restaurante, contenido del menú real. Lista para publicar, pendiente de desplegar en AWS (S3 + CloudFront).

▶️ Próximo paso (retomar acá): guiar al usuario paso a paso por la creación del reporte en Looker Studio (ver arriba). Una vez que la tabla de bebidas de Ancestral esté bien en Looker Studio, replicar el patrón para el resto de categorías/negocios. **Importante**: el código de hoy (todas las tablas de Inventarios, formato de Sheets) todavía no está commiteado ni pusheado a GitHub — el Action de las 3am sigue corriendo la versión vieja del pipeline hasta que se suba.

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
