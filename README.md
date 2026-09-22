# ScanQR PROA

Aplicación de escritorio desarrollada en Python para gestionar estudiantes y asignarles un aula mediante códigos QR.

El proyecto está pensado para utilizarse en el contexto de exámenes. Permite registrar los datos de un estudiante, guardar esa información en una base de datos SQLite, generar un código QR y luego utilizar una cámara para leer ese QR y mostrar rápidamente el aula asignada.

## ¿Qué hace el programa?

El funcionamiento principal se divide en dos partes:

1. **Registrar un estudiante**
   - Se completan los datos del estudiante.
   - Los datos se guardan en una base de datos SQLite.
   - Se genera un código QR con los datos principales.
   - La imagen del QR se guarda en la carpeta `qrcodes`.
   - El QR también se puede guardar en otra ubicación.

2. **Escanear un código QR**
   - Se abre la cámara de la computadora.
   - OpenCV busca códigos QR en la imagen.
   - Cuando encuentra uno, lee la información.
   - El programa interpreta los datos en formato JSON.
   - Se muestra el nombre, DNI y aula asignada.

## Tecnologías utilizadas

- **Python:** lenguaje principal del proyecto.
- **Tkinter:** creación de las ventanas, botones, formularios y demás elementos de la interfaz.
- **OpenCV (`cv2`):** acceso a la cámara y lectura de códigos QR.
- **Pillow (`PIL`):** apertura, redimensionamiento y visualización de imágenes.
- **SQLite (`sqlite3`):** almacenamiento de los datos de los estudiantes.
- **qrcode:** generación de las imágenes de los códigos QR.
- **JSON:** organización de los datos que se guardan dentro de cada QR.
- **os:** manejo de carpetas y archivos.
- **datetime:** registro de fecha y hora.
- **shutil:** copia de las imágenes QR cuando se utiliza la opción de guardar una copia.

## Estructura del proyecto

La estructura actual del proyecto es aproximadamente la siguiente:

```text
scanqr-proa/
│
├── escáner_aulas.py
├── examenes.db
├── PROAico.ico
├── PROA LOGO1.png
├── nuevo_estudiante.png
├── codigo_qr.png
├── guardar.png
├── compartir.png
│
└── qrcodes/
    ├── qr_12345678.png
    ├── qr_12345678-Juan ...
    ├── qr_35678987.png
    └── ...
```

### `escáner_aulas.py`

Es el archivo principal de la aplicación.

Contiene:

- La conexión y creación de la base de datos.
- Las funciones para guardar estudiantes.
- La generación de códigos QR.
- La ventana para registrar estudiantes.
- La ventana del escáner.
- El menú principal.
- El inicio de la aplicación.

### `examenes.db`

Es la base de datos SQLite del proyecto.

Actualmente contiene la tabla `estudiantes`, que guarda:

- DNI
- Nombre
- Apellido
- Localidad
- Colegio
- Curso
- Aula asignada
- Fecha de registro
- Ruta de la imagen QR

La base de datos se crea automáticamente si no existe cuando se inicia el programa.

### `qrcodes/`

Carpeta donde se guardan las imágenes de los códigos QR generados por el programa.

### Imágenes

Los archivos:

- `PROA LOGO1.png`
- `nuevo_estudiante.png`
- `codigo_qr.png`
- `guardar.png`
- `compartir.png`

se utilizan como recursos visuales de la interfaz.

### `PROAico.ico`

Es el ícono utilizado por las ventanas de la aplicación.

## Cómo funciona el QR

El QR no guarda una imagen ni una tabla de la base de datos. Guarda un texto con formato JSON.

Por ejemplo:

```json
{
    "dni": "45123456",
    "nombre_completo": "Juan Pérez",
    "aula": "A-01"
}
```

Cuando el escáner encuentra el QR:

```text
Cámara
  ↓
OpenCV
  ↓
Código QR
  ↓
Texto JSON
  ↓
Python interpreta el JSON
  ↓
Se muestran los datos
```

Esto permite que la información dentro del QR esté organizada y sea fácil de leer desde Python.

## Base de datos

La aplicación utiliza SQLite, por lo que no necesita un servidor de base de datos externo.

La tabla principal es:

```sql
CREATE TABLE IF NOT EXISTS estudiantes (
    dni TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    apellido TEXT NOT NULL,
    localidad TEXT,
    colegio TEXT,
    curso TEXT,
    aula_asignada TEXT NOT NULL,
    fecha_registro TEXT,
    qr_path TEXT
)
```

El DNI funciona como identificador principal del estudiante.

## Requisitos

Se necesita tener instalado:

- Python 3
- Tkinter
- OpenCV
- Pillow
- qrcode

Las bibliotecas externas se pueden instalar con:

```bash
pip install opencv-python pillow qrcode
```

`sqlite3`, `json`, `os`, `datetime` y `shutil` forman parte de Python y no necesitan instalarse mediante `pip`.

En algunas instalaciones de Python para Windows, Tkinter puede venir incluido. Si no está disponible, hay que instalar una versión de Python que lo incluya.

## Cómo ejecutar el programa

Desde la carpeta del proyecto:

```bash
python escáner_aulas.py
```

También se puede ejecutar desde un editor como Visual Studio Code.

Es importante ejecutar el programa desde la carpeta principal del proyecto, porque el código busca allí las imágenes y el archivo de ícono.

## Importante antes de subir el proyecto a GitHub

El archivo `examenes.db` contiene datos almacenados por la aplicación. Si contiene datos reales de estudiantes, no debería publicarse en un repositorio público.

Por el mismo motivo, las imágenes de la carpeta `qrcodes` pueden contener información personal dentro de sus códigos QR.

Para un repositorio público de GitHub, se recomienda utilizar un archivo `.gitignore` para evitar subir:

```gitignore
examenes.db
qrcodes/
__pycache__/
*.pyc
```

Las imágenes de ejemplo y los recursos gráficos de la interfaz sí pueden mantenerse en el repositorio si no contienen información personal.

## Estado actual del proyecto

Actualmente el programa permite:

- Registrar estudiantes.
- Validar algunos campos obligatorios.
- Guardar estudiantes en SQLite.
- Generar códigos QR.
- Guardar las imágenes QR.
- Previsualizar el QR generado.
- Guardar una copia del QR en otra ubicación.
- Utilizar la cámara de la computadora.
- Detectar códigos QR.
- Leer los datos en formato JSON.
- Mostrar el estudiante y el aula asignada.
- Reiniciar el escáner para leer otro código.

## Posibles mejoras futuras

Algunas funciones que se pueden agregar en futuras versiones:

- Buscar estudiantes por DNI, nombre o apellido.
- Editar los datos de un estudiante.
- Eliminar estudiantes.
- Detectar y avisar cuando un DNI ya está registrado.
- Registrar un historial de escaneos.
- Guardar la fecha y hora de cada escaneo.
- Permitir seleccionar qué cámara utilizar.
- Mejorar el diseño de la interfaz.
- Mostrar un indicador cuando la cámara está conectada.
- Separar el proyecto en varios archivos para facilitar su mantenimiento.
- Agregar una pantalla de administración de estudiantes.
- Agregar estadísticas de estudiantes y escaneos.

## Objetivo del proyecto

El objetivo de ScanQR PROA es utilizar herramientas de programación para simplificar la organización de estudiantes y aulas durante los exámenes, combinando una interfaz gráfica sencilla con una base de datos local y el uso de códigos QR.

## Repositorio

El proyecto se encuentra en:

https://github.com/joaco-trejo/scanqr-proa
