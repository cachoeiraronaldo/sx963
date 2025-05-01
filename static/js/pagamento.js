// const mp = new MercadoPago('TEST-e2face31-69ca-428f-bbc9-23f3462bfabf', { locale: 'pt-BR' });

// AMBIENTE DE PRODUÇÃO:
const mp = new MercadoPago('APP_USR-a538b0f2-b924-4a3c-83a2-29b44657ba5c', { locale: 'pt-BR' });

const creatorUsername = document.getElementById('creator-username').value;
const tipoPagamento = document.getElementById('tipo-pagamento').value;
const mediaId = document.getElementById('media-id').value || null;
const valorPagamento = document.getElementById('valor-pagamento').value || '19.90';


console.log("Valor do Pagamento:", valorPagamento);
console.log("Tipo de Pagamento:", tipoPagamento);
console.log("ID do Vídeo:", mediaId);

const cardForm = mp.cardForm({
    amount: valorPagamento,
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
        onFormMounted: () => console.log('Formulário montado'),
        onSubmit: async (event) => {

            event.preventDefault();

            try {
                const { token, issuerId, paymentMethodId, installments } = await cardForm.getCardFormData();
                if (!token) throw new Error('Não foi possível gerar o token do cartão.');

                const response = await fetch('/process_payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        token,
                        payment_method_id: paymentMethodId,
                        installments,
                        issuer_id: issuerId,
                        creator_username: creatorUsername,
                        [tipoPagamento === 'video' ? 'valor_video' : 'valor_assinatura']: valorPagamento,
                        tipo_pagamento: tipoPagamento,
                        ...(mediaId && { media_id: mediaId })
                    })
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    if (errorData.error) {
                        alert(errorData.error);
                    } else {
                        throw new Error(`Erro na requisição: ${response.statusText}`);
                    }
                    return;
                }

                const data = await response.json();

                if (["approved", "pending", "in_process"].includes(data.status)) {
                    alert('✅ Pagamento processado com sucesso!');
                    const usernameSemArroba = creatorUsername.replace('@', '');
                    window.location.href = `/dashboard/${usernameSemArroba}`;
                } else {
                    alert(`❌ Erro ao processar pagamento: ${data.error || "Pagamento não aprovado."}`);
                }
            } catch (error) {
                alert(`❌ Erro: ${error.message}`);
            }
        }
    }
});

document.getElementById('form-checkout-pix').addEventListener('submit', async function (event) {
    event.preventDefault();

    const formData = {
        amount: parseFloat(valorPagamento),
        email: document.getElementById('pix-user-email').value,
        description: document.getElementById('pix-description').value,
        creator_username: creatorUsername,
        tipo_pagamento: tipoPagamento,
        media_id: mediaId
    };

    try {
        const response = await fetch('/process_payment_pix', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        console.log(result);

        if (result.status === "pending") {
            document.getElementById('pix-qr-code').src = `data:image/png;base64,${result.qr_code}`;
            document.getElementById('pix-copy-code').value = result.qr_code_copy;
            document.getElementById('pix-payment-result').style.display = 'block';
            alert("Pagamento pendente! Utilize o QR Code ou o código Pix para concluir o pagamento.");
        } else {
            alert("Erro ao processar pagamento: " + result.error);
        }
    } catch (error) {
        console.error("Erro ao processar pagamento:", error);
        alert("Erro ao processar pagamento. Tente novamente.");
    }
});

function copyPixCode() {
    const codeInput = document.getElementById('pix-copy-code');
    codeInput.select();
    codeInput.setSelectionRange(0, 99999);
    document.execCommand("copy");
    alert("Código Pix copiado!");
}
