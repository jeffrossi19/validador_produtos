import hvac
from flask import current_app as app

class VaultClient:
    def __init__(self, url, role_id, secret_id, role_name):
        self.client = hvac.Client(url=url)
        self.role_id = role_id
        self.secret_id = secret_id
        self.role_name = role_name
        self.token = None

    def login(self):
        try:
            login_response = self.client.auth.approle.login(
                role_id=self.role_id,
                secret_id=self.secret_id,
            )
            if login_response and "auth" in login_response and "client_token" in login_response["auth"]:
                self.token = login_response["auth"]["client_token"]
                self.client.token = self.token
                app.logger.info("Authenticated successfully with Vault using AppRole.")
                return True
            else:
                app.logger.error("Failed to authenticate with Vault using AppRole.")
                return False
        except Exception as e:
            app.logger.error("Error authenticating with Vault: %s", str(e))
            return False

    def get_database_credentials(self):
        try:
            response = self.client.read(f"database/static-creds/{self.role_name}")
            if response and "data" in response and "username" in response["data"] and "password" in response["data"]:
                return response["data"]["username"], response["data"]["password"]
            else:
                raise Exception("Database credentials not found in Vault.")
        except Exception as e:
            app.logger.error("Error retrieving credentials from Vault: %s", str(e))
            return None, None