// Começo da função Menu Hambuguer

// Selecionando elementos do menu hamburguer e da sobreposição
const hamburger = document.getElementById('hamburger');
const mobileMenu = document.getElementById('mobile-menu');
const overlay = document.getElementById('overlay');
const homeSection = document.getElementById('home-section'); // Seção Home
const aboutSection = document.getElementById('about-section'); // Seção Sobre
const contactSection = document.getElementById('contact-section'); // Seção Contato

// Função para abrir/fechar o menu e a sobreposição
function toggleMenu(isOpen) {
    if (isOpen) {
        mobileMenu.classList.remove('hidden');
        mobileMenu.classList.add('open');
        overlay.classList.add('active');
        document.body.classList.add('no-scroll');
    } else {
        mobileMenu.classList.add('hidden');
        mobileMenu.classList.remove('open');
        overlay.classList.remove('active');
        document.body.classList.remove('no-scroll');
    }
}

// Função para mostrar/ocultar seções
function showSection(sectionToShow, sectionToHide) {
    sectionToShow.style.display = 'block';
    sectionToHide.style.display = 'none';
    overlay.classList.add('active'); // Ativa a sobreposição
    toggleMenu(false); // Fecha o menu
}

// Função para fechar seções e voltar para a Home
function closeSection(sectionToClose) {
    sectionToClose.style.display = 'none';
    homeSection.style.display = 'block';
    overlay.classList.remove('active'); // Remove a sobreposição
}

// Abrir o menu ao clicar no botão hamburguer
if (hamburger && mobileMenu && overlay) {
    hamburger.addEventListener('click', () => {
        toggleMenu(!mobileMenu.classList.contains('open')); // Alterna o estado do menu
    });
}

// Fechar o menu ao clicar na sobreposição
overlay.addEventListener('click', () => {
    toggleMenu(false); // Fecha o menu
    closeSection(aboutSection); // Fecha a seção "Sobre" se estiver aberta
    closeSection(contactSection); // Fecha a seção "Contato" se estiver aberta
});

// Fechar o menu ao clicar em um link do menu (opcional)
mobileMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
        toggleMenu(false); // Fecha o menu
    });
});

// Mostrar a seção "Sobre"
document.getElementById('about-link').addEventListener('click', function(event) {
    event.preventDefault(); // Impede o comportamento padrão do link
    showSection(aboutSection, homeSection); // Mostra a seção "Sobre"
});

// Mostrar a seção "Contato"
document.getElementById('contact-link').addEventListener('click', function(event) {
    event.preventDefault(); // Impede o comportamento padrão do link
    showSection(contactSection, homeSection); // Mostra a seção "Contato"
});

// Fechar manualmente a seção "Sobre"
document.getElementById('close-about-btn').addEventListener('click', function() {
    closeSection(aboutSection); // Fecha a seção "Sobre"
});

// Fechar manualmente a seção "Contato"
document.getElementById('close-contact-btn').addEventListener('click', function() {
    closeSection(contactSection); // Fecha a seção "Contato"
});

// Fim da função Menu Hambuguer

