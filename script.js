document.getElementById('consulta-form').addEventListener('submit', function (event) {
    event.preventDefault();

    const oiCliente = document.getElementById('oi_cliente').value;

    fetch('/gerar_planilha', {
        method: 'POST',
        body: new URLSearchParams({ oi_cliente: oiCliente }),
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(new Blob([blob]));
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = 'planilha.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    })
    .catch(error => console.error('Erro:', error));
});
