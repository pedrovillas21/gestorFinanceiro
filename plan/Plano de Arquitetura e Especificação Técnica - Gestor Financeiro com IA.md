# **Plano de Arquitetura e Especificação Técnica: Gestor Financeiro com IA**

Documento de Visão de Produto, Regras de Negócio e Roadmap de Desenvolvimento

## ---

**1\. Visão Geral do Sistema**

O **Gestor Financeiro Inteligente** é uma plataforma omnicanal que permite o gerenciamento passivo e ágil de finanças pessoais via mensagens de texto e áudio (Telegram/WhatsApp), integrando um dashboard web de alta performance para análise de investimentos, simulações financeiras e monitoramento de ativos do mercado em tempo real.

## **2\. Escolha das Tecnologias & Justificativa Técnica**

### **Back-end: Python (FastAPI)**

**Por que Python é a melhor escolha para este projeto?**

* **Nativo para Inteligência Artificial:** Suporte de primeira classe para a SDK oficial do Gemini (google-genai) e manipulação nativa de fluxos de dados de áudio.  
* **Ecossistema de Dados e Finanças:** Bibliotecas consolidada para cálculo financeiro, processamento de planilhas (pandas, openpyxl) e integração com APIs de mercado financeiro (yfinance, Braapi).  
* **Performance com FastAPI:** Framework assíncrono de altíssima performance, ideal para lidar com webhooks de bots (Telegram/WhatsApp) sem bloquear threads de execução.

### **Front-end: TypeScript \+ React / Next.js \+ Tailwind CSS 4.0**

* **TypeScript:** Garante tipagem estática rigorosa para dados financeiros, evitando erros numéricos e garantindo previsibilidade.  
* **Tailwind CSS 4.0:** Utiliza a nova engine pré-compilada em Rust (Oxide), garantindo compilação ultra-rápida, consumo de memória reduzido e sintaxe simplificada sem a necessidade de tailwind.config.js complexo.  
* **Componentes Visuais & Gráficos:** Integração nativa com bibliotecas como Recharts ou Tremor para dashboards interativos de alta fidelidade visual.

## **3\. Arquitetura da Solução**

| Camada | Tecnologia / Ferramenta | Responsabilidade |
| :---- | :---- | :---- |
| **Canais de Entrada** | Telegram Bot API / WhatsApp Cloud API | Recepção de mensagens de texto e arquivos de áudio (.ogg). |
| **Motor de IA** | Google Gemini 2.5 Flash | Processamento direto de áudio/texto e extração de JSON estruturado com response\_schema. |
| **Back-end API** | Python (FastAPI \+ Pydantic) | Gerenciamento de regras de negócio, webhooks, autenticação e integração com APIs de mercado. |
| **Banco de Dados** | PostgreSQL / Supabase (SQLAlchemy) | Armazenamento de transações, carteira de investimentos e categorias. |
| **Front-end Web** | TypeScript \+ React (Next.js) \+ Tailwind 4.0 | Dashboard interativo, visualização de planilhas, simuladores e cotações em tempo real. |
| **Provedor de Mercado** | Braapi / Yahoo Finance API | Consumo de cotações de ações (B3 / Mercado Internacional) em tempo real. |

## **4\. Regras de Negócio Fundamentais**

### **4.1. Processamento via Bot de Mensagens**

* **Entrada Multimodal:** O sistema deve aceitar comandos de voz e texto sem formatação pré-definida.  
* **Classificação Automática:** A IA deve identificar o tipo (Receita/Despesa), valor, categoria (Alimentação, Transporte, Moradia, Lazer, etc.) e meio de pagamento.  
* **Confirmação Instantânea:** O bot deve responder com o resumo formatado da transação e o saldo atualizado da categoria.  
* **Fallback de Incerteza:** Se a IA não identificar com clareza o valor ou tipo, o bot deve solicitar confirmação do usuário com botões de opção.

### **4.2. Módulo de Investimentos e Cotações**

* **Atualização em Tempo Real:** Ações e fundos imobiliários registrados pelo usuário devem ter seus preços atualizados via API financeira.  
* **Cálculo de Preço Médio e Rentabilidade:** O sistema deve calcular automaticamente a rentabilidade total e o ganho de capital com base nos aportes realizados.

### **4.3. Calculadora de Investimentos (Juros Compostos)**

* Permitir simulações alterando: Aporte Inicial, Aporte Mensal, Taxa de Juros (Anual/Mensal) e Período (Anos/Meses).  
* Gerar gráfico comparativo de Valor Total Investido vs. Juros Acumulados.

## **5\. Roadmap de Desenvolvimento (Fases)**

### **Fase 1: Core Backend & Bot Telegram (Semanas 1-2)**

* Configuração do ambiente Python (FastAPI, Pydantic, SQLAlchemy).  
* Integração da SDK do Gemini 2.5 Flash com suporte a Structured Outputs e áudio.  
* Criação do Webhook do Bot do Telegram para captura de voz/texto e persistência no banco de dados.

### **Fase 2: Dashboard Web & Gestão Financeira (Semanas 3-4)**

* Setup do projeto Front-end (Next.js/React \+ TypeScript \+ Tailwind 4.0).  
* Construção das telas de Dashboard: resumo de receitas/despesas, visão de tabela estilo planilha e filtros por período.  
* Exportação e importação de planilhas (CSV / XLSX).

### **Fase 3: Módulo de Investimentos & Cotações em Tempo Real (Semanas 5-6)**

* Integração com API de mercado de ações (Braapi / yfinance).  
* Criação da tabela interativa da carteira com atualização ao vivo.  
* Implementação da Calculadora Interativa de Juros Compostos e Simulações.

**Nota de Arquitetura:** A escolha do stack Python no back-end e TypeScript/Tailwind 4.0 no front-end garante a separação ideal de responsabilidades: alto desempenho em processamento de dados e IA no servidor, alinhado a uma experiência de usuário moderna, rápida e responsiva no navegador.