// Começo da função vídeos grátis

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.category-container').forEach((container) => {
        const leftBtn = container.querySelector('.left-btn');
        const rightBtn = container.querySelector('.right-btn');
        const videoRow = container.querySelector('.category-videos');

        if (!leftBtn || !rightBtn || !videoRow) {
            console.warn('Elementos de rolagem ausentes em um container de categoria.');
            return;
        }

        const videoCard = videoRow.querySelector('.video-card');
        if (!videoCard) {
            console.warn('Nenhum cartão de vídeo encontrado nesta categoria.');
            return;
        }

        const videoWidth = videoCard.offsetWidth + parseInt(getComputedStyle(videoRow).gap || 0);

        rightBtn.addEventListener('click', () => {
            videoRow.scrollBy({ left: videoWidth, behavior: 'smooth' });
        });

        leftBtn.addEventListener('click', () => {
            videoRow.scrollBy({ left: -videoWidth, behavior: 'smooth' });
        });

        let startX = 0;
        let scrollLeft = 0;

        videoRow.addEventListener('touchstart', (e) => {
            startX = e.touches[0].pageX - videoRow.offsetLeft;
            scrollLeft = videoRow.scrollLeft;
        });

        videoRow.addEventListener('touchmove', (e) => {
            const x = e.touches[0].pageX - videoRow.offsetLeft;
            const walk = (x - startX) * 2;
            videoRow.scrollLeft = scrollLeft - walk;
        });
    });

    document.querySelectorAll('.category-videos').forEach((videoContainer) => {
        videoContainer.addEventListener('click', (e) => {
            if (e.target.tagName === 'VIDEO') {
                const video = e.target;
                if (video.requestFullscreen) {
                    video.requestFullscreen();
                }
            }

            if (e.target.tagName === 'IMG') {
                expandOrCollapseImage(e.target);
            }
        });
    });

    function expandOrCollapseImage(image) {
        let overlay = document.querySelector('.overlay'); // Verifica se já existe um overlay
    
        if (image.classList.contains('expanded')) {
            // Voltar aos estilos originais
            const originalStyles = image.dataset.originalStyles;
            if (originalStyles) {
                const styles = JSON.parse(originalStyles);
                Object.keys(styles).forEach((key) => {
                    image.style[key] = styles[key];
                });
            }
            image.classList.remove('expanded');
    
            // Remove o overlay se existir
            if (overlay) {
                document.body.removeChild(overlay);
            }
        } else {
            // Salvar os estilos originais da imagem antes de expandi-la
            const originalStyles = {
                position: image.style.position || '',
                zIndex: image.style.zIndex || '',
                top: image.style.top || '',
                left: image.style.left || '',
                transform: image.style.transform || '',
                maxWidth: image.style.maxWidth || '',
                maxHeight: image.style.maxHeight || '',
                objectFit: image.style.objectFit || '',
                cursor: image.style.cursor || '',
            };
            image.dataset.originalStyles = JSON.stringify(originalStyles);
    
            // Expandir a imagem
            image.style.position = 'fixed';
            image.style.zIndex = '1000';
            image.style.top = '50%';
            image.style.left = '50%';
            image.style.transform = 'translate(-50%, -50%)';
            image.style.maxWidth = '95%'; // Aumenta um pouco o tamanho
            image.style.maxHeight = '95%'; // Aumenta um pouco o tamanho
            image.style.objectFit = 'contain';
            image.style.cursor = 'zoom-out';
            image.classList.add('expanded');
    
            // Cria o overlay se não existir
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.classList.add('overlay');
                overlay.style.position = 'fixed';
                overlay.style.top = '0';
                overlay.style.left = '0';
                overlay.style.width = '100%';
                overlay.style.height = '100%';
                overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
                overlay.style.zIndex = '999'; // Abaixo da imagem expandida
                overlay.style.cursor = 'zoom-out';
                document.body.appendChild(overlay);
    
                // Fecha a imagem ao clicar no overlay
                overlay.addEventListener('click', () => expandOrCollapseImage(image));
            }
        }
    }
});

// Selecionando elementos do menu de categorias
const categoriesLink = document.getElementById('categories-link');
const categoriesMenuMobile = document.querySelector('.dropdown'); // Seleciona o menu de categorias

// Adicionando o evento de clique para mostrar/esconder o menu de categorias
if (categoriesLink && categoriesMenuMobile) {
    categoriesLink.addEventListener('click', function (event) {
        event.preventDefault(); // Evita o comportamento padrão do link
        categoriesMenuMobile.classList.toggle('hidden'); // Alterna visibilidade do menu de categorias
        mobileMenu.classList.remove('open'); // Fecha o menu móvel se aberto
        overlay.classList.remove('active'); // Fecha a sobreposição se aberta
    });
}

// Adicionando evento para cada link de categoria
const categoryLinks = categoriesMenuMobile ? categoriesMenuMobile.querySelectorAll('a') : [];

if (categoryLinks) {
    categoryLinks.forEach(link => {
        link.addEventListener('click', function () {
            // Ao clicar em uma categoria, ocultar o menu de categorias
            categoriesMenuMobile.classList.add('hidden'); // Oculta o menu de categorias
            mobileMenu.classList.remove('open'); // Oculta o menu móvel
            overlay.classList.remove('active'); // Oculta a sobreposição
        });
    });
}

// Fim da função vídeos grátis

// Começo da função visualizações

