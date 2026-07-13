# Calculadora de peso por calibre

Esta aplicación calcula automáticamente una fórmula lineal y una fórmula
potencial para cada variedad usando el archivo Excel histórico.

## Estructura de carpetas

calculadora_peso_variedad/
├── app.py
├── requirements.txt
└── data/
    └── Historico_Calibres_Peso.xlsx

## Columnas requeridas en el Excel

La hoja `Hoja1` debe contener estas columnas:

- `variety`
- `Calibre Promedio`
- `Peso Promedio`

Las demás columnas pueden permanecer en el archivo.

## Ejecutar en tu computadora

1. Instala Python 3.11 o 3.12.
2. Abre una terminal dentro de la carpeta del proyecto.
3. Crea un entorno virtual:

   Windows:
   python -m venv .venv
   .venv\Scripts\activate

4. Instala las dependencias:

   pip install -r requirements.txt

5. Ejecuta la aplicación:

   streamlit run app.py

6. Se abrirá en el navegador. Normalmente:
   http://localhost:8501

## Actualizar la información

Reemplaza el archivo:

data/Historico_Calibres_Peso.xlsx

Mantén el mismo nombre, hoja y columnas. Al reiniciar la aplicación,
las fórmulas se recalcularán automáticamente por variedad.

## Publicar con Streamlit Community Cloud

1. Crea un repositorio en GitHub.
2. Sube `app.py`, `requirements.txt` y la carpeta `data`.
3. Ingresa a Streamlit Community Cloud.
4. Selecciona el repositorio.
5. Indica `app.py` como archivo principal.
6. Presiona Deploy.

La plataforma generará un enlace público para compartir con los usuarios.
