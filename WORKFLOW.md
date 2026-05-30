# WORKFLOW — Cómo trabajar en MusicBox sin quemar dinero

> Documento de flujo de trabajo. El objetivo de este archivo es **uno solo**:
> que el proyecto avance rápido **gastando lo mínimo**. Si una práctica no ahorra
> dinero o no acelera el trabajo, no está aquí.
>
> Fuente de verdad del proyecto: `CLAUDE.md` (contexto) y `ROADMAP.md` (plan).
> Este documento explica **cómo se trabaja**, no **qué** se construye.

---

## 0. El problema que resolvemos

Se ha gastado mucho dinero (≈1000 €) sin que el producto avance lo esperado.
El 90 % de ese gasto suele venir de **tres errores**, no de la complejidad del proyecto:

1. **Pagar por API (por tokens) en vez de por suscripción plana.**
2. **Trial-and-error**: pedir código sin un objetivo claro y rehacerlo muchas veces.
3. **Sesiones eternas** que arrastran un contexto enorme (cada mensaje se paga).

Este flujo ataca los tres.

---

## 1. Suscripción, NO API (lo primero y lo más importante)

Pagar la API por uso es un grifo abierto. Con una **suscripción plana** el coste es fijo
y predecible. Claude Code y Codex **van incluidos** en sus suscripciones; no necesitas
claves de API para usarlos.

| Plan | Precio/mes (USD)* | Incluye | Cuándo |
|---|---|---|---|
| **Claude Pro** | 20 $ | Claude Code (límites moderados) | **Empieza aquí** |
| **Claude Max 5×** | 100 $ | Claude Code con 5× más uso | Si Pro se te queda corto |
| **Claude Max 20×** | 200 $ | Claude Code con 20× más uso | Uso muy intensivo |
| **ChatGPT Plus** | 20 $ | Codex incluido (~30–150 mensajes/5 h) | Segunda opinión |

\* *Precios verificados en fuentes oficiales (mayo 2026). En Europa el importe en € es
similar (+ IVA). El plan **gratuito** de Claude NO incluye Claude Code.*

**Recomendación para tu caso (1 desarrollador, proyecto Python + web):**
empieza con **Claude Pro + ChatGPT Plus (40 $/mes)**. Si trabajas muchas horas al día
y chocas con los límites de Claude Code, sube a **Claude Max 5× + ChatGPT Plus (120 $/mes)**.
Cualquiera de las dos opciones es una fracción de lo que sangra la API por tokens.

> ❗ Si ahora mismo estás usando una **API key** (de Anthropic u OpenAI) con pago por uso,
> ese es el agujero. Cámbiate a suscripción y entra con `/login` (cuenta), no con la key.

---

## 2. Reparto de roles (qué hace cada herramienta)

No se "fusionan" en un solo programa. Trabajan sobre **los mismos archivos**, y **Git es
el punto de encuentro**.

- **VS Code** → tu centro de mando (editor + terminal integrada + Git).
- **Claude Code** → **agente principal**: planifica, edita varios archivos, ejecuta los
  tests, hace commits y abre PRs. Es quien hace el trabajo de fondo.
- **Codex / Copilot** → **autocompletado** mientras escribes y **segunda opinión** puntual
  (revisar un diff, proponer otra forma). No lo pongas a hacer tareas grandes en paralelo.
- **Git / GitHub** → la **única fuente de verdad**. Lo que no está commiteado y pusheado,
  no existe.

**Regla de oro:** que **una sola** herramienta edite un archivo a la vez. Claude y Codex
tocando los mismos ficheros a la vez = conflictos y dinero tirado.

---

## 3. Instalación del entorno (Windows, paso a paso)

1. **Node.js 18 o superior** → https://nodejs.org (necesario para los CLI de Claude y Codex).
2. **Git** → https://git-scm.com . Tras instalar, en una terminal:
   ```powershell
   git config --global user.name "Tu Nombre"
   git config --global user.email "segunmercader.g@gmail.com"
   ```
3. **VS Code** → https://code.visualstudio.com
4. **Claude Code** (en Windows, de lo más fácil a lo más técnico):
   - **App de escritorio con interfaz gráfica (sin terminal)** — la vía más sencilla:
     descárgala desde https://claude.com/download
   - **O por terminal (PowerShell)** — instalador nativo recomendado:
     ```powershell
     irm https://claude.ai/install.ps1 | iex
     ```
     Alternativas: `npm install -g @anthropic-ai/claude-code` o `winget install Anthropic.ClaudeCode`.
   - **Inicia sesión**: ejecuta `claude`, se abre el navegador y entras con tu cuenta
     **Pro/Max** (no necesitas API key). Comprueba con `claude --version` y `claude doctor`.
   - *(También hay extensión "Claude Code" en el Marketplace de VS Code.)*
5. **Codex** (requiere Node 18+):
   ```powershell
   npm install -g @openai/codex
   codex             # inicia sesión con tu cuenta ChatGPT Plus
   ```
   *(El paquete correcto es `@openai/codex`. Alternativa: extensión de OpenAI / Copilot en VS Code.)*
