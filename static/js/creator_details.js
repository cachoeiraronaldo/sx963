// Atualiza os seguidores
function updateFollowers(username) {
    fetch(`/get_followers/${username}`)
        .then(response => response.json())
        .then(data => {
            if (data.total_followers !== undefined) {
                document.getElementById('total-followers').innerText = data.total_followers;
            }
        })
        .catch(error => console.error('Erro ao obter seguidores:', error));
}

// Atualiza as curtidas
function updateLikes(username) {
    fetch(`/get_likes/${username}`)
        .then(response => response.json())
        .then(data => {
            if (data.total_likes !== undefined) {
                document.getElementById('total-likes').innerText = data.total_likes;
            }
        })
        .catch(error => console.error('Erro ao obter curtidas:', error));
}

// Função para lidar com o botão "Voltar"
function handleBackButton() {
    const referrer = sessionStorage.getItem('referrer');
    if (referrer) {
        window.location.href = referrer;
        sessionStorage.removeItem('referrer');
    } else {
        window.location.href = "/";
    }
}

// Ao carregar a página, atualiza os dados
document.addEventListener('DOMContentLoaded', () => {
    const username = document.body.dataset.username;
    if (username) {
        updateLikes(username);
        updateFollowers(username);
    }
});