document.addEventListener('DOMContentLoaded', () => {
    // Incrementa visualizações ao clicar em imagens
    document.querySelectorAll('.small-image').forEach((img) => {
        let hasIncremented = false; // Variável de controle para a contagem

        img.addEventListener('click', () => {
            const mediaId = img.getAttribute('data-media-id');

            // Incrementa visualizações apenas se a imagem não estiver expandida
            if (!img.classList.contains('expanded')) {
                incrementViews(mediaId); // Incrementa visualizações ao expandir
                hasIncremented = true }

            expandOrCollapseImage(img); // Chama a função para expandir ou colapsar a imagem

            // Reseta a variável de controle após um ciclo completo
            if (img.classList.contains('expanded')) {
                img.addEventListener('transitionend', () => {
                    hasIncremented = false; // Reseta a variável ao colapsar
                }, { once: true });
            }
        });
    });

    // Incrementa visualizações ao dar play em vídeos
    document.querySelectorAll('.small-video').forEach((video) => {
        video.addEventListener('play', () => {
            const mediaId = video.getAttribute('data-media-id');
            incrementViews(mediaId);
        });
    });

    // Função para enviar requisição AJAX ao servidor
    function incrementViews(mediaId) {
        fetch(`/increment_views/${mediaId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
        })
        .then(response => {
            if (response.ok) {
                // Atualiza o contador no front-end
                const viewsElement = document.getElementById(`views-${mediaId}`);
                if (viewsElement) {
                    viewsElement.textContent = parseInt(viewsElement.textContent) + 1;
                }
            } else {
                console.error('Erro ao incrementar visualizações');
            }
        })
        .catch(err => console.error('Erro na requisição:', err));
    }
});

// Fim da função visualizações

document.getElementById('privacy-policy-link').addEventListener('click', function(event) {
    event.preventDefault(); // Impede o comportamento padrão do link
    var policySection = document.getElementById('privacy-policy');
    
    // Alterna a visibilidade da seção de políticas
    if (policySection.style.display === 'none') {
        policySection.style.display = 'block'; // Mostra a seção
    } else {
        policySection.style.display = 'none'; // Esconde a seção
    }
});


    let touchStartX = 0;
    let touchEndX = 0;
    let isTouching = false;

    // Armazenar o vídeo atualmente em execução
    let currentVideo = null;

    // Função para detectar o início do toque
    function startTouchEvent(videoElement) {
        touchStartX = event.touches[0].clientX; // Pega a posição inicial do toque
        isTouching = true;
    }

    // Previne o movimento de deslizar (touchmove) para que não inicie o vídeo
    function preventTouchMove(event) {
        if (isTouching) {
            // Evita o movimento lateral para que o vídeo não inicie
            event.preventDefault();
        }
    }

    // Função para finalizar o toque e determinar se foi um clique ou deslizar
    function endTouchEvent(videoElement) {
        touchEndX = event.changedTouches[0].clientX; // Pega a posição final do toque

        // Verifica se o movimento lateral foi pequeno o suficiente (menor que 90px de diferença)
        if (Math.abs(touchEndX - touchStartX) < 90) {
            // Se o movimento lateral for pequeno, trata como um clique
            togglePlayPause(videoElement);
        }

        isTouching = false;
    }

    // Função para alternar play/pause
    function togglePlayPause(videoElement) {
        // Se já existe um vídeo sendo reproduzido e não é o mesmo que foi clicado, pausa ele
        if (currentVideo && currentVideo !== videoElement) {
            currentVideo.pause(); // Pausa o vídeo anterior
        }

        // Agora, alterna entre play e pause no vídeo clicado
        if (videoElement.paused) {
            videoElement.play(); // Dá play no vídeo
            currentVideo = videoElement; // Armazena o vídeo atual como o vídeo que está tocando
        } else {
            videoElement.pause(); // Pausa o vídeo
            currentVideo = null; // Limpa a referência do vídeo atual
        }
    }

    // INÍCIO DA FUNÇÃO DE PESQUISA 

let currentVideoIndex = 0; // Índice do primeiro vídeo visível
let videoResults = []; // Array com os resultados da pesquisa
let videosPerPage = 1; // Quantidade de vídeos visíveis por vez

// Função para ajustar a quantidade de vídeos por página com base na largura da tela
function updateVideosPerPage() {
    const width = window.innerWidth;

    if (width < 768) {
        videosPerPage = 1; // Celulares
    } else if (width >= 768 && width < 1024) {
        videosPerPage = 4; // Tablets
    } else {
        videosPerPage = 5; // Desktop
    }
}

// Atualiza a quantidade de vídeos ao carregar a página
updateVideosPerPage();

// Atualiza a quantidade de vídeos ao redimensionar a janela
window.addEventListener('resize', updateVideosPerPage);

// Captura a pesquisa quando o usuário aperta Enter
document.getElementById("search").addEventListener("keypress", function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        const searchTerm = this.value.trim();

        if (searchTerm.length > 0) {
            fetch(`/search?q=${encodeURIComponent(searchTerm)}`)
                .then((response) => response.json())
                .then((results) => {
                    videoResults = results; // Armazena os resultados
                    currentVideoIndex = 0; // Reinicia a navegação
                    displayVideos(currentVideoIndex); // Exibe os vídeos
                    document.getElementById("search-results").classList.remove("hidden"); // Exibe a seção de resultados
                    
                    // Esconde o campo de pesquisa quando a pesquisa abrir
                    document.getElementById("search-container").classList.add("hidden");
                })
                .catch((error) => console.error("Erro ao buscar vídeos:", error));
        } else {
            clearSearchResults();
        }
    }
});

// Objeto para rastrear qual vídeo foi assistido por último
let lastPlayedVideo = null;

// Função para exibir os vídeos corretamente
function displayVideos(startIndex) {
    const container = document.querySelector(".search-videos");
    container.innerHTML = ""; // Limpa os vídeos anteriores

    if (videoResults.length > 0) {
        const endIndex = Math.min(startIndex + videosPerPage, videoResults.length);

        for (let i = startIndex; i < endIndex; i++) {
            const video = videoResults[i];

            const videoCard = document.createElement("div");
            videoCard.classList.add("search-video-card");
            videoCard.innerHTML = `
                <div class="profile-badge">
                    <img src="/static/uploads/profile_pictures/${video.profile_picture_url || 'default_profile_picture.jpg'}" 
                         alt="Perfil do usuário" class="profile-picture">
                </div>
                <video class="small-video" controls data-media-id="${video.id}">
                    <source src="/static/uploads/media/${video.filename}" type="video/mp4">
                </video>
                <div class="video-info">
                    <h3 class="video-title">${video.title}</h3>
                    <p class="video-description">${video.description || "Sem descrição disponível."}</p>
                    <p class="video-views" id="views-${video.id}">${video.views} visualizações</p>
                </div>
            `;
            container.appendChild(videoCard);
        }

        // Adiciona eventos para os vídeos
        document.querySelectorAll('.small-video').forEach((video) => {
            const mediaId = video.getAttribute('data-media-id');
            let videoWatchedCompletely = false; // Flag para saber se o vídeo foi assistido até o final

            video.addEventListener('play', function () {
                // Esconde título e descrição ao dar play
                const videoCard = this.closest('.search-video-card');
                if (videoCard) {
                    videoCard.querySelector('.video-info').style.display = 'none';
                }

                // Se outro vídeo estava sendo assistido antes, reseta ele
                if (lastPlayedVideo && lastPlayedVideo !== this) {
                    lastPlayedVideo.currentTime = 0; // Zera o tempo do vídeo anterior
                }

                // Se o vídeo foi assistido até o final e está sendo reproduzido novamente, contar nova visualização
                if (videoWatchedCompletely) {
                    incrementViews(mediaId);
                    videoWatchedCompletely = false; // Reseta o flag para a próxima reprodução
                }

                // Se este vídeo não for o mesmo que estava sendo assistido antes, contar visualização
                if (lastPlayedVideo !== this) {
                    incrementViews(mediaId);
                }

                lastPlayedVideo = this; // Atualiza o último vídeo assistido
            });

            video.addEventListener('pause', function () {
                // Reexibe título e descrição ao pausar
                const videoCard = this.closest('.search-video-card');
                if (videoCard) {
                    videoCard.querySelector('.video-info').style.display = 'block';
                }
            });

            video.addEventListener('ended', function () {
                videoWatchedCompletely = true; // Marca que o vídeo foi assistido até o final
            });
        });
    } else {
        container.innerHTML = "<p>Nada foi encontrado.</p>";
    }
}

// Função para incrementar visualizações no servidor
function incrementViews(mediaId) {
    fetch(`/increment_views/${mediaId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
    })
    .then(response => {
        if (response.ok) {
            const viewsElement = document.getElementById(`views-${mediaId}`);
            if (viewsElement) {
                viewsElement.textContent = `👁️ ${parseInt(viewsElement.textContent.replace(/\D/g, '')) + 1} visualizações`;
            }
        } else {
            console.error('Erro ao incrementar visualizações');
        }
    })
    .catch(err => console.error('Erro na requisição:', err));
}

// Função para limpar os resultados e mostrar o campo de pesquisa de volta
function clearSearchResults() {
    const searchResultsSection = document.getElementById("search-results");
    searchResultsSection.querySelector(".search-videos").innerHTML = ""; // Limpa os resultados
    searchResultsSection.classList.add("hidden"); // Esconde os resultados
    document.getElementById("search").value = ""; // Limpa o campo de pesquisa
    videoResults = []; // Limpa os resultados armazenados
    currentVideoIndex = 0; // Reseta o índice do vídeo
    
    // Mostra o campo de pesquisa novamente quando a pesquisa for fechada
    document.getElementById("search-container").classList.remove("hidden");

}

document.getElementById("next-video").addEventListener("click", function () {
    // Remove o primeiro vídeo e adiciona o próximo no final (efeito de carrossel infinito)
    if (videoResults.length > 0) {
        const firstVideo = videoResults.shift(); // Remove o primeiro item do array
        videoResults.push(firstVideo); // Adiciona o primeiro item no final
        displayVideos(0); // Atualiza a exibição começando do primeiro índice (sempre 0)
    }
});

document.getElementById("prev-video").addEventListener("click", function () {
    // Remove o último vídeo e adiciona ele no começo (efeito reverso)
    if (videoResults.length > 0) {
        const lastVideo = videoResults.pop(); // Remove o último item do array
        videoResults.unshift(lastVideo); // Adiciona o último item no começo
        displayVideos(0); // Atualiza a exibição começando do primeiro índice (sempre 0)
    }
});


// Modifique o event listener do searchToggle para isso:
document.addEventListener("DOMContentLoaded", function () {
    const searchToggle = document.getElementById("search-toggle");
    const searchContainer = document.getElementById("search-container");
    const searchInput = document.getElementById("search");
    const searchResults = document.getElementById("search-results");

    searchToggle.addEventListener("click", function () {
        // Se os resultados de pesquisa estão visíveis, fecha tudo
        if (!searchResults.classList.contains("hidden")) {
            clearSearchResults();
            return;
        }
        
        // Se não, alterna a visibilidade do campo de pesquisa normal
        if (searchContainer.classList.contains("hidden")) {
            searchContainer.classList.remove("hidden");
            searchInput.focus();
        } else {
            searchContainer.classList.add("hidden");
            searchInput.value = "";
        }
    });
});

// FIM DA FUNÇÃO DE PESQUISA 

//Começo carrocel
    document.addEventListener("DOMContentLoaded", function () {
        const carouselTrack = document.querySelector('#destaque-carrossel .carousel-track');
        const items = document.querySelectorAll('#destaque-carrossel .image-container');
        const itemWidth = items[0].clientWidth; // Largura de cada item
        let currentIndex = 0; // Índice atual do deslocamento
        const visibleItems = 4; // Número de itens visíveis na tela
        const totalItems = items.length; // Total de itens
    
        function setupInfiniteLoop() {
            for (let i = 0; i < visibleItems; i++) {
                const cloneStart = items[i].cloneNode(true);
                const cloneEnd = items[totalItems - 1 - i].cloneNode(true);
                carouselTrack.appendChild(cloneStart); // Clona no final
                carouselTrack.insertBefore(cloneEnd, carouselTrack.firstChild); // Clona no início
            }
        
            // Ajusta a posição inicial para centralizar o conteúdo real
            carouselTrack.style.transform = `translateX(-${visibleItems * itemWidth}px)`;
        }
    
        // Move o carrossel para frente
        function nextSlide() {
            currentIndex++;
            carouselTrack.style.transition = 'transform 0.5s ease-in-out';
            carouselTrack.style.transform = `translateX(-${(currentIndex + visibleItems) * itemWidth}px)`;
    
            // Reinicia o loop ao final
            if (currentIndex >= totalItems) {
                setTimeout(() => {
                    carouselTrack.style.transition = 'none';
                    currentIndex = 0;
                    carouselTrack.style.transform = `translateX(-${visibleItems * itemWidth}px)`;
                }, 500);
            }
        }
    
        // Move o carrossel para trás
        function prevSlide() {
            currentIndex--;
            carouselTrack.style.transition = 'transform 0.5s ease-in-out';
            carouselTrack.style.transform = `translateX(-${(currentIndex + visibleItems) * itemWidth}px)`;
    
            // Reinicia o loop ao início
            if (currentIndex < 0) {
                setTimeout(() => {
                    carouselTrack.style.transition = 'none';
                    currentIndex = totalItems - 1;
                    carouselTrack.style.transform = `translateX(-${(currentIndex + visibleItems) * itemWidth}px)`;
                }, 500);
            }
        }
    
        // Configura os botões de controle
        document.getElementById('next').addEventListener('click', nextSlide);
        document.getElementById('prev').addEventListener('click', prevSlide);
    
        // Configura o intervalo automático
        setInterval(nextSlide, 3000);
    
        // Configura o redimensionamento
        window.addEventListener('resize', function () {
            carouselTrack.style.transition = 'none';
            carouselTrack.style.transform = `translateX(-${(currentIndex + visibleItems) * items[0].clientWidth}px)`;
        });
    
        // Inicializa o loop
        setupInfiniteLoop();

            // Adiciona eventos para os botões de navegação
        document.querySelector('#next-button').addEventListener('click', nextSlide);
        document.querySelector('#prev-button').addEventListener('click', prevSlide);
    });

//Fim carrocel
    
// Começo trailer

const socket = io();
let currentLiveStatus = {}; // Armazena os status de live de todos os criadores

// Função para inicializar todos os badges de live
function initializeLiveBadges() {
    // Para cada badge no carrossel
    document.querySelectorAll('.profile-badge-carousel').forEach(badge => {
        const isLive = badge.dataset.isLive === 'True' || badge.dataset.isLive === 'true' || badge.dataset.isLive === '1';
        if (isLive) {
            updateCarouselBadge(badge, true);
            currentLiveStatus[badge.dataset.username] = true;
        }
    });

    // Para cada badge nas categorias
    document.querySelectorAll('.profile-badge-category').forEach(badge => {
        const isLive = badge.dataset.isLive === 'True' || badge.dataset.isLive === 'true' || badge.dataset.isLive === '1';
        if (isLive) {
            updateCategoryBadge(badge, true);
            currentLiveStatus[badge.dataset.username] = true;
        }
    });

    // Para o trailer (já está sendo tratado separadamente, mas mantemos consistência)
    document.querySelectorAll('.profile-badge-trailer').forEach(badge => {
        const isLive = badge.dataset.isLive === 'True' || badge.dataset.isLive === 'true' || badge.dataset.isLive === '1';
        if (isLive) {
            updateTrailerBadge(badge, true);
            currentLiveStatus[badge.dataset.username] = true;
        }
    });
}

// Funções de atualização (mantidas como estão)
function updateTrailerBadge(badge, isLive) {
    badge.classList.toggle('live', isLive);
    badge.style.border = isLive ? '2px solid red' : '2px solid white';

    const liveStatus = badge.closest('#trailers')?.querySelector('.live-status');
    if (liveStatus) {
        liveStatus.textContent = isLive ? 'Ao Vivo' : '';
        liveStatus.style.display = isLive ? 'block' : 'none';
    }
}

function updateCategoryBadge(badge, isLive) {
    badge.classList.toggle('live', isLive);
    badge.style.border = isLive ? '2px solid red' : '2px solid white';

    const liveStatus = badge.closest('.video-card')?.querySelector('.live-status');
    if (liveStatus) {
        liveStatus.textContent = isLive ? 'Ao Vivo' : '';
        liveStatus.style.display = isLive ? 'block' : 'none';
    }
}

function updateCarouselBadge(badge, isLive) {
    badge.classList.toggle('live', isLive);
    badge.style.border = isLive ? '2px solid red' : '2px solid white';

    const liveStatus = badge.closest('.image-container')?.querySelector('.live-status');
    if (liveStatus) {
        liveStatus.textContent = isLive ? 'Ao Vivo' : '';
        liveStatus.style.display = isLive ? 'block' : 'none';
    }
}

// Evento de atualização de status via Socket.IO (mantido como está)
socket.on('live_status_update', (data) => {
    const { username, is_live } = data;
    console.log(`Atualizando status para username: ${username}, is_live: ${is_live}`);
    
    // Atualiza o status global
    currentLiveStatus[username] = is_live;
    
    // Atualiza todos os badges para este usuário
    document.querySelectorAll(`[data-username="${username}"]`).forEach(badge => {
        if (badge.classList.contains('profile-badge-trailer')) {
            updateTrailerBadge(badge, is_live);
        } else if (badge.classList.contains('profile-badge-carousel')) {
            updateCarouselBadge(badge, is_live);
        } else if (badge.classList.contains('profile-badge-category')) {
            updateCategoryBadge(badge, is_live);
        }
    });
});

// Código do trailer (mantido como está)
const trailerVideos = document.querySelectorAll('#trailer-video .video');
const trailerTitle = document.getElementById('trailer-title');
const trailerDescription = document.getElementById('trailer-description');
const trailerProfilePicture = document.getElementById('trailer-profile-picture');

let currentTrailerIndex = 0;

function playNextTrailer() {
    trailerVideos[currentTrailerIndex].classList.add('hidden');
    trailerVideos[currentTrailerIndex].pause();
    trailerVideos[currentTrailerIndex].currentTime = 0;

    currentTrailerIndex = (currentTrailerIndex + 1) % trailerVideos.length;
    const nextVideo = trailerVideos[currentTrailerIndex];

    nextVideo.classList.remove('hidden');
    nextVideo.play();

    // Atualiza informações do trailer
    trailerTitle.textContent = nextVideo.dataset.title || "Sem Título Disponível";
    trailerDescription.textContent = nextVideo.dataset.description || "Nenhuma descrição disponível no momento.";
    trailerProfilePicture.src = nextVideo.dataset.profilePicture || 'default_profile_picture.jpg';

    // Atualiza badge do trailer atual
    updateLiveBadgeForCurrentTrailer(nextVideo);
}

function updateLiveBadgeForCurrentTrailer(videoElement) {
    const username = videoElement.dataset.username;
    const isLive = currentLiveStatus[username] || videoElement.dataset.isLive === 'true';
    const participantes = videoElement.dataset.participantes ? videoElement.dataset.participantes.split(',') : [];

    // 🔄 Atualiza badge
    const trailerBadge = document.querySelector('.profile-badge-trailer');
    if (trailerBadge) {
        trailerBadge.dataset.username = username;
        const img = trailerBadge.querySelector('img');
        if (img) {
            img.src = videoElement.dataset.profilePicture || 'default_profile_picture.jpg';
        }
        updateTrailerBadge(trailerBadge, isLive);
    }

    // 🔥 PARTICIPANTES: remove o anterior (se houver)
    document.querySelectorAll('#trailer-video .media-participants-container').forEach(el => el.remove());

    if (participantes.length > 0) {
        const container = document.createElement('div');
        container.className = 'media-participants-container';

        const badge = document.createElement('div');
        badge.className = 'participants-badge';
        badge.setAttribute('data-participants', participantes.join(','));

        badge.innerHTML = `
            <i class="fas fa-users"></i>
            <span class="participants-count">${participantes.length}</span>
            <div class="participants-tooltip">
                <strong>Participantes</strong>
                <ul>
                    ${participantes.map(nome => `<li>${nome}</li>`).join('')}
                </ul>
            </div>
        `;

        container.appendChild(badge);
        document.querySelector('#trailer-video').appendChild(container);

        // Reaplica os eventos de tooltip para este novo badge
        initializeParticipantTooltips(container);
    }
}


// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    initializeLiveBadges();
    
    // Configura eventos para alternar trailers automaticamente
    trailerVideos.forEach((video, index) => {
        video.addEventListener('ended', playNextTrailer);
        if (index !== 0) video.classList.add('hidden');
    });

    // Inicializa o primeiro trailer
    if (trailerVideos.length > 0) {
        const firstVideo = trailerVideos[0];
        firstVideo.classList.remove('hidden');
        firstVideo.play();

        // Atualiza informações
        trailerTitle.textContent = firstVideo.dataset.title || "Sem Título Disponível";
        trailerDescription.textContent = firstVideo.dataset.description || "Nenhuma descrição disponível no momento.";
        trailerProfilePicture.src = firstVideo.dataset.profilePicture || 'default_profile_picture.jpg';

        // Atualiza o badge do trailer
        updateLiveBadgeForCurrentTrailer(firstVideo);
    }
});

