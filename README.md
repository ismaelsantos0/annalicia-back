# Guia de Deploy e Configuração - Sistema de Agendamentos

Este documento contém todas as instruções necessárias para hospedar e configurar a sua API de agendamentos no Railway, bem como a integração com o WhatsApp (Evolution API) e dicas de automação de deploy.

---

## 1. Variáveis de Ambiente no Railway (Environment Variables)

Para que o backend funcione corretamente no Railway, você deve configurar as seguintes variáveis na aba **Variables** do seu serviço:

### Banco de Dados
- **`DATABASE_URL`**: A URL de conexão com o banco de dados PostgreSQL. (O próprio Railway fornece isso se você adicionar um banco de dados PostgreSQL ao seu projeto. Formato esperado: `postgresql+asyncpg://usuario:senha@host:porta/banco`).

### Segurança do Sistema
- **`SECRET_KEY`**: Uma senha longa e aleatória (mínimo de 32 caracteres) usada para criptografar os tokens de login (JWT). Não compartilhe com ninguém.
- **`ALGORITHM`**: Geralmente configurado como `HS256`.
- **`ACCESS_TOKEN_EXPIRE_MINUTES`**: Tempo em minutos que o login do admin dura (ex: `480` para 8 horas).

### Configurações Iniciais do Admin
- **`ADMIN_USERNAME`**: Seu login inicial para o painel (ex: `master` ou `admin`).
- **`ADMIN_PASSWORD`**: A senha para esse primeiro login (você pode mudá-la depois).

### Integração WhatsApp (Evolution API)
- **`EVOLUTION_API_URL`**: A URL base de onde a sua Evolution API está rodando (ex: `https://whatsapp.suaempresa.com`).
- **`EVOLUTION_API_KEY`**: A chave global (Global API Key) da Evolution API para autorizar os envios.
- **`EVOLUTION_INSTANCE`**: O nome exato da instância de WhatsApp (o celular conectado) que fará os disparos (ex: `AgendamentosBot`).
- **`ADMIN_PHONE`**: (Opcional) Seu número de telefone com DDI e DDD (ex: `5511999999999`) para receber notificações de erros caso algo falhe.

---

## 2. Evolution API e Redis

O **Evolution API** é a ponte que permite que nosso sistema envie mensagens pelo WhatsApp sem precisar de celular físico ligado na tomada 24h por dia. 

Para hospedar o Evolution API (seja no próprio Railway ou em uma VPS), você geralmente precisa subir 3 componentes:
1. **Evolution API** (A aplicação Node.js)
2. **PostgreSQL** (Para salvar contatos e configurações da API)
3. **Redis** (Banco de dados em memória)

### O papel do Redis
Nossa API de Agendamentos **NÃO** precisa do Redis diretamente (nós usamos agendamentos assíncronos direto na memória do Python). No entanto, **o Evolution API exige o Redis** para funcionar perfeitamente. O Redis é utilizado pelo Evolution para:
- Gerenciar as filas de mensagens do WhatsApp (garantindo que se você mandar 100 mensagens de uma vez, elas sejam entregues aos poucos, sem tomar ban do WhatsApp).
- Manter a sessão do seu QR Code ativa de forma rápida.
- Fazer cache de conversas.

**Como criar o Redis no Railway:**
1. No painel do seu projeto no Railway, clique em `New` -> `Database` -> `Add Redis`.
2. O Railway vai criar o Redis imediatamente. Vá nas variáveis desse Redis criado para pegar a `REDIS_URL`.
3. Copie essa URL e coloque nas variáveis da sua Evolution API.

---

## 3. Automação de Deploy (Deploy em um Clique)

No momento, toda vez que você altera o código no Github, o Railway faz o deploy automaticamente. Mas, caso você queira replicar o sistema, criar ambientes de teste, ou vender a solução como um **Template de 1 clique** para outras clínicas, você pode usar o **Railway Templates**.

### Como criar o Deploy de 1 Clique:
1. No projeto atual do Railway (que já está configurado e rodando), vá em **Settings** (Configurações) do projeto.
2. Procure a opção **"Publish as Template"** ou **"Share Template"**.
3. O Railway vai gerar automaticamente um arquivo `railway.json` baseado na sua configuração atual (incluindo o banco PostgreSQL atrelado à API).
4. **Link Mágico:** Ele vai gerar um link público. Qualquer pessoa que clicar nesse link verá uma tela bonita escrito "Fazer Deploy". O Railway criará o Banco de Dados, clonará o repositório do Github e pedirá apenas que a pessoa preencha as Variáveis de Ambiente vazias (como `SECRET_KEY`, `EVOLUTION_API_KEY`, etc.).

### Arquivo `railway.toml`
Se você quiser forçar o Railway a sempre rodar comandos específicos, você pode criar um arquivo chamado `railway.toml` na raiz do seu projeto Github. Exemplo:

```toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
restartPolicyType = "ON_FAILURE"
```
Ao enviar isso pro Github, o Railway nunca mais vai "tentar adivinhar" como ligar o projeto, ele seguirá essa receita 100% das vezes, evitando qualquer erro de build.

---
*Dúvidas adicionais? Consulte a documentação oficial do Railway e da Evolution API v2.*

---

## 4. Registro de Atualizações Recentes (Changelog)

### Melhorias no Agendamento Público e Painel
- **Modo Profissional Solo**: Novo assistente (Onboarding Wizard) para identificar automaticamente se a conta é de uma Clínica ou de um Profissional Solo. 
- Se for **Solo**, o sistema ajusta a nomenclatura do painel de controle (Oculta abas como "Novo Profissional") e gera links automáticos de atendimento.
- **Cabeçalho Premium**: O cabeçalho do `AdminDashboard` e do `SchedulingPage` foram redesenhados com um design de luxo (*Glassmorphism*, Iniciais Dinâmicas, Avatares Coloridos).
- **Caixa de Especialista Inteligente**: Na tela de agendamento público (`SchedulingPage`), se a clínica possui apenas 1 profissional (Solo), a caixa de seleção com a seta flutuante é convertida automaticamente num **"Cartão de Perfil" estático**, evitando que o paciente tente selecionar outras opções inexistentes.

### Correções de Segurança e API
- **Links Personalizados SaaS**: Adicionada chave global de segurança `allow_custom_links` ao banco de dados `configuracoes_clinica`, permitindo que apenas o usuário `master` autorize a geração de links independentes.
- **Lockdown Visual**: A visualização de configurações da empresa (CEP, Rua, Nome) para usuários recepcionistas/clínica é estritamente **Somente Leitura**, com as caixas de texto bloqueadas nativamente para impedir edições indevidas.
- **Liberação Pública de Configurações**: A rota `/settings` agora tem suporte unificado: acessos `GET` desautenticados são permitidos para abastecer a tela de agendamento do paciente, enquanto acessos `PUT` continuam seguros com o Token JWT.
