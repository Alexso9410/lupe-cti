#!/usr/bin/env python3
"""
TryHackMe Full Room Scraper con Playwright
Extrae contenido de TODAS las pestañas acordeón de una room de TryHackMe
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import requests

# Ollama config
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "minimax-m2.7:cloud"


def scrape_tryhackme_playwright(url: str, output_dir: str = None):
    """
    Usa Playwright con Edge persistente (con tu sesión logueada) para navegar y extraer contenido
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright no está instalado")
        print("💡 Instálalo con: pip install playwright")
        print("💡 Luego ejecuta: playwright install chromium")
        return None
    
    print(f"🌐 Navegando a: {url}")
    
    with sync_playwright() as p:
        # Usar perfil persistente de Edge para mantener sesión logueada
        # Busca el directorio de perfil de Edge
        edge_profile_paths = [
            Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data",
            Path.home() / ".config" / "microsoft-edge" / "Default",  # Linux
            Path.home() / "Library" / "Application Support" / "Microsoft Edge"  # macOS
        ]
        
        profile_path = None
        for path in edge_profile_paths:
            if path.exists():
                profile_path = str(path)
                break
        
        if profile_path:
            print(f"✅ Usando perfil de Edge existente: {profile_path}")
            print("   (Mantiene tu sesión logueada)")
            
            try:
                # Lanzar con contexto persistente
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_path,
                    channel="msedge",
                    headless=False,
                    viewport={'width': 1920, 'height': 1080},
                    accept_downloads=True
                )
                page = context.new_page()
            except Exception as e:
                print(f"⚠️ No se pudo usar perfil persistente: {e}")
                print("🔄 Usando Edge normal (sin sesión)...")
                browser = p.chromium.launch(headless=False, channel="msedge")
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()
        else:
            print("⚠️ No se encontró perfil de Edge")
            print("🔄 Usando Edge normal (sin sesión)...")
            browser = p.chromium.launch(headless=False, channel="msedge")
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
        
        # Navegar a la URL
        page.goto(url, wait_until='networkidle', timeout=60000)
        print("✅ Página cargada")
        
        # Esperar a que cargue el contenido (selectores más genéricos)
        try:
            # Intentar múltiples selectores comunes de TryHackMe
            selectors_to_try = [
                '[data-testid="task-panel"]',
                '.room-task',
                '[class*="task"]',
                'main',
                'article',
                '#root',
                'body'
            ]
            
            found_selector = None
            for selector in selectors_to_try:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    found_selector = selector
                    print(f"✅ Encontrado selector: {selector}")
                    break
                except:
                    continue
            
            if not found_selector:
                print("⚠️ Usando espera genérica...")
                page.wait_for_timeout(5000)
                
        except Exception as e:
            print(f"⚠️ Error esperando selector: {e}")
            print("🔄 Continuando con espera genérica...")
            page.wait_for_timeout(5000)
        
        print("📋 Buscando tareas...")
        
        # Encontrar todos los headers de tareas (múltiples intentos con selectores)
        task_headers = []
        header_selectors = [
            '[data-testid="task-header"]',
            '.task-header',
            '[class*="TaskTitle"]',
            '[class*="task-title"]',
            '[data-state]',
            'button[class*="accordion"]',
            'div[class*="task-header"]'
        ]
        
        for selector in header_selectors:
            task_headers = page.query_selector_all(selector)
            if len(task_headers) > 0:
                print(f"✅ Encontradas {len(task_headers)} tareas con selector: {selector}")
                break
        
        if not task_headers:
            print("⚠️ No se encontraron tareas estructuradas")
            print("🔄 Extrayendo contenido completo de la página...")
            
            # Fallback: extraer todo el contenido visible
            full_content = page.evaluate('''() => {
                const main = document.querySelector('main') || document.querySelector('[class*="room"]') || document.body;
                return {
                    title: document.title,
                    text: main.innerText.substring(0, 15000),
                    html: main.innerHTML.substring(0, 50000)
                };
            }''')
            
            all_tasks = [{
                'index': 0,
                'title': full_content.get('title', 'Contenido completo'),
                'content': full_content.get('text', ''),
                'url': url
            }]
            
            browser.close()
            
            # Guardar directamente
            if output_dir:
                output_path = Path(output_dir)
            else:
                output_path = Path.home() / "Downloads"
            
            output_path.mkdir(parents=True, exist_ok=True)
            
            room_name = url.split('/room/')[-1].split('/')[0] if '/room/' in url else 'tryhackme_room'
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{room_name}_{timestamp}.json"
            output_file = output_path / filename
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'url': url,
                    'scraped_at': datetime.now().isoformat(),
                    'tasks': all_tasks
                }, f, ensure_ascii=False, indent=2)
            
            print(f"\n✅ Scraping completado (fallback)")
            print(f"📁 Guardado en: {output_file}")
            print(f"📊 Tareas extraídas: {len(all_tasks)}")
            
            return str(output_file)
        
        print(f"✅ Encontradas {len(task_headers)} tareas")
        
        all_tasks = []
        
        for idx, header in enumerate(task_headers):
            try:
                # Obtener título de la tarea
                title = header.inner_text().strip()[:100]  # Limitar longitud
                print(f"\n📖 Tarea {idx+1}: {title}")
                
                # Hacer clic para expandir (con manejo de errores mejorado)
                try:
                    # Verificar si el elemento es visible antes de hacer clic
                    is_visible = header.is_visible()
                    if is_visible:
                        header.click(timeout=5000)
                        page.wait_for_timeout(1500)  # Esperar a que cargue contenido
                    else:
                        print(f"   ⚠️ Tarea {idx+1} no visible, intentando scroll...")
                        header.scroll_into_view_if_needed()
                        page.wait_for_timeout(500)
                        if header.is_visible():
                            header.click(timeout=5000)
                            page.wait_for_timeout(1500)
                        else:
                            print(f"   ⚠️ No se pudo clickear tarea {idx+1}")
                            continue
                except Exception as click_error:
                    print(f"   ⚠️ Error al hacer clic: {click_error}")
                    continue
                
                # Buscar contenido de la tarea expandida
                # El contenido suele estar en el siguiente elemento sibling o en un panel cercano
                content = ""
                
                # Intentar múltiples estrategias para encontrar el contenido
                content_selectors = [
                    '[data-testid="task-content"]',
                    '.task-content',
                    '.accordion-content',
                    '[class*="TaskBody"]',
                    '[class*="task-body"]'
                ]
                
                for selector in content_selectors:
                    content_el = page.query_selector(selector)
                    if content_el:
                        content = content_el.inner_text()
                        break
                
                # Si no encontró con selectores, intenta obtener el HTML del área visible
                if not content:
                    # Obtener todo el texto visible en la página después del clic
                    content = page.evaluate('''() => {
                        const main = document.querySelector('main') || document.body;
                        return main.innerText.substring(0, 5000);  // Limitar para no saturar
                    }''')
                
                all_tasks.append({
                    'index': idx,
                    'title': title,
                    'content': content,
                    'url': url
                })
                
                # Scroll para ver siguiente tarea
                header.scroll_into_view_if_needed()
                
            except Exception as e:
                print(f"⚠️ Error en tarea {idx+1}: {e}")
                continue
        
        # Cerrar navegador/contexto
        try:
            if 'browser' in locals():
                browser.close()
            elif 'context' in locals():
                context.close()
        except:
            pass
        
        # Guardar resultado
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path.home() / "Downloads"
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Sanitizar nombre de archivo
        room_name = url.split('/room/')[-1].split('/')[0] if '/room/' in url else 'tryhackme_room'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{room_name}_{timestamp}.json"
        
        output_file = output_path / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'tasks': all_tasks
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Scraping completado")
        print(f"📁 Guardado en: {output_file}")
        print(f"📊 Tareas extraídas: {len(all_tasks)}")
        
        return str(output_file)


