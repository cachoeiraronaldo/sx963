// Configuração do Socket.IO - DEVE VIR PRIMEIRO
const socket = io('https://www.sx69.com.br', {
  path: '/socket.io',
  secure: true,
  transports: ['websocket']
});

// Configurações globais
const isOwner = document.body.dataset.isOwner === 'true';
const username = document.body.dataset.username;
const creatorUsername = document.body.dataset.creatorUsername;
let room = null;
let localStream = null;

// Elementos DOM
const mainVideo = document.getElementById('mainVideo');
const startLiveBtn = isOwner ? document.getElementById('startLiveBtn') : null;
const stopLiveBtn = isOwner ? document.getElementById('stopLiveBtn') : null;
const watchLiveBtn = !isOwner ? document.getElementById('watchLiveBtn') : null;
const statusElement = document.getElementById('status');
const connectionQualityElement = document.getElementById('connectionQuality');

// Funções auxiliares
function showError(message) {
  console.error('Erro:', message);
  statusElement.textContent = `Erro: ${message}`;
  statusElement.style.color = 'red';
  
  if (startLiveBtn) startLiveBtn.disabled = false;
  if (stopLiveBtn) stopLiveBtn.disabled = true;
  if (watchLiveBtn) watchLiveBtn.disabled = false;
}

function updateStatus(message) {
  if (!message || message.trim() === '') {
    statusElement.classList.add('hidden');
    statusElement.textContent = '';
  } else {
    statusElement.classList.remove('hidden');
    console.log('Status:', message);
    statusElement.textContent = message;
    statusElement.style.color = 'inherit';
  }
}

function updateConnectionQuality(quality) {
  let qualityText, qualityClass, iconClass;
  
  if (quality === undefined || quality === null) {
      qualityText = 'desconhecida';
      qualityClass = 'unknown';
      iconClass = 'fas fa-question-circle';
  } else if (typeof quality === 'number') {
      if (quality >= 0.8) {
          qualityText = 'excelente';
          qualityClass = 'excellent';
          iconClass = 'fas fa-check-circle';
      } else if (quality >= 0.5) {
          qualityText = 'boa';
          qualityClass = 'good';
          iconClass = 'fas fa-check-circle';
      } else if (quality >= 0.3) {
          qualityText = 'fraca';
          qualityClass = 'poor';
          iconClass = 'fas fa-exclamation-circle';
      } else {
          qualityText = 'insuficiente';
          qualityClass = 'failed';
          iconClass = 'fas fa-times-circle';
      }
  } else {
      qualityText = String(quality).toLowerCase();
      qualityClass = qualityText;
      iconClass = 'fas fa-question-circle';
  }

  const connectionStatus = document.getElementById('connectionStatus');
  connectionStatus.className = 'connection-quality quality-' + qualityClass;
  
  connectionStatus.innerHTML = `
      <i class="${iconClass}"></i>
      <span>Qualidade da conexão: <strong>${qualityText}</strong></span>
  `;
}

