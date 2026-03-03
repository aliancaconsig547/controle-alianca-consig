document.addEventListener('DOMContentLoaded', () => {
    // --- FUNÇÕES UTILITÁRIAS ---
    function parseMoney(value) {
        if (!value) return 0;
        let clean = value.replace(/[^\d,]/g, '').replace(',', '.');
        return parseFloat(clean) || 0;
    }

    const maskMoney = (event) => {
        let input = event.target;
        let value = input.value.replace(/\D/g, ''); 
        value = (Number(value) / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        input.value = value;
        calcularLiquido();
    };

    const maskCPF = (event) => {
        let input = event.target;
        let v = input.value.replace(/\D/g, "");
        if (v.length > 14) v = v.slice(0, 14);
        v = v.replace(/(\d{3})(\d)/, "$1.$2");
        v = v.replace(/(\d{3})(\d)/, "$1.$2");
        v = v.replace(/(\d{3})(\d{1,2})$/, "$1-$2");
        input.value = v;
    };

    // --- SELEÇÃO DE ELEMENTOS ---
    const valorContratoInput = document.getElementById('valor_contrato');
    const valorQuitadoInput = document.getElementById('valor_quitado');
    const custoProdutoInput = document.getElementById('custo_produto');
    const custosContratoInput = document.getElementById('custos_contrato'); // Novo
    const valorDevolvidoInput = document.getElementById('valor_devolvido'); // Novo
    const percComissaoInput = document.getElementById('percentual_comissao');
    const resultadoSpan = document.getElementById('resultado_liquido');
    const cpfInput = document.getElementById('cpf');

    // --- EVENT LISTENERS ---
    if (cpfInput) cpfInput.addEventListener('input', maskCPF);

    // Inputs Monetários (Adicionado os novos campos na lista)
    const inputsMonetarios = [
        valorContratoInput, 
        valorQuitadoInput, 
        custoProdutoInput, 
        custosContratoInput, 
        valorDevolvidoInput
    ];

    inputsMonetarios.forEach(el => {
        if (el) {
            el.addEventListener('input', maskMoney);
            // Formata ao carregar se já tiver valor (Edição)
            if(el.value && !el.value.includes('R$')) {
                 let val = parseFloat(el.value).toFixed(2).replace('.', '');
                 el.value = val;
                 el.dispatchEvent(new Event('input'));
            }
        }
    });

    if (percComissaoInput) percComissaoInput.addEventListener('change', calcularLiquido);

    // --- LÓGICA DE CÁLCULO ATUALIZADA ---
    function calcularLiquido() {
        const valorContrato = parseMoney(valorContratoInput.value);
        const valorQuitado = parseMoney(valorQuitadoInput.value);
        const custoProduto = parseMoney(custoProdutoInput.value);
        const custosExtras = parseMoney(custosContratoInput.value); // Novo
        const valorDevolvido = parseMoney(valorDevolvidoInput.value); // Novo
        
        const percComissao = parseFloat(percComissaoInput.value) / 100 || 0;

        const valorComissao = valorContrato * percComissao;
        
        // FÓRMULA: Contrato - Quitado - Comissão - CustoProduto - CustosExtras - Devolvido
        const liquidoFinal = valorContrato - valorQuitado - valorComissao - custoProduto - custosExtras;

        resultadoSpan.textContent = liquidoFinal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }
});