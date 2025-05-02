// Configuração inicial
const mp = new MercadoPago('APP_USR-a538b0f2-b924-4a3c-83a2-29b44657ba5c', {
    locale: 'pt-BR'
});

// Elementos do DOM
const elements = {
    creatorUsername: document.getElementById('creator-username'),
    tipoPagamento: document.getElementById('tipo-pagamento'),
    mediaId: document.getElementById('media-id'),
    valorPagamento: document.getElementById('valor-pagamento'),
    cardForm: document.getElementById('form-checkout'),
    pixForm: document.getElementById('form-checkout-pix'),
    pixResult: document.getElementById('pix-payment-result'),
    qrCode: document.getElementById('pix-qr-code'),
    copyCode: document.getElementById('pix-copy-code')
};

// Configuração do formulário de cartão
const cardFormConfig = {
    amount: elements.valorPagamento.value || '19.90',
    autoMount: true,
    form: {
        id: 'form-checkout',
        cardholderName: { id: 'form-checkout__cardholderName' },
        cardholderEmail: { id: 'form-checkout__cardholderEmail' },
        cardNumber: { id: 'form-checkout__cardNumber' },
        cardExpirationDate: { id: 'form-checkout__cardExpirationDate' },
        securityCode: { id: 'form-checkout__securityCode' },
        installments: { id: 'form-checkout__installments' },
        issuer: { id: 'form-checkout__issuer' }
    },
    callbacks: {
        onFormMounted: (error) => {
            if (error) console.error('Erro ao montar formulário:', error);
        },
        onSubmit: async (event) => {
            event.preventDefault();
            try {
                const { token, issuerId, paymentMethodId, installments } = mp.cardForm.getCardFormData();
                
                if (!token) {
                    throw new Error('Não foi possível gerar o token do cartão.');
                }

                const payload = {
                    token,
                    payment_method_id: paymentMethodId,
                    installments: parseInt(installments),
                    issuer_id: issuerId,
                    creator_username: elements.creatorUsername.value,
                    tipo_pagamento: elements.tipoPagamento.value,
                    [elements.tipoPagamento.value === 'video' ? 'valor_video' : 'valor_assinatura']: elements.valorPagamento.value,
                    ...(elements.mediaId.value && { media_id: elements.mediaId.value })
                };

                const response = await fetch('/process_payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || "Erro ao processar pagamento");
                }

                if (["approved", "pending", "in_process"].includes(data.status)) {
                    alert('✅ Pagamento processado com sucesso!');
                    window.location.href = data.redirect_url || `/dashboard/${elements.creatorUsername.value.replace('@', '')}`;
                } else {
                    throw new Error(data.error || "Pagamento não aprovado");
                }
            } catch (error) {
                console.error('Erro no pagamento:', error);
                alert(`❌ Erro: ${error.message}`);
            }
        }
    }
};

// Inicializar formulário de cartão
const cardForm = mp.cardForm(cardFormConfig);

// Configurar PIX
elements.pixForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    
    try {
        const response = await fetch('/process_payment_pix', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                creator_username: elements.creatorUsername.value,
                tipo_pagamento: elements.tipoPagamento.value,
                media_id: elements.mediaId.value,
                valor: elements.valorPagamento.value
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Erro ao processar PIX");
        }

        if (result.status === "pending") {
            elements.qrCode.src = `data:image/png;base64,${result.qr_code}`;
            elements.copyCode.value = result.qr_code_copy;
            elements.pixResult.style.display = 'block';
            alert("Pagamento pendente! Utilize o QR Code ou o código Pix para concluir o pagamento.");
        } else {
            throw new Error(result.error || "Status inesperado");
        }
    } catch (error) {
        console.error('Erro no PIX:', error);
        alert(`❌ Erro: ${error.message}`);
    }
});

// Então modifique a função:
async function copyPixCode() {
    try {
        await navigator.clipboard.writeText(elements.copyCode.value);
        const feedback = document.getElementById('copy-feedback');
        feedback.classList.add('show');
        setTimeout(() => feedback.classList.remove('show'), 2000);
    } catch (err) {
        alert("Não foi possível copiar. Selecione e copie manualmente.");
    }
}