// Fim trailer

// Função para exibir o formulário de login
function showLoginForm() {
    document.getElementById("login-form").classList.remove("hidden");
    document.getElementById("signup-form").classList.add("hidden");
    document.getElementById("creator-signup-form").classList.add("hidden");
}

// Função para exibir o formulário de cadastro
function showSignupForm() {
    document.getElementById("signup-form").classList.remove("hidden");
    document.getElementById("login-form").classList.add("hidden");
    document.getElementById("creator-signup-form").classList.add("hidden");
}

// Alternar para o formulário de login ao clicar no botão "Entrar"
document.getElementById("show-login").addEventListener("click", showLoginForm);

// Alternar para o formulário de cadastro ao clicar no link "Cadastrar nova conta"
document.getElementById("show-signup").addEventListener("click", showSignupForm);

// Exibir o formulário de login quando o botão de login for clicado
document.getElementById("login-btn").addEventListener("click", function () {
    showLoginForm();
});

// Fechar o formulário de login quando o botão de fechar for clicado
document.getElementById("close-login").addEventListener("click", function () {
    document.getElementById("login-form").classList.add("hidden");
});

// Fechar o formulário de login ao clicar fora dele
document.getElementById("login-form").addEventListener("click", function (e) {
    if (e.target === this) {
        this.classList.add("hidden");
    }
});

