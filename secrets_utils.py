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
    1. `GOOGLE_CREDENTIALS_JSON` env var (JSON string)
    2. AWS Secrets Manager secret named by `GOOGLE_CREDENTIALS_SECRET_NAME`
    3. Azure Key Vault secret named by `GOOGLE_CREDENTIALS_SECRET_NAME` in vault `AZURE_KEY_VAULT_NAME`
    4. Local file `credentials.json` in project root

    Returns dict or None.
    """
    # 1) Env var
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
