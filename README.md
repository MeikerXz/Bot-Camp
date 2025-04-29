# Bot de Cadastro para Campeonatos de Valorant

Este bot permite aos usuários se cadastrarem em campeonatos de Valorant através do Discord.

## Funcionalidades

- Cadastro interativo com perguntas em formato embed
- Seleção de campeonato via dropdown usando eventos do servidor
- Envio de todas as informações para um canal específico
- Sistema de timeout para evitar cadastros incompletos

## Configuração

1. Clone este repositório
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
   ```
   DISCORD_TOKEN=seu_token_aqui
   CANAL_CADASTROS_ID=id_do_canal_aqui
   ```
4. Execute o bot:
   ```
   python bot.py
   ```

## Comandos

- `!cadastrar`: Inicia o processo de cadastro para o campeonato

## Requisitos

- Python 3.8+
- discord.py 2.0+
- python-dotenv

## Personalização

Você pode personalizar as perguntas do cadastro editando a lista `PERGUNTAS_CADASTRO` no arquivo `cadastro.py`.