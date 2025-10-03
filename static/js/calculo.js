document.addEventListener('DOMContentLoaded', () => {
    // Campos que afetam o cálculo
    const valorContratoInput = document.getElementById('valor_contrato');
    const valorQuitadoInput = document.getElementById('valor_quitado'); // NOVO CAMPO
    const custoProdutoInput = document.getElementById('custo_produto');
    const percComissaoInput = document.getElementById('percentual_comissao');
    const resultadoSpan = document.getElementById('resultado_liquido');

    const campos = [valorContratoInput, valorQuitadoInput, custoProdutoInput, percComissaoInput];

    campos.forEach(campo => {
        if (campo) { // Verifica se o campo existe na página
            campo.addEventListener('input', calcularLiquido);
        }
    });

    function calcularLiquido() {
        const valorContrato = parseFloat(valorContratoInput.value) || 0;
        const valorQuitado = parseFloat(valorQuitadoInput.value) || 0; // NOVO CAMPO
        const custoProduto = parseFloat(custoProdutoInput.value) || 0;
        const percComissao = parseFloat(percComissaoInput.value) / 100 || 0;

        // Nova fórmula
        const valorComissao = valorContrato * percComissao;
        const liquidoFinal = valorContrato - valorQuitado - valorComissao - custoProduto;

        resultadoSpan.textContent = liquidoFinal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }
});