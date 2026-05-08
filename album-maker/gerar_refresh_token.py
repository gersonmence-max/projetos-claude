#!/usr/bin/env python3
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def gerar_refresh_token(credentials_json_path):
    try:
        with open(credentials_json_path, 'r') as f:
            client_config = json.load(f)

        print("📌 Iniciando autenticação OAuth...")
        print("⏳ Uma janela do navegador vai abrir em segundos...\n")

        flow = InstalledAppFlow.from_client_config(
            client_config,
            scopes=SCOPES
        )

        creds = flow.run_local_server(port=8080)
        refresh_token = creds.refresh_token

        if refresh_token:
            print("\n" + "="*60)
            print("✅ SUCESSO! Refresh Token gerado:")
            print("="*60)
            print(f"\n🔑 REFRESH TOKEN:\n{refresh_token}\n")
            print("="*60)

            with open('refresh_token.txt', 'w') as f:
                f.write(refresh_token)
            print("✅ Token salvo em 'refresh_token.txt'")
        else:
            print("❌ Erro: Não foi possível obter o Refresh Token")
            return False

        return True

    except FileNotFoundError:
        print(f"❌ Erro: Arquivo 'credentials.json' não encontrado!")
        return False
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False

if __name__ == "__main__":
    credentials_path = "credentials.json"
    if os.path.exists(credentials_path):
        gerar_refresh_token(credentials_path)
    else:
        print("❌ Arquivo 'credentials.json' não encontrado nesta pasta!")