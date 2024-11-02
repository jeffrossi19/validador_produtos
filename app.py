from flask import Flask, request, send_file
import pandas as pd
from vault_client import VaultClient
from database_connection import DatabaseConnection
from generate_excel import generate_excel

app = Flask(__name__)

# Configurações do banco de dados PostgreSQL
db_config = {
    "dbname": "your_dbname",
    "host": "your_host",
    "options": "your_options",
}

# Configuração da conexão com o Vault
vault_client = VaultClient(
)

@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Validação de Produtos</title>
    </head>
    <body>
        <h1>Validação de Produtos</h1>

        <form id="consulta-form">
            <label for="oi_cliente">OI do Cliente:</label>
            <input type="text" id="oi_cliente" name="oi_cliente" required>
            <button type="submit">Gerar Planilha</button>
        </form>

        <script>
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
        </script>
    </body>
    </html>
    """

@app.route("/gerar_planilha", methods=["POST"])
def gerar_planilha():
    try:
        oi_cliente = request.form["oi_cliente"]

        if vault_client.login():
            username, password = vault_client.get_database_credentials()
            if username and password:
                with DatabaseConnection() as conn:
                    consulta_sql = """
                        SELECT
                            ae.ds_validacao AS descricao_da_validacao,
                            r.id_in_client AS sku,
                            r.product_title AS titulo_do_produto,
                            r.sku_title AS titulo_do_sku
                        FROM (
                            SELECT
                                p1.id AS id_product,
                                p1.title AS product_title,
                                s.id AS id_sku,
                                s.title AS sku_title,
                                s.id_in_client AS id_in_client,
                                st.amount AS stock,
                                c1.path AS categoria,
                                b1.name AS marca
                            FROM
                                product p1
                                INNER JOIN sku s ON s.oi = %s
                                    AND s.id_product = p1.id
                                INNER JOIN stock st ON st.oi = %s
                                    AND st.id_sku = s.id
                                LEFT JOIN category c1 ON c1.id = p1.id_category
                                    AND c1.oi = %s
                                LEFT JOIN brand b1 ON b1.id = p1.id_brand
                                    AND b1.oi = %s
                            WHERE
                                p1.oi = %s
                                AND s.is_active = '1'
                        ) AS r,
                        public.aegp_validacao_anuncios ae
                        WHERE
                            ae.bo_ativo = 1
                            AND ae.ds_marketplace = 'BACKOFFICE'
                            AND public.aegp_valida_anuncio(r.id_sku, ae.ds_marketplace, ae.ds_validacao) = 1
                    """
                    with conn.cursor() as cursor:
                        cursor.execute(
                            consulta_sql, (oi_cliente, oi_cliente, oi_cliente, oi_cliente, oi_cliente)
                        )
                        df = pd.DataFrame(
                            cursor.fetchall(),
                            columns=[
                                "descricao_da_validacao",
                                "sku",
                                "titulo_do_produto",
                                "titulo_do_sku",
                            ],
                        )
                    output = generate_excel(df)
                    return send_file(
                        output,
                        as_attachment=True,
                        download_name="planilha.xlsx",
                        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
        return "Failed to authenticate or retrieve credentials", 500
    except Exception as e:
        app.logger.error("Error generating spreadsheet: %s", str(e))
        return str(e), 500

if __name__ == "__main__":
    app.run(debug=False)