import os
import json
import traceback

def _from_env(var_name: str):
    val = os.getenv(var_name)
    if val:
        try:
            return json.loads(val)
        except Exception:
            return val
    return None


def get_google_credentials_json():
    """Return Google credentials JSON (dict) from one of these sources, in order:
    1. `GOOGLE_APPLICATION_CREDENTIALS` env var pointing to JSON file path (Render Secret Files)
    2. `GOOGLE_CREDENTIALS_JSON` env var (JSON string)
    3. AWS Secrets Manager secret named by `GOOGLE_CREDENTIALS_SECRET_NAME`
    4. Azure Key Vault secret named by `GOOGLE_CREDENTIALS_SECRET_NAME` in vault `AZURE_KEY_VAULT_NAME`
    5. Local file `credentials.json` in project root

    Returns dict or None.
    """
    # 1) GOOGLE_APPLICATION_CREDENTIALS (file path - standard Google Cloud approach)
    try:
        creds_file_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_file_path and os.path.exists(creds_file_path):
            with open(creds_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        traceback.print_exc()
    
    # 2) GOOGLE_CREDENTIALS_JSON env var (inline JSON)
    try:
        env_val = _from_env('GOOGLE_CREDENTIALS_JSON')
        if env_val:
            return env_val
    except Exception:
        pass

    # 2) AWS Secrets Manager
    try:
        secret_name = os.getenv('GOOGLE_CREDENTIALS_SECRET_NAME')
        if secret_name:
            import boto3
            client = boto3.client('secretsmanager')
            resp = client.get_secret_value(SecretId=secret_name)
            secret = resp.get('SecretString') or resp.get('SecretBinary')
            if secret:
                try:
                    return json.loads(secret)
                except Exception:
                    return secret
    except Exception:
        pass

    # 3) Azure Key Vault
    try:
        kv_name = os.getenv('AZURE_KEY_VAULT_NAME')
        secret_name = os.getenv('GOOGLE_CREDENTIALS_SECRET_NAME')
        if kv_name and secret_name:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            credential = DefaultAzureCredential()
            vault_url = f"https://{kv_name}.vault.azure.net"
            client = SecretClient(vault_url=vault_url, credential=credential)
            secret = client.get_secret(secret_name)
            val = secret.value
            try:
                return json.loads(val)
            except Exception:
                return val
    except Exception:
        pass

    # 4) Local file fallback
    try:
        if os.path.exists('credentials.json'):
            with open('credentials.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        traceback.print_exc()

    return None


def has_google_credentials():
    return get_google_credentials_json() is not None

def get_smtp_credentials():
    """Return SMTP credentials dict from one of these sources, in order:
    1. `SMTP_CREDENTIALS_JSON` env var (JSON string with keys: smtp_server, smtp_port, username, password)
    2. Individual env vars: SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
    3. AWS Secrets Manager secret named by `SMTP_CREDENTIALS_SECRET_NAME`
    4. Azure Key Vault secret named by `SMTP_CREDENTIALS_SECRET_NAME` in vault `AZURE_KEY_VAULT_NAME`
    5. Local file `.smtp_config` (JSON) in project root (not recommended for production)

    Returns dict with keys {smtp_server, smtp_port, username, password} or None.
    """
    # 1) JSON env var
    try:
        env_val = _from_env('SMTP_CREDENTIALS_JSON')
        if env_val and isinstance(env_val, dict):
            return env_val
    except Exception:
        pass

    # 2) Individual env vars
    try:
        server = os.getenv('SMTP_SERVER')
        port = os.getenv('SMTP_PORT')
        username = os.getenv('SMTP_USERNAME')
        password = os.getenv('SMTP_PASSWORD')

        if server and port and username and password:
            return {
                'smtp_server': server,
                'smtp_port': int(port),
                'username': username,
                'password': password
            }
    except Exception:
        pass

    # 3) AWS Secrets Manager
    try:
        secret_name = os.getenv('SMTP_CREDENTIALS_SECRET_NAME')
        if secret_name:
            import boto3
            client = boto3.client('secretsmanager')
            resp = client.get_secret_value(SecretId=secret_name)
            secret = resp.get('SecretString') or resp.get('SecretBinary')
            if secret:
                try:
                    creds = json.loads(secret)
                    if isinstance(creds, dict) and 'smtp_server' in creds:
                        return creds
                except Exception:
                    pass
    except Exception:
        pass

    # 4) Azure Key Vault
    try:
        kv_name = os.getenv('AZURE_KEY_VAULT_NAME')
        secret_name = os.getenv('SMTP_CREDENTIALS_SECRET_NAME')
        if kv_name and secret_name:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            credential = DefaultAzureCredential()
            vault_url = f"https://{kv_name}.vault.azure.net"
            client = SecretClient(vault_url=vault_url, credential=credential)
            secret = client.get_secret(secret_name)
            val = secret.value
            try:
                creds = json.loads(val)
                if isinstance(creds, dict) and 'smtp_server' in creds:
                    return creds
            except Exception:
                pass
    except Exception:
        pass

    # 5) Local file fallback (not recommended for production)
    try:
        if os.path.exists('.smtp_config'):
            with open('.smtp_config', 'r', encoding='utf-8') as f:
                creds = json.load(f)
                if isinstance(creds, dict) and 'smtp_server' in creds:
                    return creds
    except Exception:
        traceback.print_exc()

    return None


def has_smtp_credentials():
    return get_smtp_credentials() is not None