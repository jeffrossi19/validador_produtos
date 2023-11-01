from flask import Flask, request, send_file
import pandas as pd
import psycopg2
import xlsxwriter
import hvac
from io import BytesIO

app = Flask(__name__)

# Configurações do banco de dados PostgreSQL
db_config = {
    "dbname": "anymarket",
    "user": None,
    "password": None,
    "host": "anymarket-prd-read-replica-reports.cdj7j791k4zu.us-east-1.rds.amazonaws.com",
    "options": "-c search_path=dbo,anymarket_prd",
}

# Configuração da conexão com o Vault
vault_url = "http://10.119.18.99:8200"
role_id = "cb4169c7-a2ff-0f91-aa65-1db1cdad64fa"
secret_id = "6b3f7754-de18-9a68-fc44-44b50e572504"
role_name = "validador_produtos"

client = hvac.Client(url=vault_url)

def login_to_vault_with_approle(client, role_id, secret_id):
    try:
        login_response = client.auth.approle.login(
            role_id=role_id,
            secret_id=secret_id,
        )

        if login_response and "auth" in login_response and "client_token" in login_response["auth"]:
            client.token = login_response["auth"]["client_token"]
            return True
        else:
            return False
    except Exception as e:
        print("Erro ao autenticar no Vault:", str(e))
        return False

if login_to_vault_with_approle(client, role_id, secret_id):
    print("Autenticado com sucesso no Vault usando AppRole.")
else:
    print("Falha na autenticação no Vault usando AppRole.")

def get_database_credentials():
    try:
        response = client.read(f"database/static-creds/{role_name}")

        if response and "data" in response and "username" in response["data"] and "password" in response["data"]:
            username = response["data"]["username"]
            password = response["data"]["password"]
            return username, password
        else:
            raise Exception("Credenciais de banco de dados não encontradas no Vault.")

    except Exception as e:
        print("Erro ao obter credenciais do Vault:", str(e))
        return None, None

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
        username, password = get_database_credentials()

        if username and password:
            conn = psycopg2.connect(
                dbname=db_config["dbname"],
                user=username,
                password=password,
                host=db_config["host"],
                options=db_config["options"],
            )

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

            cursor = conn.cursor()
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

            output = BytesIO()
            writer = pd.ExcelWriter(output, engine="xlsxwriter")
            df.to_excel(writer, sheet_name="Planilha", index=False)
            writer.close()
            output.seek(0)
            conn.close()

            
            return send_file(
                output,
                as_attachment=True,
                download_name="planilha.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
         
    except Exception as e:
        print(e)
        return str(e), 500  # Retorna um erro 500 em caso de exceção

if __name__ == "__main__":
    app.run(debug=False)