# Guia de Deploy Multi-Clínicas (Software as a Service)

Este guia explica como você pode usar **este mesmo repositório** para vender e hospedar o sistema para dezenas ou centenas de clínicas diferentes, garantindo que os dados de cada uma fiquem isolados e seguros.

## O Conceito: Um Código, Várias Bolhas
Você **NÃO** precisa duplicar o código no GitHub para cada clínica que comprar o sistema.
A abordagem correta é o modelo **Multi-Instância**. 
- O código mestre fica no seu GitHub.
- Cada clínica ganha um **Projeto novo no Railway**.
- Cada projeto puxa o mesmo código, mas usa Bancos de Dados diferentes, Links diferentes e Variáveis diferentes.

A maior vantagem disso é a **Atualização Global**: Se você corrigir um bug ou criar uma funcionalidade nova no seu código, todas as clínicas receberão a atualização automaticamente na próxima vez que o Railway sincronizar o repositório.

---

## Passo a Passo: Como fazer o deploy para uma nova clínica

Sempre que você fechar contrato com uma nova clínica, siga estes passos exatos:

### Passo 1: Criar o Projeto no Railway
1. Acesse o seu painel do [Railway](https://railway.app/).
2. Clique em **New Project** (Novo Projeto).
3. Selecione **Deploy from GitHub repo**.
4. Escolha este exato repositório do Github (`agendamento-api`).
5. O Railway vai começar o deploy (é normal que ele falhe ou não funcione 100% no início, pois faltam as variáveis).

### Passo 2: Adicionar o Banco de Dados
1. Dentro do painel deste novo projeto da clínica, clique em **Create** (ou no botão de `+` no canto superior direito).
2. Selecione **Database** -> **Add PostgreSQL**.
3. O Railway vai subir um banco de dados novo, zerado e exclusivo para esta clínica.

### Passo 3: Configurar as Variáveis da Clínica
1. Clique no card da aplicação (agendamento-api) e vá até a aba **Variables**.
2. Preencha os seguintes dados para esta clínica específica:
   - `DATABASE_URL`: Pegue a URL do banco PostgreSQL que você acabou de criar.
   - `SECRET_KEY`: Gere uma senha longa e aleatória (nunca use a mesma para duas clínicas).
   - `ADMIN_USERNAME`: O login que o dono da clínica vai usar (ex: `admin_clinica`).
   - `ADMIN_PASSWORD`: A senha inicial da clínica.
   - Variáveis do WhatsApp da clínica:
     - `EVOLUTION_API_URL`
     - `EVOLUTION_API_KEY`
     - `EVOLUTION_INSTANCE` (nome da instância do WhatsApp desta clínica)

### Passo 4: Link Público (Domínio)
1. Ainda no card da aplicação, vá na aba **Settings**.
2. Na seção *Networking*, clique em **Generate Domain** (ou adicione um Domínio Customizado se a clínica tiver um site próprio).
3. Entregue este link para o dono da clínica junto com o `ADMIN_USERNAME` e `ADMIN_PASSWORD`.

---

## Bônus: Automação Absoluta (Templates de 1 Clique)

Se você não quiser fazer o Passo a Passo acima manualmente toda vez, você pode transformar o seu projeto atual em um **Template do Railway**.

1. Vá no projeto do Railway de uma clínica que já esteja funcionando perfeitamente.
2. Nas configurações (Settings) do projeto, clique em **Publish as Template**.
3. O Railway vai perguntar quais Variáveis o usuário precisará preencher (Marque como obrigatórias as senhas, nomes e URLs da Evolution).
4. O Railway vai gerar um **Link de Template Mágico**.

**Como usar o link mágico?**
Sempre que você ou seu cliente clicar nesse link, abrirá uma tela do Railway. A pessoa só precisa digitar a senha e o nome da instância do WhatsApp e apertar "Deploy". O Railway criará o banco de dados e fará tudo sozinho em 3 minutos!
