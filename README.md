# ABML — Aplicación Basada en Machine Learning

**Proyecto de Grado** 

Sistema de detección de patrones de comportamiento mediante biometría facial computacional. Captura expresiones faciales durante sesiones estructuradas de preguntas y respuestas, analizando emociones y respuestas en tiempo real.

---

## Tabla de contenido

- [Descripción general](#descripción-general)
- [Arquitectura del sistema](#arquitectura-del-sistema)
- [Diagramas de Secuencia del Sistema (SSD)](#diagramas-de-secuencia-del-sistema-ssd)
  - [SSD 1 — Autenticación de usuario](#ssd-1--autenticación-de-usuario)
  - [SSD 2 — Configuración de sesión de análisis](#ssd-2--configuración-de-sesión-de-análisis)
  - [SSD 3 — Ejecución de análisis en tiempo real](#ssd-3--ejecución-de-análisis-en-tiempo-real)
  - [SSD 4 — Visualización web en tiempo real](#ssd-4--visualización-web-en-tiempo-real)
- [Componentes](#componentes)
- [Stack tecnológico](#stack-tecnológico)
- [Requisitos previos](#requisitos-previos)
- [Instalación y configuración](#instalación-y-configuración)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Despliegue](#despliegue)
- [Equipo](#equipo)

---

## Descripción general

ABML integra tres subsistemas que trabajan en conjunto para detectar y registrar patrones conductuales mediante el análisis de expresiones faciales:

| Subsistema                          | Tecnología            | Rol                                                  |
| ----------------------------------- | ---------------------- | ---------------------------------------------------- |
| **API REST**                  | C# / ASP.NET Core 9    | Núcleo de datos y comunicación en tiempo real      |
| **Aplicación de escritorio** | Python + CustomTkinter | Captura, análisis de emociones y control de sesión |
| **Sitio web**                 | React + Vite           | Visualización en tiempo real para el evaluado       |

```
┌─────────────────────────────────────────────────────────────┐
│                        ABML System                          │
│                                                             │
│  ┌──────────────┐   HTTP/JWT    ┌─────────────────────┐    │
│  │  Desktop App │◄─────────────►│   API REST (.NET 9) │    │
│  │  (Python)    │               │                     │    │
│  └──────────────┘               │   ┌─────────────┐   │    │
│         │                       │   │  Base de    │   │    │
│         │ Análisis facial        │   │  Datos      │   │    │
│         ▼                       │   │ (SQL/PG/My) │   │    │
│  ┌──────────────┐               │   └─────────────┘   │    │
│  │  Cámara /    │               │                     │    │
│  │  Pantalla    │               │   ┌─────────────┐   │    │
│  └──────────────┘               │   │  SignalR    │   │    │
│                                 │   │    Hub      │   │    │
│  ┌──────────────┐  WebSocket    │   └──────┬──────┘   │    │
│  │  Web Browser │◄──────────────┤          │          │    │
│  │  (React)     │               └──────────┼──────────┘    │
│  └──────────────┘                          │               │
└───────────────────────────────────────────────────────────-─┘
```

---

## Arquitectura del sistema

El backend sigue **Arquitectura Limpia** con principios **SOLID**:

```
Controllers  →  Services (interfaces)  →  Repositories (multi-DB)  →  Database
     ↕                  ↕
  JWT Auth           SignalR Hub
```

**Patrón multi-base de datos:** el sistema detecta y conmuta automáticamente entre SQL Server, PostgreSQL y MySQL/MariaDB sin cambios en la lógica de negocio.

---

## Diagramas de Secuencia del Sistema (SSD)

Los SSD describen las interacciones entre los actores externos y el sistema como una caja negra, mostrando los eventos del sistema que se disparan.

### SSD 1 — Autenticación de usuario

**Actor:** Evaluador (usuario de la aplicación de escritorio)

```
Evaluador          Desktop App          API REST          Base de datos
    │                   │                   │                   │
    │── ingresarCredenciales() ────────────►│                   │
    │                   │                   │── validarUsuario()►│
    │                   │                   │◄── usuario ────────│
    │                   │◄── JWT Token ──────│                   │
    │◄── acceso concedido ──│               │                   │
    │                   │                   │                   │
    │    [Token expira] │                   │                   │
    │── renovarSesión() ────────────────────►│                   │
    │                   │◄── nuevo JWT ──────│                   │
```

**Operaciones del sistema:**

- `iniciarSesion(usuario, contraseña)` → valida credenciales con BCrypt y retorna JWT
- `renovarToken(jwt)` → emite nuevo token si el actual es válido

---

### SSD 2 — Configuración de sesión de análisis

**Actor:** Evaluador

```
Evaluador          Desktop App          API REST          Base de datos
    │                   │                   │                   │
    │── seleccionarGrupoPreguntas() ────────►│                   │
    │                   │                   │── consultarGrupos()►│
    │                   │◄── lista grupos ───│◄── grupos ─────────│
    │◄── mostrar grupos ────│               │                   │
    │                   │                   │                   │
    │── elegirGrupo(id) ────►│              │                   │
    │                   │── obtenerPreguntas(grupoId) ──────────►│
    │                   │◄────────────────── preguntas ──────────│
    │◄── confirmar config ──│               │                   │
    │                   │                   │                   │
    │── seleccionarFuenteCaptura() ─►│       │                   │
    │◄── fuente configurada ─────────│       │                   │
    │                   │                   │                   │
    │── iniciarSesion() ────────────────────►│                   │
    │                   │◄── sessionId ──────│                   │
```

**Operaciones del sistema:**

- `obtenerGruposPreguntas()` → retorna grupos desde la BD
- `obtenerPreguntas(grupoId)` → retorna lista de preguntas del grupo
- `crearSesion(evaluadorId, grupoId)` → genera y persiste el ID de sesión

---

### SSD 3 — Ejecución de análisis en tiempo real

**Actor:** Evaluador / Sistema de captura facial

```
Evaluador          Desktop App        Cámara/Pantalla       API REST
    │                   │                   │                  │
    │── avanzarPregunta() ──►│              │                  │
    │                   │── capturarFrame() ►│                  │
    │                   │◄── frame(imagen) ──│                  │
    │                   │                   │                  │
    │                   │── analizarEmocion(frame) ──►[modelo]  │
    │                   │◄── emocion(label, confianza) ─────────│
    │                   │                   │                  │
    │                   │── enviarPregunta(preguntaDto) ────────►│
    │                   │◄────────────────── OK ────────────────│
    │◄── mostrar emocion ───│               │                  │
    │                   │                   │                  │
    │── marcarRespuesta(positivo|negativo) ─►│                  │
    │                   │── guardarResultado(sesion, pregunta,  │
    │                   │   emocion, respuesta) ────────────────►│
    │                   │◄─────────────────── confirmación ─────│
    │                   │                   │                  │
    │    [fin preguntas]│                   │                  │
    │── finalizarSesion() ──────────────────►│                  │
    │                   │◄── sesión cerrada ─│                  │
```

**Operaciones del sistema:**

- `enviarPreguntaActual(preguntaDto)` → actualiza estado en memoria y emite evento SignalR
- `registrarEmocion(sesionId, preguntaId, emocion, respuesta)` → persiste resultado
- `finalizarSesion(sesionId)` → cierra sesión y emite evento `SesionFinalizada`

---

### SSD 4 — Visualización web en tiempo real

**Actor:** Evaluado (persona cuyas expresiones se analizan)

```
Evaluado          Web Browser (React)         API REST (SignalR Hub)
    │                   │                              │
    │── abrirURL() ─────►│                             │
    │                   │── conectarSignalR() ─────────►│
    │                   │◄── conexión establecida ──────│
    │◄── pantalla espera──│                             │
    │                   │                              │
    │        [Evaluador avanza pregunta — SSD 3]        │
    │                   │◄── evento PreguntaCambiada ───│
    │                   │    { texto, opciones, grupo } │
    │◄── mostrar pregunta──│                            │
    │                   │                              │
    │        [Siguiente pregunta]                       │
    │                   │◄── evento PreguntaCambiada ───│
    │◄── actualizar UI ────│                            │
    │                   │                              │
    │        [Sesión finalizada — SSD 3]                │
    │                   │◄── evento SesionFinalizada ───│
    │◄── "Análisis completo" ──│                        │
    │                   │                              │
    │    [Pérdida de conexión]                          │
    │                   │── reconexión automática ──────►│
    │                   │◄── última pregunta conocida ───│
```

**Operaciones del sistema:**

- `suscribirPreguntaCambiada()` → escucha evento WebSocket y actualiza componente React
- `obtenerEstadoActual()` → al reconectar, solicita la pregunta vigente en memoria del servidor

---

## Componentes

### API REST — `APICSHARP-ABML`

Núcleo del sistema. Expone endpoints REST genéricos y un hub de comunicación en tiempo real.

**Controladores:**

| Controlador                  | Ruta base               | Función                             |
| ---------------------------- | ----------------------- | ------------------------------------ |
| `AutenticacionController`  | `/api/autenticacion`  | Login y emisión de JWT              |
| `EntidadesController`      | `/api/entidades`      | CRUD genérico sobre cualquier tabla |
| `ConsultasController`      | `/api/consultas`      | Consultas SQL parametrizadas         |
| `ProcedimientosController` | `/api/procedimientos` | Ejecución de stored procedures      |
| `EstructurasController`    | `/api/estructuras`    | Introspección de esquema de BD      |
| `PreguntasController`      | `/api/preguntas`      | Envío de preguntas vía SignalR     |
| `DiagnosticoController`    | `/api/diagnostico`    | Health check de API y BD             |

**Documentación interactiva:**

- Swagger UI: `http://localhost:{puerto}/swagger`
- ReDoc: `http://localhost:{puerto}/redoc`

---

### Aplicación de escritorio — `Desktop-ABML`

Interfaz principal del evaluador. Gestiona la captura, el análisis y el control de la sesión.

**Módulos:**

| Módulo      | Archivo                       | Responsabilidad                                   |
| ------------ | ----------------------------- | ------------------------------------------------- |
| Captura      | `model/capture.py`          | Captura de pantalla/cámara (mss + win32)         |
| Analizador   | `model/emotion_analyzer.py` | Detección de emociones por visión computacional |
| Sesión      | `model/session_manager.py`  | Persistencia local y en API                       |
| Grupos       | `model/groups_manager.py`   | Recuperación de grupos de preguntas              |
| UI Principal | `ui/pages/main_menu.py`     | Menú de navegación                              |
| UI Config    | `ui/pages/config_page.py`   | Configuración de sesión                         |
| UI Análisis | `ui/pages/analysis_page.py` | Panel de análisis en tiempo real                 |

---

### Sitio web — `WebSite-ABMLL`

Pantalla que ve el evaluado durante la sesión. Se actualiza automáticamente mediante WebSocket.

**Componentes React:**

| Componente         | Archivo                               | Responsabilidad                                             |
| ------------------ | ------------------------------------- | ----------------------------------------------------------- |
| `PreguntaActual` | `src/components/PreguntaActual.jsx` | Muestra la pregunta activa                                  |
| `useSignalR`     | `src/hooks/useSignalR.js`           | Gestión de conexión WebSocket con reconexión automática |

---

## Stack tecnológico

```
Backend          C# / ASP.NET Core 9.0 · Dapper · SignalR · JWT · BCrypt
Bases de datos   SQL Server · PostgreSQL · MySQL · MariaDB
Frontend web     React 19 · Vite 8 · @microsoft/signalr
Desktop          Python 3 · CustomTkinter · OpenCV · mss · pywin32 · Pillow
```

---

## Requisitos previos

| Componente    | Requisito                                    |
| ------------- | -------------------------------------------- |
| API           | .NET SDK 9.0+                                |
| Web           | Node.js 18+                                  |
| Desktop       | Python 3.8+                                  |
| Base de datos | SQL Server / PostgreSQL / MySQL (cualquiera) |

---

## Instalación y configuración

### 1. API REST

```bash
cd APICSHARP-ABML

# Copiar y editar configuración
cp appsettings.example.json appsettings.json
# Editar: cadena de conexión, clave JWT, proveedor de BD

dotnet restore
dotnet run
```

### 2. Sitio web

```bash
cd WebSite-ABMLL

npm install

# Crear .env con la URL de la API
echo "VITE_API_URL=http://localhost:5000" > .env

npm run dev
```

### 3. Aplicación de escritorio

```bash
cd Desktop-ABML

pip install customtkinter opencv-python mss pygetwindow pywin32 pillow requests

# Editar model/config.py con la URL de la API y credenciales
python main.py
```

---

## Estructura del proyecto

```
Proyecto_Grado_USB/
├── APICSHARP-ABML/          # Backend .NET 9
│   ├── Controllers/
│   ├── Servicios/
│   ├── Repositorios/
│   ├── Hubs/
│   └── Modelos/
├── Desktop-ABML/            # Aplicación Python
│   ├── model/
│   ├── ui/
│   │   └── pages/
│   └── assets/
└── WebSite-ABMLL/           # Frontend React
    └── src/
        ├── components/
        └── hooks/
```

---

## Despliegue

| Subsistema | Plataforma            | URL                                               |
| ---------- | --------------------- | ------------------------------------------------- |
| API REST   | Railway               | `https://api-proyect-production.up.railway.app` |
| Sitio web  | Vercel                | `https://preguntas-sigma.vercel.app`            |
| Desktop    | Windows (PyInstaller) | Ejecutable local                                  |

---

## Equipo

Proyecto de grado desarrollado por:

- **Jeferson** — API REST, Módulo web (WebSite-ABMLL)
- **Lucas** — Arquitectura backend, Aplicación de escritorio (Desktop-ABML)