// Fechar o formulário de cadastro ao clicar fora dele
document.getElementById("signup-form").addEventListener("click", function (e) {
    if (e.target === this) {
        this.classList.add("hidden");
    }
});

// Alternar para o formulário de login
document.getElementById("show-login").addEventListener("click", function () {
    document.getElementById("login-form").classList.remove("hidden");
    document.getElementById("signup-form").classList.add("hidden");
    document.getElementById("creator-signup-form").classList.add("hidden");
});

// Alternar para o formulário de cadastro normal
document.getElementById("show-signup").addEventListener("click", function () {
    document.getElementById("signup-form").classList.remove("hidden");
    document.getElementById("login-form").classList.add("hidden");
    document.getElementById("creator-signup-form").classList.add("hidden");
});

// Alternar para o formulário de criador de conteúdo
document.getElementById("show-creator-signup").addEventListener("click", function () {
    document.getElementById("signup-form").classList.add("hidden");
    document.getElementById("creator-signup-form").classList.remove("hidden");
});

// Voltar para o formulário de cadastro normal
document.getElementById("show-signup-from-creator").addEventListener("click", function () {
    document.getElementById("creator-signup-form").classList.add("hidden");
    document.getElementById("signup-form").classList.remove("hidden");
});

// Fechar os formulários ao clicar fora deles
document.getElementById("creator-signup-form").addEventListener("click", function (e) {
    if (e.target === this) {
        this.classList.add("hidden");
    }
});