async function setupRoom() {
  try {
      updateStatus('Obtendo token de acesso...');
      
      const response = await fetch(`/get_token/${username}?is_owner=${isOwner}&creator=${creatorUsername}`);
      if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || 'Falha ao obter token');
      }
      const { token, ws_url } = await response.json();
      
      const roomObj = new LivekitClient.Room({
          adaptiveStream: true,
          dynacast: true,
          trackSubscriptionDefaults: {
              autoSubscribe: true,
              maxQuality: 'high'
          }
      });

      roomObj.on('connectionQualityChanged', (quality) => {
          console.log('Qualidade da conexão:', quality);
          updateConnectionQuality(quality);
      });

      roomObj.on('signalConnected', () => {
          console.log('Conexão de sinalização estabelecida');
          updateStatus('Conectado à sala!');
      });

      roomObj.on('iceConnectionStateChanged', state => {
          console.log('Estado ICE:', state);
      });

      roomObj.on('mediaDevicesChanged', () => {
          console.log('Dispositivos de mídia alterados');
      });

      roomObj.on('participantConnected', participant => {
          console.log(`Participante conectado: ${participant.identity}`);
          if (participant.identity === creatorUsername) {
              participant.tracks.forEach(pub => {
                  if (!pub.isSubscribed) pub.setSubscribed(true);
              });
          }
      });

      roomObj.on('trackPublished', publication => {
          console.log(`Track publicada pelo participante ${publication.participant.identity}`);
          if (publication.participant.identity === creatorUsername) {
              console.log(`Track do criador publicada, inscrevendo...`);
              publication.setSubscribed(true);
          }
      });

      roomObj.on('trackSubscribed', (track, publication, participant) => {
          console.log(`✅ Track ${track.kind} inscrita de ${participant.identity}`);
          if (participant.identity === creatorUsername) {
              if (!mainVideo.srcObject) {
                  mainVideo.srcObject = new MediaStream();
              }
              mainVideo.srcObject.addTrack(track.mediaStreamTrack);
              mainVideo.play().catch(e => console.error('Play error:', e));
              updateStatus('Assistindo a live');
          }
      });

      console.log('Tentando conectar à sala com ws_url:', ws_url);
      await roomObj.connect(ws_url, token, {
          autoSubscribe: true,
          maxRetries: 3,
          iceServers: [
              { urls: 'stun:stun.l.google.com:19302' },
              { urls: 'stun:global.stun.twilio.com:3478' }
          ]
      });

      if (roomObj && roomObj.participants) {
          roomObj.participants.forEach(participant => {
              if (participant.identity === creatorUsername) {
                  participant.tracks.forEach(pub => {
                      if (pub.track) {
                          attachTrack(pub.track, participant);
                      } else if (!pub.isSubscribed) {
                          pub.setSubscribed(true);
                      }
                  });
              }
          });
      }

      return roomObj;
  } catch (error) {
      console.error('Erro na conexão:', error);
      throw error;
  }
}

function setupRoomEventHandlers() {
  if (!room) return;

  room.on('trackSubscriptionFailed', (sid, error) => {
      console.error('Falha na inscrição:', sid, error);
  });

  room.on('iceConnectionStateChanged', state => {
      console.log('Estado ICE:', state);
  });

  room.on('signalConnected', () => {
    console.log('Conexão de sinalização estabelecida');
  });

  room.on('mediaDevicesChanged', () => {
    console.log('Dispositivos de mídia alterados');
  });

  room.on('localTrackPublished', (publication) => {
      console.log(`Track local publicada: ${publication.track.kind}`);
  });

  room.on('trackPublished', publication => {
      if (publication.participant.identity === creatorUsername) {
          console.log(`Track do criador publicada, inscrevendo...`);
          publication.setSubscribed(true);
      }
  });

  room.on('trackSubscribed', (track, publication, participant) => {
        if (participant.identity === creatorUsername) {
            console.log(`✅ Track ${track.kind} inscrita de ${participant.identity}`);
            if (!mainVideo.srcObject) {
                mainVideo.srcObject = new MediaStream();
            }
            mainVideo.srcObject.addTrack(track.mediaStreamTrack);
            mainVideo.play().catch(e => console.error('Play error:', e));
        }
    });

    room.on('trackSubscriptionFailed', (sid, error) => {
        console.error('❌ Falha na inscrição:', sid, error);
    });

    room.on('participantConnected', participant => {
        console.log(`👤 Participante conectado: ${participant.identity}`);
        if (participant.identity === creatorUsername) {
            participant.tracks.forEach(pub => {
                if (!pub.isSubscribed) {
                    pub.setSubscribed(true);
                }
            });
        }
    });
}

function attachTrack(track, participant) {
  if (participant.identity !== creatorUsername) return;

  console.log(`Anexando track ${track.kind}...`);
  
  if (!mainVideo.srcObject) {
      mainVideo.srcObject = new MediaStream();
  }

  mainVideo.srcObject.getTracks()
      .filter(t => t.kind === track.kind)
      .forEach(t => mainVideo.srcObject.removeTrack(t));

  mainVideo.srcObject.addTrack(track.mediaStreamTrack);

  if (track.kind === 'video') {
      mainVideo.load();
      mainVideo.play().catch(e => console.error('Erro ao reproduzir:', e));
  }
  
  updateStatus('Transmissão recebida!');
}

