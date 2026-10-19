# Knowledge System Integration

Aplicación web para integrar información de distintas fuentes y visualizar entidades y sus relaciones mediante un grafo interactivo. El sistema permite importar archivos Excel/CSV, crear entidades a partir de sus datos y detectar relaciones automáticamente cuando existen referencias identificables entre ellas.

## Tecnologías

- **Frontend:** React, TypeScript, Vite y Material UI.
- **Backend:** Python y Flask.
- **Base de datos:** SQLite.
- **Importación de archivos:** Excel y CSV.
- **Pruebas:** pytest.

## Estructura del proyecto

- `frontend/`: interfaz web, visualización del grafo e importación de archivos.
- `backend/`: API, lógica de negocio, autenticación, importación de datos, generación de relaciones y pruebas.
- `backend/base.db`: base de datos SQLite local, creada o inicializada según la configuración del backend.

## Requisitos previos

Instalar las siguientes herramientas:

- **Git:** https://git-scm.com/downloads
- **Node.js LTS:** https://nodejs.org/
- **Python 3.10 o superior**, compatible con las dependencias del proyecto.
- **PowerShell**, disponible en Windows.

Después de instalar Node.js o Python, cerrar y volver a abrir PowerShell para que se actualice la variable `PATH`.

Comprobar la instalación:

```powershell
git --version
node --version
npm.cmd --version
py --version
```

Si `py` no está disponible, comprobar Python con:

```powershell
python --version
```

## Instalación y ejecución

### 1. Descargar el repositorio

Si todavía no se descargó el proyecto:

```powershell
git clone https://github.com/4nyuria/Knowledge-System-Integration.git
cd Knowledge-System-Integration
```

Si ya se tiene el repositorio clonado, abrir PowerShell en su carpeta raíz.

La estructura esperada es:

```text
Knowledge-System-Integration/
├── frontend/
└── backend/
```

**Importante:** los comandos deben ejecutarse desde la carpeta correspondiente. El frontend y el backend se ejecutan en terminales separadas.

### 2. Preparar e iniciar el backend

Abrir una primera terminal de PowerShell y entrar en la carpeta del backend:

```powershell
Set-Location ".\backend"
```

Si se está ubicado fuera de la raíz del proyecto, primero hay que entrar en la carpeta donde se clonó el repositorio.

#### Crear el entorno virtual

```powershell
py -m venv .venv
```

Si el comando `py` no está disponible:

```powershell
python -m venv .venv
```

#### Instalar las dependencias

No es obligatorio activar el entorno virtual. Para evitar errores con las políticas de ejecución de PowerShell, se puede utilizar directamente el intérprete del entorno:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

#### Activar el modo demo

Para la demostración local, establecer la variable antes de iniciar Flask:

```powershell
$env:MODO_DEMO = "1"
```

#### Iniciar Flask

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

El backend estará disponible en:

http://127.0.0.1:5000

**Mantener esta terminal abierta mientras se utiliza la aplicación.**

### 3. Preparar e iniciar el frontend

Abrir una segunda terminal de PowerShell, sin cerrar la del backend.

Desde la raíz del repositorio, entrar en la carpeta del frontend:

```powershell
Set-Location ".\frontend"
```

Instalar las dependencias:

```powershell
npm.cmd ci
```

Si no existe `package-lock.json`, utilizar `npm.cmd install` en su lugar.

Iniciar el servidor de desarrollo:

```powershell
npm.cmd run dev
```

**Importante en Windows PowerShell:** utilizar `npm.cmd` en lugar de `npm` si aparece un error relacionado con la ejecución de `npm.ps1` o las políticas de ejecución de scripts.

La aplicación estará disponible normalmente en:

http://localhost:5173

Abrir la dirección indicada por Vite en la terminal si el puerto predeterminado está ocupado.

Las solicitudes que comienzan con `/api` se redirigen al backend local mediante la configuración del proxy de Vite.

## Funcionalidades actuales

### Importación de Excel/CSV

La aplicación permite cargar archivos compatibles para crear fuentes y entidades a partir de sus datos.

Durante la importación, el backend procesa los registros válidos y registra la información correspondiente en SQLite.

### Generación automática de relaciones

El backend utiliza la lógica definida en `relaciones.py` para detectar posibles relaciones entre entidades a partir de sus identificadores y referencias.

Por ejemplo, un pedido que incluya un identificador de cliente puede relacionarse con el cliente correspondiente si la referencia se resuelve de forma inequívoca.

**Importante:** no todos los archivos generan relaciones. Si un archivo contiene únicamente clientes y no incluye referencias a pedidos, productos u otras entidades, puede crear nodos sin generar relaciones nuevas. Los valores ambiguos o que no encuentran una coincidencia válida no deberían generar conexiones arbitrarias.

### Visualización del grafo

Las entidades y las relaciones obtenidas desde el backend se muestran en la interfaz web como nodos y conexiones del grafo.