// Fechar os formulários
document.getElementById("close-login").addEventListener("click", function () {
    document.getElementById("login-form").classList.add("hidden");
});

document.getElementById("close-signup").addEventListener("click", function () {
    document.getElementById("signup-form").classList.add("hidden");
});

document.getElementById("close-creator-signup").addEventListener("click", function () {
    document.getElementById("creator-signup-form").classList.add("hidden");
});

// Alternar para o formulário de login a partir do formulário de criador de conteúdo
document.getElementById("show-login-from-creator").addEventListener("click", function () {
    document.getElementById("creator-signup-form").classList.add("hidden"); // Esconde o formulário de criador
    document.getElementById("login-form").classList.remove("hidden"); // Exibe o formulário de login
});



// Exibir e ocultar formulários
document.getElementById('forgot-password-link').addEventListener('click', function() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('forgot-password-modal').classList.remove('hidden');
});

document.getElementById('close-forgot-password').addEventListener('click', function() {
    document.getElementById('forgot-password-modal').classList.add('hidden');
    document.getElementById('login-form').classList.remove('hidden');
});

document.getElementById('close-login').addEventListener('click', function() {
    document.getElementById('login-form').classList.add('hidden');
});

document.getElementById('close-reset-password').addEventListener('click', function() {
    document.getElementById('reset-password-modal').classList.add('hidden');
});