async function startBroadcasting() {
  try {
    if (!isOwner) {
      statusElement.style.display = 'none';
      room = await setupRoom();
      return;
    }

    updateStatus('Configurando transmissão...');
    room = await setupRoom();
    
    try {
      localStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280, max: 1280 },
          height: { ideal: 720, max: 720 },
          frameRate: { ideal: 30, max: 30 },
          facingMode: 'user'
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false,
          channelCount: 1
        }
      });
    } catch (error) {
      console.error('Erro ao obter mídia:', error);
      throw new Error('Permissão de câmera/microfone negada');
    }

    mainVideo.srcObject = localStream;
    mainVideo.muted = true;
    
    const videoTrack = localStream.getVideoTracks()[0];
    const audioTrack = localStream.getAudioTracks()[0];
    
    console.log('Video Track:', videoTrack ? 'OK' : 'Falha');
    console.log('Audio Track:', audioTrack ? 'OK' : 'Falha');

    try {
      await Promise.all([
        room.localParticipant.publishTrack(videoTrack, {
          simulcast: true,
          videoEncoding: {
            maxBitrate: 1_500_000,
            maxFramerate: 30
          }
        }),
        room.localParticipant.publishTrack(audioTrack, {
          dtx: false,
          red: false
        })
      ]);
      console.log('Tracks publicadas com sucesso');
    } catch (publishError) {
      console.error('Erro ao publicar tracks:', publishError);
      throw new Error('Falha ao publicar transmissão');
    }

    updateStatus('');
    
    try {
      const response = await fetch(`/start_live/${creatorUsername}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) throw new Error('Falha no servidor');
      
      socket.emit('creator_ready', { username: creatorUsername });
      console.log('Live iniciada no servidor');
    } catch (serverError) {
      console.error('Erro no servidor:', serverError);
      throw new Error('Problema ao registrar a live');
    }

  } catch (error) {
    console.error('Erro na transmissão:', error);
    
    if (localStream) {
      localStream.getTracks().forEach(t => t.stop());
      localStream = null;
    }
    if (room) {
      await room.disconnect();
      room = null;
    }
    mainVideo.srcObject = null;
    
    showError(error.message);
    if (startLiveBtn) startLiveBtn.disabled = false;
    if (stopLiveBtn) stopLiveBtn.disabled = true;
  }
}

async function stopBroadcasting() {
  try {
    updateStatus('Encerrando transmissão...');
    
    if (localStream) {
      localStream.getTracks().forEach(track => track.stop());
      localStream = null;
    }
    
    if (room) {
      await room.disconnect();
      room = null;
    }
    
    mainVideo.srcObject = null;
    
    await fetch(`/stop_live/${creatorUsername}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    updateStatus('Transmissão encerrada');
  } catch (error) {
    console.error('Erro ao encerrar transmissão:', error);
    throw error;
  }
}

// Configuração dos eventos
function setupEventListeners() {
  if (isOwner) {
    startLiveBtn.addEventListener('click', async () => {
      try {
        startLiveBtn.disabled = true;
        await startBroadcasting();
        stopLiveBtn.disabled = false;
      } catch (error) {
        showError(error.message);
        startLiveBtn.disabled = false;
      }
    });

    stopLiveBtn.addEventListener('click', async () => {
      try {
        stopLiveBtn.disabled = true;
        await stopBroadcasting();
        startLiveBtn.disabled = false;
      } catch (error) {
        showError(error.message);
        stopLiveBtn.disabled = false;
      }
    });
  } else if (watchLiveBtn) {
    watchLiveBtn.addEventListener('click', async () => {
      try {
        watchLiveBtn.disabled = true;
        await startBroadcasting();
      } catch (error) {
        showError(error.message);
        watchLiveBtn.disabled = false;
      }
    });
  }
}

