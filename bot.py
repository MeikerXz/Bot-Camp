import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import asyncio

# Carrega as variáveis do arquivo .env
load_dotenv()

# Obtém o token do bot e ID do canal das variáveis de ambiente
TOKEN = os.getenv('DISCORD_TOKEN')
CANAL_CADASTRO_ID = os.getenv('CANAL_CADASTROS_ID')
GUILD_ID = os.getenv('GUILD_ID')  # Adicione o ID do seu servidor de teste no .env

# Intents do bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guild_scheduled_events = True

# Inicializa o bot
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user.name}')
    print(f'ID do Bot: {bot.user.id}')
    print('------')

    # Carrega o cog de cadastro
    await bot.load_extension("cogs.cadastro.cadastro")

    # Sincroniza os comandos slash
    if GUILD_ID:
        guild = bot.get_guild(int(GUILD_ID))
        if guild:
            await bot.tree.sync(guild=guild)
            print(f"Comandos slash sincronizados com a guilda: {guild.name}")
        else:
            print("Guilda de teste não encontrada.")
    else:
        print("AVISO: GUILD_ID não configurado no .env. Os comandos slash podem levar um tempo para atualizar globalmente.")
        await bot.tree.sync()  # Sincroniza globalmente (pode levar alguns minutos)

    print("Comandos slash sincronizados!") # Adicionado para indicar que a sincronização ocorreu

# Verifica se o token existe
if not TOKEN:
    print("ERRO: Token do Discord não encontrado no arquivo .env")
    exit(1)

# Executa o bot
print("Iniciando o bot...")
print(".")
bot.run(TOKEN)