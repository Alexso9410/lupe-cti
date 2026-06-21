// popup.js - Controla la interfaz del popup de la extensión

let extractedData = null;

document.getElementById('extractBtn').addEventListener('click', async () => {
  const status = document.getElementById('status');
  const progress = document.getElementById('progress');
  const progressFill = document.getElementById('progressFill');
  const progressText = document.getElementById('progressText');
  const result = document.getElementById('result');
  const extractBtn = document.getElementById('extractBtn');
  
  status.textContent = '⏳ Extrayendo contenido...';
  status.className = 'status';
  progress.style.display = 'block';
  extractBtn.disabled = true;
  result.style.display = 'none';
  
  try {
    // Obtener la pestaña activa
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab.url.includes('tryhackme.com/room/') && !tab.url.includes('tryhackme.com/module/')) {
      status.innerHTML = '<span class="error">❌ No estás en una room de TryHackMe</span>';
      extractBtn.disabled = false;
      progress.style.display = 'none';
      return;
    }
    
    // Enviar mensaje al content script
    chrome.tabs.sendMessage(tab.id, { action: 'extract' }, (response) => {
      if (chrome.runtime.lastError) {
        status.innerHTML = `<span class="error">❌ Error: ${chrome.runtime.lastError.message}</span>`;
        extractBtn.disabled = false;
        progress.style.display = 'none';
        return;
      }
      
      if (response && response.success) {
        extractedData = response.data;
        
        progressFill.style.width = '100%';
        progressText.textContent = `${response.data.tasks.length} tareas extraídas`;
        
        status.innerHTML = `<span class="success">✅ Extracción completada</span>`;
        
        result.innerHTML = `
          <strong>Room:</strong> ${response.data.room_name}<br>
          <strong>Tareas:</strong> ${response.data.tasks.length}<br>
          <strong>Contenido:</strong> ${response.data.total_content_length} caracteres
        `;
        result.style.display = 'block';
        
        // Mostrar botón de descarga
        document.getElementById('downloadBtn').style.display = 'block';
      } else {
        status.innerHTML = `<span class="error">❌ ${response?.error || 'Error desconocido'}</span>`;
        extractBtn.disabled = false;
      }
    });
    
    // Escuchar actualizaciones de progreso
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (message.action === 'progress') {
        const percent = (message.current / message.total) * 100;
        progressFill.style.width = percent + '%';
        progressText.textContent = `Tarea ${message.current} de ${message.total}: ${message.task_name || '...'}`;
      }
      return true;
    });
    
  } catch (error) {
    status.innerHTML = `<span class="error">❌ Error: ${error.message}</span>`;
    extractBtn.disabled = false;
    progress.style.display = 'none';
  }
});

document.getElementById('downloadBtn').addEventListener('click', () => {
  if (!extractedData) return;
  
  const blob = new Blob([JSON.stringify(extractedData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  chrome.downloads.download({
    url: url,
    filename: `tryhackme_${extractedData.room_name}_${new Date().toISOString().slice(0,10).replace(/-/g,'')}.json`,
    saveAs: true
  });
});

// Verificar si estamos en una página válida al cargar
chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  const status = document.getElementById('status');
  
  if (!tab) {
    status.innerHTML = '<span class="error">❌ No se puede acceder a la pestaña</span>';
    document.getElementById('extractBtn').disabled = true;
    return;
  }
  
  if (tab.url.includes('tryhackme.com/room/') || tab.url.includes('tryhackme.com/module/')) {
    const roomName = tab.url.split('/').pop().split('?')[0];
    status.innerHTML = `✅ Detectada room: <strong>${roomName}</strong>`;
  } else {
    status.innerHTML = '⚠️ Ve a una room de TryHackMe para usar esta extensión';
    document.getElementById('extractBtn').disabled = true;
  }
});