// Variável global para armazenar o email
let globalEmail = '';

// Lógica para enviar o código de recuperação
document.getElementById('forgot-password-form').addEventListener('submit', function(e) {
    e.preventDefault(); // Impede o envio do formulário

    const emailInput = document.getElementById('recovery-email'); // Captura o campo de email
    globalEmail = emailInput.value; // Armazena o email na variável global

    const formData = new FormData(this); // Cria um objeto FormData a partir do formulário

    fetch('/forgot_password', {
        method: 'POST',
        body: formData,
    })
    .then(response => {
        if (response.ok) {
            alert("Código de recuperação enviado para o seu e-mail.");
            // Abre o modal de redefinição de senha
            document.getElementById('forgot-password-modal').classList.add('hidden');
            document.getElementById('reset-password-modal').classList.remove('hidden');
        } else {
            alert("Erro ao enviar o código de recuperação.");
        }
    })
    .catch(error => {
        console.error('Erro inesperado:', error);
        alert("Erro ao enviar o código de recuperação. Tente novamente.");
    });
});

// Lógica para redefinir a senha
document.getElementById('reset-password-form').addEventListener('submit', function(e) {
    e.preventDefault(); // Impede o envio do formulário

    const formData = new FormData(this); // Cria um objeto FormData a partir do formulário

    // Adicionando o log para verificar os dados enviados
    console.log('Dados enviados:', {
        email: globalEmail, // Usa a variável global
        verificationCode: formData.get('verification-code'),
        newPassword: formData.get('new-password')
    });

    fetch(`/reset_password/${globalEmail}`, { // Inclui o email na URL
        method: 'POST',
        body: formData,
    })
    .then(response => {
        if (response.ok) {
            alert("Senha redefinida com sucesso!");
            // Após o alerta, abrir o modal de login
            document.getElementById('reset-password-modal').classList.add('hidden'); // Fecha o modal de redefinição
            document.getElementById('login-form').classList.remove('hidden'); // Abre o modal de login
        } else {
            alert("Erro ao redefinir a senha.");
        }
    })
    .catch(error => {
        console.error('Erro inesperado:', error);
        alert("Erro ao redefinir a senha. Tente novamente.");
    });
});

