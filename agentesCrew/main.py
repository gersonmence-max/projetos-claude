from langchain_community.llms import Ollama
import time

llm = Ollama(model="llama2")

print("TESTANDO BUSCADOR DE EV CHARGERS")
print("-" * 50)

def teste_basico():
    print("\n[TESTE 1] Funcionalidade Basica")
    prompt = "Voce e um testador. Teste uma busca de carregadores em Sao Paulo. Responda em 2 linhas."
    resposta = llm.invoke(prompt)
    print(resposta)

def teste_localizacao():
    print("\n[TESTE 2] Precisao de Localizacao")
    prompt = "Teste a precisao de busca por proximidade. Responda em 2 linhas."
    resposta = llm.invoke(prompt)
    print(resposta)

if __name__ == "__main__":
    try:
        teste_basico()
        time.sleep(2)
        teste_localizacao()
        print("\nTestes concluidos!")
    except Exception as e:
        print(f"Erro: {e}")
        