6. **Clona el repo y ábrelo**:
   ```powershell
   git clone https://github.com/GerHard1981/musicboxdiscogsapi.git
   code musicboxdiscogsapi
   ```
   En VS Code: **Terminal → Nueva terminal** y escribe `claude`.

---

## 4. El ciclo de trabajo por tarea (el ritual que ahorra dinero)

Cada tarea es **un solo objetivo**. Nunca mezcles objetivos en la misma sesión.

```
1. RAMA      → git checkout -b feat/<nombre-corto>
2. PLAN      → pide a Claude un plan corto ANTES de tocar código. Da tu OK.
3. IMPLEMENTA→ Claude edita solo lo necesario para ESE objetivo.
4. PRUEBA    → python -m pytest -q   (debe quedar en verde)
5. PR DRAFT  → se abre el PR en borrador contra main.
6. REVISA    → tú (o Codex) miráis el diff. Merge cuando esté bien.
7. CIERRA    → termina la sesión. No arrastres contexto a la siguiente tarea.
```

Pedir el **plan antes que el código** es lo que más dinero ahorra: evita que el agente
se lance a hacer algo mal y haya que rehacerlo 5 veces.

---

## 5. Reglas de oro de ahorro

- **Un objetivo por sesión.** Sesiones cortas. Cierra cuando termines la tarea.
- **Plan antes que código.** Siempre.
- **Modelo adecuado:** Sonnet por defecto; Opus **solo** para diseño difícil o bugs
  enredados. En Claude Code cambias con `/model`. Opus cuesta varias veces más por lo mismo.
- **No re-explores el repo cada vez.** Ya existe `CLAUDE.md`: el agente arranca con contexto.
- **Tests como red de seguridad.** Si `pytest` pasa, no repitas trabajo "por si acaso".
- **No pidas imposibles al entorno.** Saber qué puede cada herramienta evita gasto inútil
  (p. ej., un agente en la nube no puede tocar tu Google Drive ni tu disco local).
- **Una herramienta por archivo.** Claude o Codex, no los dos a la vez sobre lo mismo.

---

## 6. Plantillas de prompts exactos

Copia, pega y rellena lo que está entre `<...>`. Están pensadas para gastar poco.

### 6.1 Arrancar una tarea
```
Trabaja en el repo musicboxdiscogsapi, en una rama nueva feat/<nombre>.
Objetivo (UNO solo): <objetivo concreto y medible>.
Reglas: lee y respeta CLAUDE.md. No añadas dependencias nuevas. No toques .env.
La API es de solo lectura (no borra/mueve música ni reescribe tags).
Antes de programar, dame un plan corto (qué archivos tocas y por qué) y espera mi OK.
Al acabar: ejecuta pytest y py_compile, y abre un PR en draft. No hagas nada fuera del objetivo.
```

### 6.2 Arreglar un bug
```
Bug: <síntoma exacto y cómo reproducirlo>.
Comportamiento esperado: <qué debería pasar>.
Primero localiza la causa y explícamela en 2 líneas. No cambies nada hasta que confirme.
Luego aplica el fix MÍNIMO y añade un test que falle antes y pase después.
```

### 6.3 Segunda opinión / revisión (Claude o Codex)
```
Revisa SOLO el diff de esta rama buscando bugs reales y simplificaciones de alto valor.
No reescribas por estilo. Lista los hallazgos por severidad. No apliques cambios sin mi OK.
```

### 6.4 Mantener el rumbo (anti-deriva)
```
Recuerda: un solo objetivo (<X>). Si encuentras otros problemas, anótalos en una lista
"para después" y NO los toques ahora.
```

### 6.5 Cerrar la sesión (barato)
```
Resume en 5 líneas qué cambiaste y qué queda pendiente. Actualiza ROADMAP.md si procede.
No abras temas nuevos.
```

---

## 7. Errores caros que NO repetimos

- **Trial-and-error sin plan.** Pide siempre el plan primero (§4, §6.1).
- **Sesiones infinitas.** Cada mensaje arrastra todo el contexto y se paga. Cierra y abre limpio.
- **Opus para todo.** Reserva el modelo caro para lo difícil.
- **Dos repos / dudas de dónde está la verdad.** Git es la única fuente de verdad.
- **Rehacer la UI entera por un cambio pequeño.** Cambios mínimos y localizados.
- **Pedirle a una herramienta algo que no puede hacer.** (Ver §5.)

---

## 8. Chuleta de comandos

```powershell
# Tests y compilación (antes de cada PR)
python -m pytest -q
python -m py_compile (git ls-files '*.py')

# Arrancar la API en local
.\run_api.ps1            # web en http://127.0.0.1:8765/  ·  Swagger en /docs

# Indexar la biblioteca
python index_music.py

# Git por tarea
git checkout -b feat/<nombre>
git add -A && git commit -m "feat: <qué>"
git push -u origin feat/<nombre>
```