// Começo Assine
document.getElementById("subscribe-btn").addEventListener("click", function () {
    window.location.href = "/creators_list";
});

document.addEventListener("DOMContentLoaded", function () {
    const loginBtn = document.getElementById("login-btn");
    const logoutBtn = document.getElementById("logout-btn");

    if (loginBtn && logoutBtn) {
        fetch("/check_login")  // ✅ Usando sua rota existente
            .then(response => response.json())
            .then(data => {
                if (data.is_logged_in) {
                    loginBtn.style.display = "none";  // Esconde login
                    logoutBtn.style.display = "inline-block";  // Mostra logout
                } else {
                    loginBtn.style.display = "inline-block";  // Mostra login
                    logoutBtn.style.display = "none";  // Esconde logout
                }
            })
            .catch(error => console.error("Erro ao verificar login:", error));
    }
});
// Fim Assine


// Botão Assistir
document.getElementById("btn-assistir").addEventListener("click", function () {
    window.location.href = "/creators_list";
});

// Redirecionar para assinatura
function subscribeTo(creatorUsername) {
    window.location.href = "/subscribe/" + creatorUsername;
}

// Redirecionar para o dashboard do criador assinado
function goToDashboard(creatorUsername) {
    window.location.href = "/dashboard/" + creatorUsername;
}


//Botoes dentro do cadastro do criador de conteudos
function nextStep(step) {
    document.querySelectorAll('.form-step').forEach(step => step.classList.add('hidden'));
    document.getElementById(`step-${step}`).classList.remove('hidden');
}

function prevStep(step) {
    document.querySelectorAll('.form-step').forEach(step => step.classList.add('hidden'));
    document.getElementById(`step-${step}`).classList.remove('hidden');
}

//Botoes dentro do cadastro faz parte do aceitar os termos para poder ser cadastrado

function openTermsModal() {
    document.getElementById("terms-modal").classList.remove("hidden");
    document.getElementById("terms-modal").classList.add("flex");
}

function closeTermsModal() {
    document.getElementById("terms-modal").classList.remove("flex");
    document.getElementById("terms-modal").classList.add("hidden");
}

// Função de particiapantes

function initializeParticipantTooltips(container = document) {
    const tooltips = container.querySelectorAll('.participants-badge, .pessoas-midia-tooltip');
    
    tooltips.forEach(tooltip => {
        const content = tooltip.querySelector('.participants-tooltip, .pessoas-tooltip-content');
        
        // Desktop - hover
        tooltip.addEventListener('mouseenter', function () {
            if (window.innerWidth > 768 && content) {
                content.style.display = 'block';
                
                const rect = content.getBoundingClientRect();
                if (rect.right > window.innerWidth) {
                    content.style.right = 'auto';
                    content.style.left = '0';
                }
            }
        });

        tooltip.addEventListener('mouseleave', function () {
            if (window.innerWidth > 768 && content) {
                content.style.display = 'none';
                content.style.right = '';
                content.style.left = '';
            }
        });

        // Mobile - touch
        tooltip.addEventListener('click', function (e) {
            if (window.innerWidth <= 768 && content) {
                e.stopPropagation();
                content.style.display = content.style.display === 'block' ? 'none' : 'block';
            }
        });
    });

    // Clicar fora fecha tudo no mobile
    document.addEventListener('click', function (e) {
        if (window.innerWidth <= 768 &&
            !e.target.closest('.participants-badge') &&
            !e.target.closest('.pessoas-midia-tooltip')) {
            document.querySelectorAll('.participants-tooltip, .pessoas-tooltip-content').forEach(content => {
                content.style.display = 'none';
            });
        }
    });
}

// Inicializa quando a página carregar
document.addEventListener('DOMContentLoaded', function () {
    initializeParticipantTooltips();
});












    








