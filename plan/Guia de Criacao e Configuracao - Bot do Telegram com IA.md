# **Guia de Implementação e Configuração: Bot do Telegram com IA**

Manual Operacional de Provisionamento, Webhooks, Segurança e Integração para o Gestor Financeiro

## ---

**1\. Visão Geral da Solução do Bot**

Este documento especifica o plano de criação, provisionamento e integração do **Bot do Telegram** para o Gestor Financeiro com IA. O bot funciona como o principal canal de entrada multimodal, permitindo a usuários autenticados o envio de áudios (.ogg) e textos para cadastro imediato de receitas e despesas.

## **2\. Etapas de Provisionamento no Telegram**

### **2.1. Registro com o @BotFather**

1. Abrir a aplicação do Telegram e buscar pelo usuário oficial @BotFather.  
2. Executar o comando /newbot.  
3. **Nome de Exibição:** Definir como Gestor Financeiro IA (ou nome de preferência).  
4. **Username do Bot:** Definir um nome único terminado em bot (ex: meu\_gestor\_financeiro\_bot).  
5. **Armazenamento do Token:** Copiar o HTTP API Token gerado (ex: 7123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ) e armazenar na variável de ambiente TELEGRAM\_BOT\_TOKEN.

### **2.2. Customização e Menu de Comandos**

* /setdescription — Mensagem inicial exibida antes de iniciar o bot: *"Seu assistente financeiro pessoal com IA. Envie áudios ou textos para gerenciar suas finanças."*  
* /setcommands — Configurar o menu nativo de comandos:  
  `start - Conectar ou autenticar sua conta Web via Deep Link`  
  `ajuda - Instruções de como registrar receitas e despesas por áudio ou texto`  
  `saldo - Exibir resumo do saldo e despesas do mês atual`  
        

## **3\. Arquitetura de Comunicação e Webhook**

| Ambiente | Modo de Comunicação | Mecanismo / Ferramenta |
| :---- | :---- | :---- |
| **Desenvolvimento Local** | Long Polling ou Tunneling | python-telegram-bot (Polling) ou Ngrok / Cloudflare Tunnels apontando para FastAPI. |
| **Produção (Nuvem)** | Webhook HTTPS (Push) | Endpoint FastAPI registrado via Telegram Webhook API (/setWebhook). |

### **3.1. Registro do Endpoint de Webhook no FastAPI**

O registro é feito através de uma requisição HTTP enviada à API do Telegram:

`POST https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook`  
`Header: Content-Type: application/json`

`{`  
  `"url": "https://api.seu-dominio.com/api/v1/telegram/webhook",`  
  `"secret_token": "TOKEN_SECRETO_PARA_VALIDAR_ASSINATURA"`  
`}`


## **4\. Fluxo de Execução e Tratamento de Mensagens**

### **4.1. Recebimento e Validação de Usuário**

1. O Telegram envia um payload JSON via Webhook contendo chat\_id e os dados da mensagem.  
2. O FastAPI consulta o banco de dados PostgreSQL para verificar se existe um usuário com aquele telegram\_chat\_id.  
3. **Se não encontrado:** O bot recusa o processamento e envia o link de Deep Link da aplicação Web para cadastro/vinculação.  
4. **Se encontrado:** O pipeline segue para a etapa de processamento de mídia.

### **4.2. Processamento de Áudio e Chamada da IA**

1. O backend obtém o file\_id do arquivo de áudio enviado pelo Telegram.  
2. Faz o download do arquivo .ogg diretamente através da API de arquivos do Telegram (https://api.telegram.org/file/bot{TOKEN}/{file\_path}).  
3. Envia o buffer de áudio para o pipeline da **Cascata do Gemini** (Gemini Flash Recente → Gemini 2.5 Flash).  
4. A IA retorna o JSON estruturado com tipo, valor, categoria e metodo\_pagamento.  
5. A transação é persistida com o user\_id do usuário e uma mensagem de confirmação é enviada de volta ao chat.

## **5\. Checklist de Requisitos e Dependências**

* \[ \] Conta no Telegram ativada e acesso ao @BotFather.  
* \[ \] Credencial de API do Gemini configurada (GEMINI\_API\_KEY).  
* \[ \] Pacotes Python instalados: fastapi, httpx, python-dotenv, pydantic, sqlalchemy.  
* \[ \] Certificado SSL Válido / HTTPS no servidor back-end em produção.