## Usuario y autenticación en modo demo

El proyecto incluye rutas de autenticación. Para realizar pruebas locales de integración, se puede habilitar el modo demo mediante:

```powershell
$env:MODO_DEMO = "1"
```

Esta variable debe configurarse en la misma terminal desde la que se inicia Flask y antes de ejecutar el servidor.

Consideraciones:

- La variable es temporal y se pierde al cerrar la terminal.
- Si se reinicia Flask desde otra terminal, volver a configurarla.
- La existencia de un usuario en la base de datos no significa que exista una sesión iniciada.
- No se debe asumir que una instalación nueva contiene el mismo usuario de prueba que otra computadora.
- Si aparece la pantalla de inicio de sesión o una respuesta `401`, revisar la configuración actual de autenticación y el comportamiento del modo demo.
- No se debe inventar ni compartir una contraseña personal para solucionar errores de acceso.

El modo demo es únicamente para entornos locales y controlados. No debe utilizarse como configuración de seguridad en producción.

Para desactivar la variable en la terminal actual:

```powershell
Remove-Item Env:MODO_DEMO -ErrorAction SilentlyContinue
```

Después de modificar la variable de entorno, reiniciar Flask para aplicar la configuración.

## Base de datos y archivos locales

La aplicación utiliza SQLite. La base de datos local se encuentra en `backend/base.db`.

- Los datos importados se almacenan localmente y no se sincronizan automáticamente con las computadoras de otros integrantes.
- No borrar `base.db` si se quieren conservar los datos importados.
- No ejecutar `semilla.py` como solución a un problema de inicio: el script de semillas puede limpiar las tablas y volver a cargar datos.
- No subir al repositorio bases de datos con información privada, contraseñas ni archivos de configuración sensibles.
- Consultar `.gitignore` antes de realizar un commit.

En una instalación nueva, seguir el mecanismo de inicialización definido por el backend y comprobar que la base de datos se cree correctamente.

## Pruebas del backend

Desde una terminal ubicada en la carpeta `backend`, ejecutar:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Antes de ejecutar las pruebas, comprobar si utilizan una base de datos aislada. No ejecutar pruebas que reinicien o modifiquen datos importantes sin verificar su configuración.

## Solución de problemas frecuentes

### Error al ejecutar `npm`

Si aparece un error relacionado con `npm.ps1` o las políticas de ejecución de PowerShell, utilizar:

```powershell
npm.cmd ci
npm.cmd run dev
```

No es necesario cambiar la política de seguridad de PowerShell para utilizar `npm.cmd`.

### Error `ENOENT` o `package.json` no encontrado

Este error suele indicar que el comando se ejecutó desde una carpeta incorrecta.

Comprobar la ubicación actual:

```powershell
Get-Location
Get-ChildItem
```

Para ejecutar los comandos de npm, entrar en `frontend`, donde se encuentra `package.json`.

### Error al importar módulos de Python

Verificar que las dependencias se hayan instalado en el entorno virtual del backend:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Ejecutar Flask utilizando ese mismo intérprete.

### El frontend no se conecta con el backend

Comprobar que Flask esté ejecutándose en `http://127.0.0.1:5000` y que la terminal del backend no se haya cerrado.

También verificar que Vite esté utilizando la configuración de proxy del proyecto.

### Error de autenticación o respuesta `401`

Verificar que `MODO_DEMO` esté configurado antes de iniciar Flask. Si el error continúa, revisar las rutas de autenticación y la configuración actual del backend. No asumir que existe una sesión válida porque haya un usuario en SQLite.

### Puerto ocupado

Si los puertos `5000` o `5173` están ocupados, comprobar qué proceso los utiliza antes de detenerlo. Vite puede ofrecer otro puerto; en ese caso, abrir la dirección que indique la terminal.

## Resumen de inicio rápido

Una vez instaladas las dependencias, ejecutar desde la raíz del repositorio.

**Terminal 1 — Backend:**

```powershell
Set-Location ".\backend"
$env:MODO_DEMO = "1"
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

**Terminal 2 — Frontend:**

```powershell
Set-Location ".\frontend"
npm.cmd run dev
```

Abrir http://localhost:5173.

En la primera ejecución, crear el entorno virtual e instalar las dependencias siguiendo los pasos de instalación anteriores.
# EN CASO DE QUE SE SIGA TOMANDO EN CUENTA EL USUARIO REALIZAR LO SIGUIENTE:
1) cancela el flask por ahora y desde la ubicacion del back abrir nuevamente una powershell
2) desde alli ejecutar los siguientes comandos y volver a ejecutar el front
   ```powershell
   .\.venv\Scripts\python.exe .\semilla.py .\base.db
   $env:MODO_DEMO = "1"
   .\.venv\Scripts\python.exe -m flask --app app run --debug
   ```
