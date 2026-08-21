# Setup — computadora nueva

Guía para dejar este proyecto funcionando en una computadora distinta a la original. Pensada para correrse paso a paso, ya sea a mano o pidiéndole a Claude Code que la siga.

## 0. Cómo llegan los archivos acá

Este proyecto vive dentro de Google Drive (`Mi unidad/Grupo ANC - Claude/Ancestral/Analitica y TI/Databases y ETLs`), sincronizado con la cuenta **ancestral.ti@gmail.com**. Con solo instalar Google Drive para escritorio e iniciar sesión con esa cuenta, esta carpeta completa aparece sola — **no hace falta clonar el repo de GitHub** para tener los archivos.

Eso incluye archivos que a propósito *no* están en GitHub (ver `.gitignore`): `.env`, `credentials/` y `data/` (la base `warehouse.duckdb` + los datos crudos). Viajan solo por Drive porque son sensibles (contraseñas, plata del negocio).

**Importante:** evitar tener dos computadoras sincronizando y usando `git` sobre esta misma carpeta al mismo tiempo — Drive puede generar conflictos dentro de `.git/`. Tratarlo como "una máquina activa a la vez".

## 1. Prerrequisitos a instalar en la máquina nueva

- [Google Drive para escritorio](https://www.google.com/drive/download/) — iniciar sesión con `ancestral.ti@gmail.com` y esperar a que sincronice esta carpeta.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (gestor de Python) — instala Python 3.12 solo.
- [GitHub CLI (`gh`)](https://cli.github.com/) — para hacer `git push`/`pull` sin pelear con contraseñas.
- Git (normalmente ya viene, o se instala junto con GitHub Desktop / gh).

## 2. Autenticación

```bash
gh auth login
```
Elegir `GitHub.com` → `HTTPS` → `Login with a web browser`, y usar la cuenta **AncestralTI**.

```bash
git config --global user.name "AncestralTI"
git config --global user.email "ancestral.ti@gmail.com"
```

## 3. Instalar dependencias del proyecto

Parado dentro de esta carpeta (`Databases y ETLs`):

```bash
uv sync
```

Esto crea `.venv` con todas las librerías (`dash`, `duckdb`, `pandas`, etc. — ver `pyproject.toml`). No se sube a Drive ni a GitHub a propósito (pesa ~580 MB y se regenera solo con este comando).

## 4. Verificar que las credenciales llegaron por Drive

Deberían existir (ya sincronizados, no hay que crearlos):
- `.env` (si por algún motivo no está, copiar `.env.example` como `.env` y pedir los valores reales al dueño del proyecto)
- `credentials/google-service-account.json`
- `data/warehouse.duckdb`

## 5. Probar que todo funciona

**Correr el pipeline (extrae de las fuentes y actualiza el warehouse):**
```bash
uv run python -m src.pipeline
```

**Ver los dashboards en local** (cada uno es una app separada, corren en puertos distintos):
```bash
uv run python -m src.dashboard.app_operaciones   # http://localhost:8050
uv run python -m src.dashboard.app_ventas        # http://localhost:8051
uv run python -m src.dashboard.app_finanzas      # http://localhost:8052
```
Piden usuario/contraseña (HTTP Basic Auth) — están en `.env` como `DASHBOARD_USER` / `DASHBOARD_PASSWORD`.

**Ver el notebook de exploración:**
```bash
uv run jupyter lab notebooks/explorar_datos.ipynb
```

## 6. Automatización ya existente (no requiere nada de la máquina nueva)

El pipeline corre solo todos los días a las 3am (hora Bolivia) vía GitHub Actions (`.github/workflows/pipeline.yml`), usando credenciales guardadas como GitHub Secrets — independiente de qué computadora esté prendida.

## ⚠️ Problema conocido — pendiente de arreglar

`render.yaml` (config de despliegue en Render.com) todavía apunta a `src.dashboard.app:server`, un archivo que ya no existe — se dividió en `app_operaciones.py` / `app_ventas.py` / `app_finanzas.py` (commit `542c529`) y `render.yaml` no se actualizó. **El despliegue en Render está roto hasta que se decida** si va como 3 servicios separados (uno por dashboard) o un único punto de entrada que combine los 3. No afecta el pipeline diario (que corre por GitHub Actions, no por Render).

## Dueño / contacto

Preguntas de negocio o credenciales que falten: dueño original del proyecto (cuenta `frf88` / `farojas88@gmail.com`).
