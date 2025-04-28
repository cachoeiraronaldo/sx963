const socket = io(); // já deve estar inicializado

socket.on("novo_usuario_admin", (usuario) => {
    const container = document.getElementById("user-list-container");
    if (!container) return;

    const card = document.createElement("div");
    card.classList.add("user-card");
    card.innerHTML = `
        <div class="user-info">               
            <strong>Nome de Usuário:</strong> ${usuario.nome_usuario}<br>
            <strong>CPF:</strong> ${usuario.cpf || 'Não informado'}<br>
            <strong>ID:</strong> ${usuario.id}<br>
            <h4>Faturamento do Mês Atual</h4>
            <strong>Assinantes:</strong> 0<br>
            <strong>Faturamento por Assinaturas:</strong> R$ 0.00<br>
            <strong>Vídeos Vendidos:</strong> 0<br>
            <strong>Faturamento por Vídeos:</strong> R$ 0.00<br>
            <strong>Faturamento Total:</strong> R$ 0.00<br>
            <strong>Saldo Líquido (75%):</strong> R$ 0.00<br>
            <span class="user-status badge badge-warning">Pendente</span>
        </div>
        <div class="user-documents">
            <strong>Documentos:</strong><br>
            <div>
                ${usuario.documento_frente_url ? 
                    `<a href="${usuario.documento_frente_url}" target="_blank">Ver Documento Frente</a>` 
                    : 'Documento Frente não disponível'}
            </div>
            <div>
                ${usuario.documento_verso_url ? 
                    `<a href="${usuario.documento_verso_url}" target="_blank">Ver Documento Verso</a>` 
                    : 'Documento Verso não disponível'}
            </div>
            <div>
                ${usuario.documento_rosto_url ? 
                    `<a href="${usuario.documento_rosto_url}" target="_blank">Ver Documento com Rosto</a>` 
                    : 'Documento com Rosto não disponível'}
            </div>
        </div>
        <div class="actions">
            <button class="btn btn-success btn-aprovar-criador" data-user-id="${usuario.id}">
                Liberar
            </button>
            <button class="btn btn-danger btn-excluir-criador" data-user-id="${usuario.id}">
                Excluir
            </button>
        </div>
    `;
    container.appendChild(card);

    // ✅ Flash message com sucesso
    if (usuario.mensagem) {
        const flashItem = document.createElement("div");
        flashItem.classList.add("flash-message", "success");
        flashItem.textContent = usuario.mensagem;
        document.body.appendChild(flashItem);
        setTimeout(() => flashItem.remove(), 12000);
    }
});

socket.on("nova_midia_admin", (data) => {
    const { usuario_id, midia, mensagem } = data;
    const container = document.getElementById(`media-container-${usuario_id}`);
    if (!container) return;

    const card = document.createElement("div");
    card.classList.add("video-card1");
    card.setAttribute("data-id", midia.id);

    // Cria o HTML para os participantes
    let participantesHTML = '';
    if (midia.participantes && midia.participantes.length > 0) {
        participantesHTML = `
            <strong>Participantes:</strong>
            <div class="pessoas-midia-container">
                ${midia.participantes.map(pessoa => 
                    `<span class="pessoa-midia-tag" title="${pessoa}">${pessoa}</span>`
                ).join('')}
            </div>
        `;
    }

    // Gera o bloco de mídia de acordo com a categoria
    let midiaHTML = '';
    if (midia.categoria === "trailer") {
        midiaHTML = `
            <strong>Título:</strong> ${midia.descricao || 'Sem título'}<br>
            ${participantesHTML}
            <video width="320" height="240" controls>
                <source src="${midia.url}" type="video/mp4">
            </video>
        `;
    } else {
        midiaHTML = `
            <strong>Nome do Arquivo:</strong> ${midia.filename}<br>
            <strong>Categoria:</strong> ${midia.categoria}<br>
            <strong>Descrição:</strong> ${midia.descricao || 'Sem descrição'}<br>
            ${participantesHTML}
            ${midia.type === 'image' ?
                `<img src="${midia.url}" width="320" height="240">` :
                `<video width="320" height="240" controls>
                    <source src="${midia.url}" type="video/mp4">
                </video>`}
        `;
    }

    // Junta tudo no card
    card.innerHTML = `
        ${midiaHTML}
        <span class="badge badge-warning">pendente</span>
        <div class="media-message">Sem mensagem associada.</div>
        <div class="actions">
            <button class="btn btn-success btn-approve" data-id="${midia.id}">Aprovar</button>
            <button class="btn btn-warning btn-block" data-id="${midia.id}">Bloquear</button>
            <button class="btn btn-danger btn-delete" data-id="${midia.id}">Excluir</button>
        </div>
    `;
    container.appendChild(card);

    // Feedback visual
    if (mensagem) {
        const flashItem = document.createElement("div");
        flashItem.classList.add("flash-message", "success");
        flashItem.textContent = mensagem;
        document.body.appendChild(flashItem);
        setTimeout(() => flashItem.remove(), 12000);
    }
});


