document.addEventListener('DOMContentLoaded', function() {
    // Configurações iniciais
    const body = document.body;
    const themeColor = body.getAttribute('data-theme-color');
    const coverPhoto = body.getAttribute('data-cover-photo');
    const username = body.getAttribute('data-username');
    const isOwner = body.getAttribute('data-is-owner') === 'true';

    // Aplica o tema
    document.documentElement.style.setProperty('--theme-color', themeColor);
    document.documentElement.style.setProperty('--cover-photo', `url('${coverPhoto}')`);

    // Socket.IO para atualização de status de live
    const socket = io();
    socket.on('live_status_update', (data) => {
        const liveStatusElement = document.getElementById('live-status');
        if (liveStatusElement && data.username === username) {
            liveStatusElement.innerText = data.is_live ? "Ao vivo!" : "Offline";
        }
    });

    // Botão de voltar
    document.querySelector('.back-btn').addEventListener('click', function(e) {
        e.preventDefault();
        const referrer = sessionStorage.getItem('referrer-from-subscriptions');
        if (referrer) {
            window.location.href = referrer;
            sessionStorage.removeItem('referrer-from-subscriptions');
        } else {
            window.location.href = "/";
        }
    });

    // Botão de like
    document.getElementById('like-btn').addEventListener('click', function() {
        fetch(`/toggle_like/${username}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showFlashMessage(data.error, 'error');
                } else {
                    document.getElementById('like-count').innerText = data.total_likes;
                    showFlashMessage(data.message, 'success');
                }
            })
            .catch(error => console.error('Erro ao curtir:', error));
    });

    // Botão de seguir/seguidores
    const followButton = isOwner ? document.getElementById('followers-btn') : document.getElementById('follow-btn');
    followButton.addEventListener('click', function() {
        if (isOwner) {
            window.location.href = `/seguidores/${username}`;
        } else {
            fetch(`/seguir/${username}`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        showFlashMessage(data.error, 'error');
                    } else {
                        const countElement = document.getElementById('follow-count');
                        let currentCount = parseInt(countElement.innerText) || 0;
                        countElement.innerText = data.following ? currentCount + 1 : Math.max(0, currentCount - 1);
                        showFlashMessage(data.message, 'success');
                    }
                })
                .catch(error => console.error('Erro ao seguir:', error));
        }
    });

    // Botão de mensagens
    document.getElementById('message-btn').addEventListener('click', function() {
        window.location.href = `/mensagens/${username}`;
    });

    // Botão de live
    document.getElementById('live-btn').addEventListener('click', function() {
        fetch(`/check_live_status/${username}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                if (data.is_live || data.is_owner) {
                    window.location.href = `/live/${username}`;
                } else {
                    showFlashMessage(data.message || "🔴 Live offline", "error");
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                showFlashMessage(error.message, "error");
            });
    });

    // Galeria de mídia
    document.querySelectorAll('.expandable-image').forEach(img => {
        img.addEventListener('click', function() {
            const expandedImg = document.getElementById('expanded-image');
            expandedImg.src = this.src;
            document.getElementById('expanded-image-container').style.display = 'flex';
        });
    });

    document.getElementById('expanded-image-container').addEventListener('click', function() {
        this.style.display = 'none';
    });

    // Atualização periódica de mensagens não lidas
    function updateUnreadMessages() {
        // Pega o ID da conversa aberta do localStorage (se existir)
        const conversaAbertaId = localStorage.getItem('conversaAbertaId') || '';
        
        fetch(`/contar_mensagens_nao_lidas?conversa_aberta_id=${conversaAbertaId}`)
            .then(response => response.json())
            .then(data => {
                if (!data.error) {
                    document.getElementById('unread-messages').innerText = data.count;
                }
            })
            .catch(console.error);
    }
    
    // Executa imediatamente e a cada 5 segundos
    updateUnreadMessages();
    setInterval(updateUnreadMessages, 5000);

    // Função auxiliar para mostrar mensagens flash
    function showFlashMessage(message, category) {
        let container = document.getElementById('flash-messages');
        if (!container) {
            container = document.createElement('div');
            container.id = 'flash-messages';
            document.body.prepend(container);
        }

        const messageElement = document.createElement('div');
        messageElement.className = `flash-message ${category}`;
        messageElement.textContent = message;
        container.appendChild(messageElement);

        setTimeout(() => messageElement.remove(), 3000);
    }

    // Confirmação para exclusão de mídia
    document.querySelectorAll('.delete-media-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (!confirm('Tem certeza que deseja excluir esta mídia?')) {
                e.preventDefault();
            }
        });
    });
});

// Função de particiapantes

document.addEventListener('DOMContentLoaded', function() {
    // Seletores corrigidos para seu HTML real
    const tooltips = document.querySelectorAll('.participants-badge, .pessoas-midia-tooltip');
    
    tooltips.forEach(tooltip => {
        // Encontra o conteúdo do tooltip de forma flexível
        const content = tooltip.querySelector('.participants-tooltip, .pessoas-tooltip-content');
        
        // Desktop - hover
        tooltip.addEventListener('mouseenter', function() {
            if (window.innerWidth > 768 && content) {
                content.style.display = 'block';
                
                // Verifica se o tooltip está saindo da tela (apenas para desktop)
                const rect = content.getBoundingClientRect();
                if (rect.right > window.innerWidth) {
                    content.style.right = 'auto';
                    content.style.left = '0';
                }
            }
        });
        
        tooltip.addEventListener('mouseleave', function() {
            if (window.innerWidth > 768 && content) {
                content.style.display = 'none';
                // Reseta a posição
                content.style.right = '';
                content.style.left = '';
            }
        });
        
        // Mobile - touch
        tooltip.addEventListener('click', function(e) {
            if (window.innerWidth <= 768 && content) {
                e.stopPropagation();
                content.style.display = content.style.display === 'block' ? 'none' : 'block';
            }
        });
    });
    
    // Fechar tooltips ao clicar fora (mobile)
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768 && 
            !e.target.closest('.participants-badge') && 
            !e.target.closest('.pessoas-midia-tooltip')) {
            
            document.querySelectorAll('.participants-tooltip, .pessoas-tooltip-content').forEach(content => {
                content.style.display = 'none';
            });
        }
    });
});