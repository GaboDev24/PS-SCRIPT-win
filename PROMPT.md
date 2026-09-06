Quiero que crees un programa en Python para Windows con interfaz gráfica (usando Tkinter) 
que automatice Adobe Photoshop para generar múltiples imágenes a partir de una plantilla PSD, 
cambiando el texto de una capa específica por distintos nombres.

CONTEXTO Y OBJETIVO:
Tengo una tarjeta diseñada en Photoshop (.psd) para un jardín de infantes, con una capa de 
texto que contiene un nombre de ejemplo. Quiero generar una imagen por cada alumno, 
reemplazando el texto de esa capa por el nombre real, y exportando cada una como archivo 
individual (JPG o PNG), manteniendo intactos todos los efectos de capa (sombras, estilos, etc.).

REQUISITOS FUNCIONALES:
1. Usar la librería `photoshop-python-api` para controlar Photoshop vía su motor de scripting 
   (COM, Windows). El programa debe abrir Photoshop en segundo plano si no está abierto.
2. Interfaz gráfica (Tkinter) con:
   - Un botón para seleccionar el archivo .psd de la plantilla
   - Un campo para escribir el nombre exacto de la capa de texto a reemplazar (o un dropdown 
     que liste automáticamente las capas de texto del PSD una vez cargado)
   - Un botón para cargar la lista de nombres desde un archivo Excel/CSV (una columna con los 
     nombres), o alternativamente un cuadro de texto donde pegar los nombres, uno por línea
   - Selector de carpeta de destino para las imágenes generadas
   - Selector de formato de salida: JPG o PNG
   - Un botón "Generar" que procese todos los nombres
   - Una barra de progreso o log en pantalla que muestre qué tarjeta se está generando 
     (ej: "Generando tarjeta 3/25: Mateo")
3. Por cada nombre en la lista, el programa debe:
   - Abrir el PSD (o reutilizar el documento ya abierto para no reabrir cada vez, lo que sea 
     más rápido y estable)
   - Ubicar la capa de texto por el nombre indicado
   - Reemplazar el contenido de esa capa por el nombre actual
   - Exportar/guardar como imagen individual con un nombre de archivo tipo 
     "tarjeta_<nombre>.jpg" en la carpeta de destino
   - Revertir el documento a su estado original o cerrarlo sin guardar cambios, para no 
     corromper la plantilla original
4. Manejo de errores: si Photoshop no está instalado, si la capa no existe, si un nombre 
   tiene caracteres inválidos para nombre de archivo (tildes, espacios, ñ está bien pero 
   evitar / \ : * ? " < > |), etc. Mostrar el error en la interfaz sin cerrar el programa.
5. Al terminar, mostrar un mensaje con la cantidad de imágenes generadas exitosamente y la 
   ruta de la carpeta de salida, con opción de abrir esa carpeta directamente.

REQUISITOS TÉCNICOS:
- Python 3.10+, Windows
- Librerías: photoshop-python-api, tkinter (nativo), pandas u openpyxl (si se usa carga desde 
  Excel/CSV)
- Estructura de código limpia, separando la lógica de automatización de Photoshop (un módulo 
  aparte) de la interfaz gráfica
- Incluir un archivo requirements.txt
- Incluir instrucciones breves de instalación y uso en un README.md

Nada de emojis.

Sigue el diseño de DESIGN.md adaptado a ventana tkinter

Empaquetarlo como .exe con pyinstaller con un solo archivo.