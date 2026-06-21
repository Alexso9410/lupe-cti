# Instalación de TryHackMe Room Scraper - Edge Extension

## Paso 1: Preparar la extensión

1. Cierra todos los archivos de la extensión que creé
2. Abre Edge y ve a la página de extensiones:
   - Escribe en la barra de direcciones: `edge://extensions/`
   - O ve a: Menú (⋯) → Extensiones → Gestionar extensiones

## Paso 2: Activar modo desarrollador

En la página `edge://extensions/`:
1. Activa el interruptor **"Modo de desarrollador"** (abajo a la izquierda)
2. Verás que aparecen nuevos botones

## Paso 3: Cargar la extensión

1. Haz clic en **"Cargar desempaquetada"** (Load unpacked)
2. Navega a esta carpeta:
   ```
   C:\Users\usuario\Documents\proyectos IA aplicada\centinela\tryhackme-obsidian-automation\tryhackme-scraper-extension
   ```
3. Selecciona la carpeta y haz clic **"Seleccionar carpeta"**

## Paso 4: Verificar instalación

- Verás la extensión "TryHackMe Room Scraper" en tu lista de extensiones
- Fíjala a la barra de herramientas:
  - Click en el icono 🧩 (extensiones) en la barra de Edge
  - Busca "TryHackMe Room Scraper" 
  - Click en el 📌 para fijarla

## Paso 5: Usar la extensión

1. Ve a cualquier room de TryHackMe (ej: `tryhackme.com/room/threatmodelling`)
2. Haz clic en el icono de la extensión 🔷
3. Click en **"📥 Extraer Contenido"**
4. Espera a que complete (verás el progreso)
5. Click en **"💾 Descargar JSON"**

## Paso 6: Procesar con Ollama

Abre terminal en la carpeta del proyecto y ejecuta:

```bash
cd "C:\Users\usuario\Documents\proyectos IA aplicada\centinela\tryhackme-obsidian-automation"
python process_to_obsidian.py
```

Elige la opción **"2. Procesar archivo JSON existente"** y selecciona el archivo descargado.

## Troubleshooting

### Si la extensión no aparece:
- Verifica que todos los archivos estén en la carpeta:
  - `manifest.json`
  - `popup.html`
  - `popup.js`
  - `content.js`

### Si no extrae tareas:
- Asegúrate de estar en una URL como `tryhackme.com/room/NOMBRE`
- Recarga la página y vuelve a intentar
- Abre la consola (F12) y revisa si hay errores

### Si Edge muestra "Permisos insuficientes":
- La extensión necesita permisos para tryhackme.com
- Ve a `edge://extensions/` → Detalles de la extensión → Permisos del sitio
- Asegúrate de que "tryhackme.com" esté permitido

## Nota importante

La extensión **no** abre todas las pestañas simultáneamente (no es posible por el acordeón). En cambio:
1. Expande la primera tarea
2. Captura su contenido
3. Guarda el contenido en memoria
4. Pasa a la siguiente tarea
5. Al final, genera un JSON con TODAS las tareas

Así obtienes todo el contenido sin necesidad de que todas las pestañas estén abiertas a la vez.
