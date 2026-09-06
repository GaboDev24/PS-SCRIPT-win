# PS Card Generator

Herramienta de escritorio para Windows que automatiza Adobe Photoshop y genera
múltiples imágenes a partir de una plantilla PSD, reemplazando el texto de una
capa específica con una lista de nombres.

---

## Requisitos

- Windows 10 o superior
- Adobe Photoshop instalado (CC o superior)
- Python 3.10 o superior

---

## Instalación

1. Clona el repositorio o descarga los archivos:

```
git clone https://github.com/gabodev24/PS-SCRIPT-win.git
cd PS-SCRIPT-win
```

2. Crea un entorno virtual (recomendado):

```
python -m venv venv
venv\Scripts\activate
```

3. Instala las dependencias:

```
pip install -r requirements.txt
```

---

## Uso

Ejecuta la aplicación con:

```
python main.py
```

### Pasos dentro de la aplicacion

1. **Plantilla PSD**: Selecciona el archivo `.psd` que contiene el diseño base.
2. **Capa de texto**: Escribe el nombre exacto de la capa de texto a reemplazar,
   o presiona "CARGAR CAPAS" para elegir desde una lista desplegable con todas
   las capas de texto detectadas en el documento.
3. **Lista de nombres**: Carga un archivo CSV o Excel (`.xlsx` / `.xls`) cuya
   primera columna contenga los nombres, o pégalos directamente en el cuadro
   de texto (uno por línea).
4. **Carpeta de destino**: Elige dónde se guardarán las imágenes generadas.
5. **Formato**: Selecciona JPG o PNG.
6. Presiona **GENERAR TARJETAS**.

La barra de progreso y el log en pantalla muestran el avance en tiempo real.
Al finalizar, se abre una ventana de resumen con la opción de abrir la carpeta.

### Nombre de los archivos generados

Cada imagen se guarda con el formato `tarjeta_<nombre>.jpg` (o `.png`).
Los caracteres inválidos en nombres de archivo (`/ \ : * ? " < > |`) se
reemplazan automáticamente con guión bajo.

---

## Empaquetar como .exe

Para distribuir la aplicación sin necesidad de instalar Python:

```
pyinstaller --noconfirm --onefile --windowed --name "PSCardGenerator" main.py
```

El ejecutable quedará en la carpeta `dist/`.

Notas importantes para el build:
- Ejecuta el comando en el mismo entorno donde están instaladas las dependencias.
- Si `customtkinter` tiene assets (temas, imágenes), puede ser necesario agregar
  `--add-data` para incluirlos. Consulta la documentación de customtkinter para PyInstaller.

---

## Estructura del proyecto

```
ps-card-generator/
  main.py                 # Interfaz gráfica (CustomTkinter)
  photoshop_manager.py    # Lógica de automatización de Photoshop
  requirements.txt        # Dependencias
  .gitignore
  README.md
```

---

## Notas

- La aplicación requiere que Adobe Photoshop esté instalado; lo inicia
  automáticamente en segundo plano si no está abierto.
- La plantilla PSD nunca se modifica; los cambios se revierten al terminar.
- Soporta capas de texto anidadas dentro de grupos (LayerSets).