// Intercepta ações de botões administrativos

document.addEventListener("click", async (e) => {
    if (e.target.matches(".btn-approve, .btn-block, .btn-delete")) {
        e.preventDefault();
        const btn = e.target;
        const mediaId = btn.dataset.id;
        let url = "";

        if (btn.classList.contains("btn-approve")) {
            url = `/admin/aprovar_media/${mediaId}`;
        } else if (btn.classList.contains("btn-block")) {
            url = `/admin/block_media/${mediaId}`;
        } else if (btn.classList.contains("btn-delete")) {
            if (!confirm("Tem certeza que deseja excluir esta mídia?")) return;
            url = `/admin/delete_media/${mediaId}`;
        }

        try {
            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });

            const result = await res.json();

            if (result.success) {
                const card = btn.closest(".video-card1");
                if (btn.classList.contains("btn-delete")) {
                    card.remove();
                } else if (btn.classList.contains("btn-block")) {
                    const badge = card.querySelector(".badge");
                    const isBlocked = result.status === "bloqueado";
                    badge.className = `badge ${isBlocked ? "badge-danger" : "badge-success"}`;
                    badge.textContent = isBlocked ? "bloqueado" : "disponivel";
                    btn.textContent = isBlocked ? "Desbloquear" : "Bloquear";
                } else if (btn.classList.contains("btn-approve")) {
                    const badge = card.querySelector(".badge");
                    badge.textContent = "disponivel";
                    badge.className = "badge badge-success";
                    btn.remove();
                }

                const flash = document.createElement("div");
                flash.className = "flash-message success";
                flash.textContent = "✅ Operação realizada com sucesso!";
                document.body.appendChild(flash);
                setTimeout(() => flash.remove(), 6000);
            } else {
                alert(result.error || "Erro na operação");
            }
        } catch (err) {
            console.error(err);
            alert("Erro ao executar ação.");
        }
    }
});

// Manipulação de eventos para os botões de usuário
document.addEventListener("click", async (e) => {
    // Liberar usuário
    if (e.target.classList.contains("btn-aprovar-criador")) {
        e.preventDefault();
        const btn = e.target;
        const userId = btn.dataset.userId;
        
        try {
            const res = await fetch(`/admin/liberar_usuario/${userId}`, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });

            const result = await res.json();

                // No trecho onde você lida com btn-aprovar-criador
            if (result.success) {
                const card = btn.closest(".user-card");
                
                // Opção 1: Apenas desativar os botões e marcar como verificado
                card.querySelectorAll(".btn").forEach(btn => {
                    btn.disabled = true;
                });
                card.style.opacity = "0.7";
                card.style.borderLeft = "4px solid #28a745"; // Borda verde para indicar verificado
                
                // Opção 2: Atualizar o status no card (se tiver um campo visível)
                const statusElement = card.querySelector(".user-status") || document.createElement("span");
                statusElement.textContent = "Verificado";
                statusElement.className = "badge badge-success";
                card.querySelector(".user-info").appendChild(statusElement);
                
                // Mostra mensagem de sucesso
                const flash = document.createElement("div");
                flash.className = "flash-message success";
                flash.textContent = result.message || `✅ Usuário ${usuario.nome_usuario} liberado com sucesso!`;
                document.body.appendChild(flash);
                setTimeout(() => flash.remove(), 6000);

                } else {
                    alert(result.error || "Erro ao liberar usuário");
                }
            } catch (err) {
                console.error(err);
                alert("Erro ao executar ação.");
            }
        }
        
    // Excluir usuário
    if (e.target.classList.contains("btn-excluir-criador")) {
        e.preventDefault();
        if (!confirm("Tem certeza que deseja excluir este usuário?")) return;
        
        const btn = e.target;
        const userId = btn.dataset.userId;
        
        try {
            const res = await fetch(`/admin/excluir_usuario/${userId}`, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });

            const result = await res.json();

            if (result.success) {
                // Remove o card do usuário
                const card = btn.closest(".user-card");
                card.remove();
                
                // Mostra mensagem de sucesso
                const flash = document.createElement("div");
                flash.className = "flash-message success";
                flash.textContent = result.message || "✅ Usuário excluído com sucesso!";
                document.body.appendChild(flash);
                setTimeout(() => flash.remove(), 6000);
            } else {
                alert(result.error || "Erro ao excluir usuário");
            }
        } catch (err) {
            console.error(err);
            alert("Erro ao executar ação.");
        }
    }
});

