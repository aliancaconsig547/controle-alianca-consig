document.addEventListener('DOMContentLoaded', () => {
    // --- FUNÇÕES UTILITÁRIAS DE MÁSCARA E CONVERSÃO ---
    
    // Converte "R$ 1.500,50" -> 1500.50 (Float)
    function parseMoney(value) {
        if (!value) return 0;
        // Remove tudo que não é dígito ou vírgula
        let clean = value.replace(/[^\d,]/g, ''); 
        // Troca vírgula por ponto para o JS entender
        clean = clean.replace(',', '.');
        return parseFloat(clean) || 0;
    }

    // Aplica máscara de moeda (Ex: 1500.5 -> R$ 1.500,50) no INPUT
    const maskMoney = (event) => {
        let input = event.target;
        let value = input.value.replace(/\D/g, ''); // Remove tudo que não é número
        
        value = (Number(value) / 100).toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        });
        
        input.value = value;
        calcularLiquido(); // Recalcula sempre que a máscara roda
    };

    // Aplica máscara de CPF
    const maskCPF = (event) => {
        let input = event.target;
        let v = input.value.replace(/\D/g, ""); // Remove não dígitos
        
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
    const percComissaoInput = document.getElementById('percentual_comissao');
    const resultadoSpan = document.getElementById('resultado_liquido');
    const cpfInput = document.getElementById('cpf');

    // --- APLICAÇÃO DOS EVENTOS ---
    
    // Máscara de CPF
    if (cpfInput) {
        cpfInput.addEventListener('input', maskCPF);
    }

    // Máscara de Moeda e Cálculo
    [valorContratoInput, valorQuitadoInput, custoProdutoInput].forEach(el => {
        if (el) {
            el.addEventListener('input', maskMoney);
            // Formata o valor inicial se já vier preenchido do backend (edição)
            if(el.value && !el.value.includes('R$')) {
                // Simula um evento para formatar o valor inicial
                 let val = parseFloat(el.value).toFixed(2).replace('.', '');
                 el.value = val;
                 el.dispatchEvent(new Event('input'));
            }
        }
    });

    if (percComissaoInput) {
        percComissaoInput.addEventListener('change', calcularLiquido);
    }

    // --- LÓGICA DE CÁLCULO ---
    function calcularLiquido() {
        const valorContrato = parseMoney(valorContratoInput.value);
        const valorQuitado = parseMoney(valorQuitadoInput.value);
        const custoProduto = parseMoney(custoProdutoInput.value);
        const percComissao = parseFloat(percComissaoInput.value) / 100 || 0;

        // Fórmula
        const valorComissao = valorContrato * percComissao;
        const liquidoFinal = valorContrato - valorQuitado - valorComissao - custoProduto;

        resultadoSpan.textContent = liquidoFinal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }
});