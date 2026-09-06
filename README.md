# PS Card Generator

Herramienta de escritorio para Windows que automatiza Adobe Photoshop y genera
multiples imagenes a partir de una plantilla PSD, reemplazando el texto de una
capa especifica con una lista de nombres.

---

## Requisitos

- Windows 10 o superior
- Adobe Photoshop instalado (CC o superior)
- Python 3.10 o superior

---

## Instalacion

1. Clona el repositorio o descarga los archivos:

```
git clone https://github.com/tu-usuario/ps-card-generator.git
cd ps-card-generator
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

Ejecuta la aplicacion con:

```
python main.py
```

### Pasos dentro de la aplicacion

1. **Plantilla PSD**: Selecciona el archivo `.psd` que contiene el diseno base.
2. **Capa de texto**: Escribe el nombre exacto de la capa de texto a reemplazar,
   o presiona "CARGAR CAPAS" para elegir desde una lista desplegable con todas
   las capas de texto detectadas en el documento.
3. **Lista de nombres**: Carga un archivo CSV o Excel (`.xlsx` / `.xls`) cuya
   primera columna contenga los nombres, o pegalos directamente en el cuadro
   de texto (uno por linea).
4. **Carpeta de destino**: Elige donde se guardaran las imagenes generadas.
5. **Formato**: Selecciona JPG o PNG.
6. Presiona **GENERAR TARJETAS**.

La barra de progreso y el log en pantalla muestran el avance en tiempo real.
Al finalizar, se abre una ventana de resumen con la opcion de abrir la carpeta.

### Nombre de los archivos generados

Cada imagen se guarda con el formato `tarjeta_<nombre>.jpg` (o `.png`).
Los caracteres invalidos en nombres de archivo (`/ \ : * ? " < > |`) se
reemplazan automaticamente con guion bajo.

---

## Empaquetar como .exe

Para distribuir la aplicacion sin necesidad de instalar Python:

```
pyinstaller --noconfirm --onefile --windowed --name "PSCardGenerator" main.py
```

El ejecutable quedara en la carpeta `dist/`.

Notas importantes para el build:
- Ejecuta el comando en el mismo entorno donde estan instaladas las dependencias.
- Si `customtkinter` tiene assets (temas, imagenes), puede ser necesario agregar
  `--add-data` para incluirlos. Consulta la documentacion de customtkinter para PyInstaller.

---

## Estructura del proyecto

```
ps-card-generator/
  main.py                 # Interfaz grafica (CustomTkinter)
  photoshop_manager.py    # Logica de automatizacion de Photoshop
  requirements.txt        # Dependencias
  .gitignore
  README.md
```

---

## Notas

- La aplicacion requiere que Adobe Photoshop este instalado; lo inicia
  automaticamente en segundo plano si no esta abierto.
- La plantilla PSD nunca se modifica; los cambios se revierten al terminar.
- Soporta capas de texto anidadas dentro de grupos (LayerSets).
