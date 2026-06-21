// content.js - Script que corre en la página de TryHackMe
// Extrae contenido de las tareas de una room específica

(function() {
  'use strict';
  
  let isExtracting = false;
  
  // Escuchar mensajes del popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'extract') {
      if (isExtracting) {
        sendResponse({ success: false, error: 'Ya se está extrayendo contenido' });
        return true;
      }
      
      // Validar que estamos en una página de room
      if (!isRoomPage()) {
        sendResponse({ 
          success: false, 
          error: 'No estás en una room de TryHackMe. Ve a una URL como tryhackme.com/room/nombre-room' 
        });
        return true;
      }
      
      extractRoomContent().then(data => {
        sendResponse({ success: true, data: data });
      }).catch(error => {
        sendResponse({ success: false, error: error.message });
      });
      
      return true;
    }
  });
  
  function isRoomPage() {
    const url = window.location.href;
    return url.includes('/room/') && !url.includes('/hacktivities');
  }
  
  async function extractRoomContent() {
    isExtracting = true;
    
    const roomData = {
      url: window.location.href,
      room_name: extractRoomName(),
      extracted_at: new Date().toISOString(),
      tasks: []
    };
    
    try {
      console.log('[TryHackMe Scraper] Iniciando extracción...');
      
      // Buscar todos los headers de tareas
      const taskHeaders = findTaskHeaders();
      console.log(`[TryHackMe Scraper] Encontradas ${taskHeaders.length} tareas`);
      
      if (taskHeaders.length === 0) {
        throw new Error('No se encontraron tareas. Asegúrate de estar en una room con tareas visibles.');
      }
      
      // Extraer contenido de cada tarea
      for (let i = 0; i < taskHeaders.length; i++) {
        const header = taskHeaders[i];
        const taskTitle = header.textContent.trim().substring(0, 50);
        
        console.log(`[TryHackMe Scraper] Procesando tarea ${i + 1}/${taskHeaders.length}: ${taskTitle}`);
        
        // Notificar progreso
        chrome.runtime.sendMessage({
          action: 'progress',
          current: i + 1,
          total: taskHeaders.length,
          task_name: taskTitle
        });
        
        // Extraer contenido
        const taskData = await extractTaskContent(header, i);
        roomData.tasks.push(taskData);
        
        await sleep(500);
      }
      
      roomData.total_content_length = roomData.tasks.reduce((sum, t) => sum + (t.content?.length || 0), 0);
      
      console.log('[TryHackMe Scraper] Extracción completada');
      
    } catch (error) {
      console.error('[TryHackMe Scraper] Error:', error);
      throw error;
    } finally {
      isExtracting = false;
    }
    
    return roomData;
  }
  
  function findTaskHeaders() {
    const taskElements = [];
    
    // Intentar múltiples selectores para el contenedor principal
    let mainContent = null;
    const containerSelectors = [
      '#root',
      'main',
      '[class*="room-content"]',
      '[data-testid="room-page"]',
      '.room-page',
      '#__next',
      'body'
    ];
    
    for (const selector of containerSelectors) {
      mainContent = document.querySelector(selector);
      if (mainContent) {
        console.log(`[TryHackMe Scraper] Contenedor encontrado con: ${selector}`);
        break;
      }
    }
    
    if (!mainContent) {
      console.log('[TryHackMe Scraper] No se encontró contenedor, usando document.body');
      mainContent = document.body;
    }
    
    // Estrategia 1: Buscar botones específicos de TryHackMe
    // Según el HTML que viste, los headers son: <button id="header-X" data-testid="header-X">
    const headerSelectors = [
      'button[id^="header-"]',
      'button[data-testid^="header-"]',
      'button[data-task-no]',
      'h3 button[aria-expanded]',
      '[class*="accordion"] button'
    ];
    
    for (const selector of headerSelectors) {
      const buttons = mainContent.querySelectorAll(selector);
      console.log(`[TryHackMe Scraper] Selector "${selector}" encontró: ${buttons.length} botones`);
      
      if (buttons.length > 0) {
        // Filtrar solo botones que parecen ser tareas reales (no sidebar)
        buttons.forEach(btn => {
          const text = btn.textContent.trim();
          // Verificar que sea una tarea real (contiene "Tarea X" o "Task X")
          if (/Tarea\s+\d+|Task\s+\d+/i.test(text)) {
            // Verificar que no esté en el sidebar (posición)
            const rect = btn.getBoundingClientRect();
            const isSidebar = rect.left < 100 && rect.width < 200;
            if (!isSidebar) {
              taskElements.push(btn);
            }
          }
        });
        
        if (taskElements.length > 0) {
          console.log(`[TryHackMe Scraper] Botones de tarea válidos: ${taskElements.length}`);
          break;
        }
      }
    }
    
    // Si aún no hay elementos, buscar por texto de forma más amplia
    if (taskElements.length === 0) {
      console.log('[TryHackMe Scraper] Buscando por texto...');
      const allButtons = mainContent.querySelectorAll('button, [role="button"], h3, h2');
      
      allButtons.forEach(el => {
        const text = el.textContent.trim();
        // Buscar patrones como "Tarea 1", "Task 1", etc.
        if (/^(Tarea|Task)\s*\d+/i.test(text)) {
          const rect = el.getBoundingClientRect();
          // Excluir sidebar (elementos muy a la izquierda)
          if (rect.left > 100 || rect.width > 300) {
            taskElements.push(el);
          }
        }
      });
    }
    
    console.log(`[TryHackMe Scraper] Total tareas encontradas: ${taskElements.length}`);
    
    // Ordenar por posición en la página (de arriba a abajo)
    return taskElements.sort((a, b) => {
      const rectA = a.getBoundingClientRect();
      const rectB = b.getBoundingClientRect();
      return rectA.top - rectB.top;
    });
  }
  
  async function extractTaskContent(headerElement, index) {
    const taskData = {
      index: index,
      title: '',
      content: '',
      html: '',
      commands: [],
      code_blocks: [],
      links: []
    };
    
    try {
      let title = headerElement.textContent.trim();
      title = title.replace(/^Task\s+\d+[:\-\s]*/i, '').replace(/^\d+\.\s*/, '');
      taskData.title = title || `Task ${index + 1}`;
      
      const isExpanded = isTaskExpanded(headerElement);
      
      if (!isExpanded) {
        headerElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        await sleep(800);
        
        try {
          headerElement.click();
        } catch (e) {
          const clickEvent = new MouseEvent('click', {
            bubbles: true,
            cancelable: true,
            view: window
          });
          headerElement.dispatchEvent(clickEvent);
        }
        
        await sleep(2000);
      }
      
      const contentContainer = findTaskContent(headerElement);
      
      if (contentContainer) {
        taskData.content = contentContainer.innerText.trim();
        taskData.html = contentContainer.innerHTML;
        
        const codeBlocks = contentContainer.querySelectorAll('code, pre');
        codeBlocks.forEach(block => {
          const text = block.textContent.trim();
          if (text.length > 0 && !taskData.code_blocks.includes(text)) {
            taskData.code_blocks.push(text);
            if (text.match(/^[\$#>]\s+/)) {
              taskData.commands.push(text);
            }
          }
        });
        
        const links = contentContainer.querySelectorAll('a[href]');
        links.forEach(link => {
          if (link.href && !link.href.startsWith('javascript:')) {
            taskData.links.push({
              text: link.textContent.trim(),
              href: link.href
            });
          }
        });
      } else {
        taskData.content = extractFallbackContent(headerElement);
      }
      
      if (taskData.content.length > 20000) {
        taskData.content = taskData.content.substring(0, 20000) + '\n\n[...]';
      }
      
    } catch (error) {
      console.error(`[TryHackMe Scraper] Error:`, error);
      taskData.error = error.message;
    }
    
    return taskData;
  }
  
  function isTaskExpanded(headerElement) {
    const ariaExpanded = headerElement.getAttribute('aria-expanded');
    if (ariaExpanded === 'true') return true;
    
    const className = headerElement.className || '';
    if (className.includes('expanded') || className.includes('open')) return true;
    
    return false;
  }
  
  function findTaskContent(headerElement) {
    // Buscar por el data-testid correspondiente (content-X)
    const headerId = headerElement.getAttribute('data-testid');
    if (headerId && headerId.startsWith('header-')) {
      const taskNum = headerId.replace('header-', '');
      const contentSelector = `[data-testid="content-${taskNum}"]`;
      const content = document.querySelector(contentSelector);
      if (content && content.textContent.trim().length > 50) {
        return content;
      }
    }
    
    // Buscar por aria-controls
    const ariaControls = headerElement.getAttribute('aria-controls');
    if (ariaControls) {
      const content = document.getElementById(ariaControls);
      if (content && content.textContent.trim().length > 50) {
        return content;
      }
    }
    
    // Buscar hermano siguiente inmediato
    let sibling = headerElement.nextElementSibling;
    for (let i = 0; i < 3 && sibling; i++) {
      if (sibling.textContent.trim().length > 100) {
        return sibling;
      }
      sibling = sibling.nextElementSibling;
    }
    
    // Buscar en el contenedor padre
    const parent = headerElement.closest('[class*="accordion"], [class*="task"]');
    if (parent) {
      const content = parent.querySelector('[role="region"], [class*="content"]');
      if (content && content.textContent.trim().length > 50) {
        return content;
      }
    }
    
    return null;
  }
  
  function extractFallbackContent(headerElement) {
    const headerRect = headerElement.getBoundingClientRect();
    const elements = document.querySelectorAll('p, div');
    let content = '';
    let count = 0;
    
    for (const el of elements) {
      const rect = el.getBoundingClientRect();
      const text = el.textContent.trim();
      
      if (rect.top > headerRect.bottom && text.length > 30) {
        content += text + '\n\n';
        count++;
        if (count > 50 || content.length > 15000) break;
      }
    }
    
    return content.trim();
  }
  
  function extractRoomName() {
    const url = window.location.href;
    const match = url.match(/\/room\/([^\/\?]+)/);
    if (match) return match[1];
    
    const title = document.querySelector('h1');
    if (title) return title.textContent.trim().replace(/\s+/g, '-').toLowerCase();
    
    return 'unknown-room';
  }
  
  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  console.log('[TryHackMe Scraper] Script cargado. En room:', isRoomPage());
})();
