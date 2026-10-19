# Knowledge System Integration

Aplicacion web que integra un frontend desarrollado con React y TypeScript con una API backend desarrollada en Flask y una base de datos SQLite.

## Tecnologias

- **Frontend:** React, TypeScript, Vite y Material UI.
- **Backend:** Python y Flask.
- **Base de datos:** SQLite.
- **Pruebas:** pytest.

## Estructura del proyecto

- `frontend/`: interfaz web.
- `backend/`: API, logica de negocio, esquema SQLite y pruebas.

## Requisitos previos

- Node.js y npm.
- Python 3.10 o superior.

## Instalacion y ejecucion

### 1. Backend

Desde la raiz del repositorio, abrir una terminal de PowerShell y ejecutar:

```powershell
Set-Location .\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

El backend quedara disponible en `http://127.0.0.1:5000`.

La base de datos `base.db` se crea localmente al iniciar la aplicacion si no existe. No es necesario descargar una base de datos previa.

Si PowerShell bloquea la activacion del entorno virtual, se puede instalar y ejecutar usando la ruta directa de Python del entorno virtual:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

### 2. Frontend

Mantener el backend ejecutandose y abrir otra terminal:

```powershell
Set-Location "$env:USERPROFILE\Downloads\Knowledge-System-Integration-remoto\frontend"
npm ci
npm run dev
```
Si sale error en la powershell se debe colocar npm.cmd. en lugar de npm solo
```
Abrir la URL local que indique Vite en la terminal, normalmente `http://localhost:5173`.

Las peticiones que comienzan con `/api` se redirigen al backend local en el puerto 5000 mediante la configuracion de Vite.

### 3. Pruebas del backend

Con las dependencias instaladas, desde la carpeta `backend` ejecutar:

```powershell
python -m pytest
```

## Configuracion local de demostracion

El modo demo puede habilitar un comportamiento especial de autenticacion. Usarlo solamente en un entorno local y controlado, nunca en produccion.

En PowerShell, antes de iniciar Flask:

```powershell
$env:MODO_DEMO = "1"
python -m flask --app app run --debug
```

Para desactivarlo en esa terminal:

```powershell
Remove-Item Env:MODO_DEMO -ErrorAction SilentlyContinue
```

## Archivos locales

La base de datos, los entornos virtuales, las dependencias instaladas y los archivos de entorno no deben subirse al repositorio. Consultar `.gitignore`.
