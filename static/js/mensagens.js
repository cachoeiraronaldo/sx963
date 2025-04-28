document.addEventListener('DOMContentLoaded', () => {
    const dataElement = document.getElementById('data');
    const criador_id = dataElement.dataset.criadorId;
    const user_id = dataElement.dataset.userId;
    let usuario_selecionado = null;

    // Configuração do Socket.IO
    const socket = io({
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        transports: ['websocket']
    });

    // Entra na sala do usuário
    socket.emit('join', { user_id: user_id });

        // ESCUTE AQUI - ADICIONE ESTE NOVO LISTENER
    socket.on('update_unread_count', (data) => {
        // Se o destinatário da mensagem for o usuário atual
        if (data.destinatario_id == user_id) {
            // Atualiza a lista de conversas
            carregarConversas();
        }
    });

    // Escuta por novas mensagens
    socket.on('new_message', (data) => {
        // Verifica se a mensagem é relevante para esta conversa
        if ((data.destinatario_id == user_id && data.remetente_id == usuario_selecionado) || 
            (data.remetente_id == user_id && data.destinatario_id == usuario_selecionado)) {
            
            const container = document.getElementById('mensagens-usuario');
            const el = document.createElement('div');
            el.className = data.remetente_id == user_id ? 'mensagem-enviada' : 'mensagem-recebida';
            el.innerHTML = `<strong>${data.remetente}</strong>: ${data.mensagem} <em>(${new Date(data.data_envio).toLocaleString()})</em>`;
            container.appendChild(el);
            container.scrollTop = container.scrollHeight;

                    // Marca como lida se for uma mensagem recebida e conversa está aberta
            if (data.destinatario_id == user_id) {
                fetch(`/marcar_mensagens_como_lidas/${data.remetente_id}`, { method: 'POST' });
            }

            // Atualiza contador de não lidas se necessário
            if (data.destinatario_id == user_id) {
                carregarConversas();
            }
        }
    });

    function carregarConversas() {
        fetch(`/conversas?criador_id=${criador_id}&conversa_aberta_id=${usuario_selecionado || ''}`)
        .then(r => r.json())
        .then(data => {
                const lista = document.getElementById('lista-conversas');
                const noMsg = document.getElementById('no-conversations');
                const currentSelected = usuario_selecionado; // Guarda o usuário selecionado atual
                lista.innerHTML = '';
                noMsg.style.display = data.conversas.length ? 'none' : 'block';
    
                data.conversas.forEach(c => {
                    const li = document.createElement('li');
                    li.textContent = c.nome_usuario;
                    if (c.nao_lidas > 0) {
                        const badge = document.createElement('span');
                        badge.className = 'badge';
                        badge.textContent = c.nao_lidas;
                        li.appendChild(badge);
                    }
                    li.addEventListener('click', () => {
                        usuario_selecionado = (usuario_selecionado === c.id) ? null : c.id;
                        document.getElementById('mensagens-usuario').innerHTML = '';
                        if (usuario_selecionado) {
                            // Armazena o ID da conversa aberta
                            localStorage.setItem('conversaAbertaId', c.id);
                            carregarMensagensUsuario(c.id);
                            fetch(`/marcar_mensagens_como_lidas/${c.id}`, { method: 'POST' })
                                .then(() => carregarConversas());
                        } else {
                            // Remove o ID da conversa aberta se fechou a conversa
                            localStorage.removeItem('conversaAbertaId');
                        }
                    });
                    
                    // Mantém o usuário selecionado após atualização
                    if (c.id === currentSelected) {
                        li.classList.add('selected');
                    }
                    
                    lista.appendChild(li);
                });
            });
    }

    function carregarMensagensUsuario(id) {
        fetch(`/mensagens_usuario/${id}?criador_id=${criador_id}`)
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('mensagens-usuario');
                container.innerHTML = '';
                data.mensagens.forEach(msg => {
                    const el = document.createElement('div');
                    el.className = msg.remetente_id === user_id ? 'mensagem-enviada' : 'mensagem-recebida';
                    el.innerHTML = `<strong>${msg.remetente}</strong>: ${msg.mensagem} <em>(${new Date(msg.data_envio).toLocaleString()})</em>`;
                    container.appendChild(el);
                });
                atualizarMensagensNaoLidas();
            });
    }

    function atualizarMensagensNaoLidas() {
        fetch('/contar_mensagens_nao_lidas')
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const badge = document.querySelector(`#lista-conversas li[data-user-id="${usuario_selecionado}"] .badge`);
                    if (badge) badge.textContent = data.count;
                }
            });
    }

    setInterval(atualizarMensagensNaoLidas, 5000);

    document.getElementById('apagar-todas-mensagens-btn').addEventListener('click', () => {
        if (!usuario_selecionado) return alert("Selecione uma conversa.");
        if (!confirm("Apagar todas as mensagens?")) return;
        fetch(`/apagar_todas_mensagens/${usuario_selecionado}`, { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                alert(data.message || data.error);
                carregarMensagensUsuario(usuario_selecionado);
            });
    });

    document.getElementById('enviar-mensagem-btn').addEventListener('click', () => {
        const msg = document.getElementById('mensagem-texto').value.trim();
        if (!msg) return alert("Digite uma mensagem.");
        if (!usuario_selecionado && user_id !== criador_id) {
            usuario_selecionado = criador_id;
            carregarConversas();
        }
    
        // Emite via socket
        socket.emit('message', { 
            remetente_id: user_id, 
            destinatario_id: usuario_selecionado, 
            mensagem: msg 
        });
    
        // Limpa campo
        document.getElementById('mensagem-texto').value = '';
    });
    
    socket.on('message', data => {
        if (data.destinatario_id === user_id || data.remetente_id === usuario_selecionado) {
            const container = document.getElementById('mensagens-usuario');
            const el = document.createElement('div');
            el.className = data.remetente_id === user_id ? 'mensagem-enviada' : 'mensagem-recebida';
            el.innerHTML = `<strong>${data.remetente}</strong>: ${data.mensagem} <em>(${new Date(data.data_envio).toLocaleString()})</em>`;
            container.appendChild(el);
            container.scrollTop = container.scrollHeight;
        }
    });

    carregarConversas();

    window.addEventListener('beforeunload', function() {
        localStorage.removeItem('conversaAbertaId');
    });
});