def process_with_ollama(json_file: str, vault_path: str = None):
    """Procesa el JSON con Ollama y genera nota Obsidian"""
    
    print("\n🤖 Verificando conexión con Ollama...")
    
    # Verificar que Ollama está corriendo
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code != 200:
            print("❌ Ollama no responde correctamente")
            print("💡 Asegúrate de que Ollama esté corriendo: ollama serve")
            print("🔄 Generando nota sin resumen de IA...")
            ai_summary = "_Ollama no disponible - Resumen no generado_"
        else:
            print("✅ Ollama conectado")
    except Exception as e:
        print(f"⚠️ No se pudo conectar a Ollama: {e}")
        print("💡 Asegúrate de que Ollama esté corriendo en http://localhost:11434")
        print("🔄 Generando nota sin resumen de IA...")
        ai_summary = "_Ollama no disponible - Resumen no generado_"
        # Continuamos sin Ollama
    
    print("\n📝 Procesando contenido...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    tasks = data.get('tasks', [])
    
    if not tasks:
        print("❌ No hay tareas para procesar")
        return
    
    # Solo llamar a Ollama si está disponible y no tenemos mensaje de error
    if ai_summary == "":
        # Preparar contenido para resumen
        summary_content = "\n\n".join([
            f"## {t['title']}\n{t['content'][:800]}" 
            for t in tasks[:5]
        ])
        
        # Llamar a Ollama
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": f"""Resume el siguiente contenido de TryHackMe:

{summary_content}

Genera:
1. Resumen ejecutivo (2-3 párrafos)
2. Lista de conceptos clave con definiciones
3. Herramientas/comandos mencionados
4. Puntos importantes para recordar

Formato: Markdown""",
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 2000}
                },
                timeout=120
            )
            
            ai_summary = response.json().get('response', 'No se pudo generar resumen')
            
        except Exception as e:
            print(f"⚠️ Error con Ollama: {e}")
            ai_summary = "_Error al generar resumen con Ollama_"
    
    # Generar nota Obsidian
    room_name = Path(json_file).stem.split('_')[0]
    
    note = f"""---
title: {room_name}
source: TryHackMe
url: {data.get('url', '')}
date: {datetime.now().strftime('%Y-%m-%d')}
tags: [tryhackme, cybersecurity]
model: {OLLAMA_MODEL}
---

# {room_name.replace('-', ' ').title()}

> 📅 Procesado: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> 🤖 Modelo: `{OLLAMA_MODEL}`

## 📋 Resumen con IA

{ai_summary}

## 📚 Contenido Completo

"""
    
    # Añadir cada tarea
    for task in tasks:
        note += f"""### {task['title']}

{task['content']}

---

"""
    
    # Determinar ruta de salida
    if vault_path:
        output_dir = Path(vault_path) / "TryHackMe"
    else:
        output_dir = Path.home() / "Documents" / "Obsidian Vault" / "TryHackMe"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{room_name}.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(note)
    
    print(f"✅ Nota generada: {output_file}")
    return str(output_file)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape TryHackMe room con Playwright')
    parser.add_argument('--url', '-u', help='URL de la room (ej: https://tryhackme.com/room/threatmodelling)')
    parser.add_argument('--vault', '-v', help='Ruta al vault de Obsidian')
    parser.add_argument('--output', '-o', help='Directorio de salida')
    
    args = parser.parse_args()
    
    if not args.url:
        # Modo interactivo
        url = input("🔗 URL de la room de TryHackMe: ").strip()
    else:
        url = args.url
    
    if not url.startswith('http'):
        url = f"https://tryhackme.com/room/{url}"
    
    # Paso 1: Scrape
    json_file = scrape_tryhackme_playwright(url, args.output)
    
    if json_file:
        # Paso 2: Procesar con Ollama
        process_with_ollama(json_file, args.vault)
    else:
        print("❌ El scraping falló")
        sys.exit(1)