// Configuração do chat
function setupChat() {
  const chatInput = document.getElementById('chatInput');
  const sendMessageBtn = document.getElementById('sendMessageBtn');
  const chatMessages = document.getElementById('chatMessages');
  
  function addMessage(sender, message, isCreator = false) {
    const messageElement = document.createElement('div');
    messageElement.className = `chat-message ${isCreator ? 'creator' : ''}`;

    // Usa textContent para evitar XSS
    if (sender === 'Sistema') {
        const sanitizedMessage = sanitizeText(message);
        messageElement.innerHTML = `<span class="system-message">${sanitizedMessage}</span>`;
    } else {
        const displaySender = (sender === username) 
            ? '<span class="sender sender-you">Você</span>' 
            : `<span class="sender">${sanitizeText(sender)}</span>`;
        const sanitizedMessage = sanitizeText(message);

        // Permite quebras de linha com <br> para mensagens longas
        messageElement.innerHTML = `${displaySender} ${sanitizedMessage.replace(/\n/g, '<br>')}`;
    }

    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Função para sanitizar texto no frontend
function sanitizeText(text) {
    if (!text) return '';
    const tempDiv = document.createElement('div');
    tempDiv.textContent = text; // Remove HTML tags automaticamente
    return tempDiv.innerHTML; // Retorna o texto seguro
}
  
  function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    if (message.length > 500) {
      alert('Mensagem muito longa (máx. 500 caracteres)');
      return;
    }

    sendMessageBtn.disabled = true;
    
    socket.emit('chat_message', {
      sender: username,
      recipient: isOwner ? null : creatorUsername,
      message: message
    });

    if (!isOwner) {
      addMessage('Você', message);
    }
    
    chatInput.value = '';
    sendMessageBtn.disabled = false;
  }
  
  sendMessageBtn.addEventListener('click', sendMessage);
  chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
  });
  
  socket.on('chat_message', (data) => {
    const isForMe = isOwner || 
                   data.sender === creatorUsername || 
                   data.recipient === username;
    
    if (isForMe) {
      addMessage(
        data.sender, 
        data.message, 
        data.sender === creatorUsername
      );
    }
  });

  socket.on('connect', () => {
    console.log('Conectado ao Socket.IO');
    
    if (!isOwner && creatorUsername) {
      socket.emit('viewer_joined', { creator_username: creatorUsername });
    }
  });

  socket.on('viewers_update', (count) => {
    console.log('Recebida atualização de espectadores:', count);
    const counterElement = document.getElementById('viewersCount');
    if (counterElement) {
      counterElement.textContent = count;
      counterElement.classList.add('counting-update');
      setTimeout(() => counterElement.classList.remove('counting-update'), 300);
    }
  });

  if (isOwner) {
    setInterval(() => {
      socket.emit('get_viewers_count', { creator_username: creatorUsername });
    }, 3000);
  }
  
  if (isOwner) {
    addMessage('Sistema', 'Bem vindo ao chat!', true);
  } else {
    addMessage('Sistema', 'Bem vindo ao chat!');
  }
}

// Inicialização
document.addEventListener('DOMContentLoaded', async () => {
  try {
    updateStatus('Verificando conexão...');
    
    if (typeof LivekitClient === 'undefined') {
      throw new Error('Cliente de vídeo não carregado');
    }

    const response = await fetch('/check_livekit_server');
    if (!response.ok) {
      throw new Error('Servidor de vídeo offline');
    }

    setupEventListeners();
    setupChat();
    
    if (isOwner) {
      startLiveBtn.disabled = false;
      updateStatus('Pronto para iniciar a live');
    } else {
      watchLiveBtn.disabled = false;
      updateStatus('Pronto para assistir');
    }
  } catch (error) {
    showError(error.message);
  }
});

// Função para tela cheia
function toggleFullscreen() {
  const videoContainer = document.querySelector('.video-container');
  
  if (!document.fullscreenElement) {
      videoContainer.requestFullscreen().catch(err => {
          console.error(`Error attempting to enable fullscreen: ${err.message}`);
      });
  } else {
      document.exitFullscreen();
  }
}

// Adicione um botão de tela cheia
document.addEventListener('DOMContentLoaded', () => {
  const videoContainer = document.querySelector('.video-container');
  const fullscreenBtn = document.createElement('button');
  fullscreenBtn.className = 'fullscreen-btn';
  fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
  fullscreenBtn.addEventListener('click', toggleFullscreen);
  videoContainer.appendChild(fullscreenBtn);
  
  // Atualize o ícone quando entrar/sair do modo tela cheia
  document.addEventListener('fullscreenchange', () => {
      if (document.fullscreenElement) {
          fullscreenBtn.innerHTML = '<i class="fas fa-compress"></i>';
      } else {
          fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
      }
  });
});