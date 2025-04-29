import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime
import os  # Importe a biblioteca 'os' aqui

class CadastroManager:
    def __init__(self, bot):
        self.bot = bot
        self.cadastros_ativos = {}

    def iniciar_cadastro(self, user_id):
        self.cadastros_ativos[user_id] = {}
        return self.cadastros_ativos[user_id]

    def adicionar_resposta(self, user_id, campo, valor):
        if user_id in self.cadastros_ativos:
            self.cadastros_ativos[user_id][campo] = valor
            return True
        return False

    def finalizar_cadastro(self, user_id):
        if user_id in self.cadastros_ativos:
            dados = self.cadastros_ativos[user_id]
            del self.cadastros_ativos[user_id]
            return dados
        return None

    def esta_em_cadastro(self, user_id):
        return user_id in self.cadastros_ativos

class EventoSelect(discord.ui.Select):
    def __init__(self, user_id, eventos):
        self.user_id = user_id
        options = []
        for evento in eventos:
            inicio = evento.start_time.strftime("%d/%m/%Y às %H:%M")
            desc = f"Começa em {inicio}"
            if evento.description:
                desc = f"{desc} - {evento.description[:50]}..."
            options.append(
                discord.SelectOption(
                    label=evento.name[:100],
                    value=str(evento.id),
                    description=desc[:100]
                )
            )
        super().__init__(placeholder="Selecione o campeonato", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        evento_nome = None
        evento_id = self.values[0]
        for option in self.options:
            if option.value == evento_id:
                evento_nome = option.label
                break
        self.view.cadastro_cog.cadastro_manager.adicionar_resposta(self.user_id, "campeonato_id", evento_id)
        self.view.cadastro_cog.cadastro_manager.adicionar_resposta(self.user_id, "campeonato_nome", evento_nome)
        embed_confirmacao = discord.Embed(
            title=self.view.embed_titulo_confirmacao,
            description=f"✅ Você selecionou: **{evento_nome}**\n{self.view.embed_descricao_confirmacao}",
            color=self.view.embed_cor_confirmacao
        )
        await interaction.response.send_message(embed=embed_confirmacao, ephemeral=True)
        self.view.valor_selecionado = evento_id
        self.view.nome_selecionado = evento_nome
        self.view.stop()

class EventoView(discord.ui.View):
    def __init__(self, user_id, eventos, cadastro_cog,
                 embed_cor_confirmacao=discord.Color.green(),
                 embed_titulo_confirmacao="Campeonato Selecionado",
                 embed_descricao_confirmacao="",
                 timeout=180):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.eventos = eventos
        self.cadastro_cog = cadastro_cog
        self.valor_selecionado = None
        self.nome_selecionado = None
        self.add_item(EventoSelect(user_id, eventos))
        self.embed_cor_confirmacao = embed_cor_confirmacao
        self.embed_titulo_confirmacao = embed_titulo_confirmacao
        self.embed_descricao_confirmacao = embed_descricao_confirmacao

class CadastroComandos(commands.Cog):
    def __init__(self, bot, canal_cadastros_id): # Adicionado canal_cadastros_id
        self.bot = bot
        self.cadastro_manager = CadastroManager(bot)
        self.canal_cadastros_id = canal_cadastros_id # Armazenando o ID do canal

    @app_commands.command(name="iniciar", description="Inicia o processo de cadastro para um campeonato.")
    async def iniciar_cadastro_slash(self, interaction: discord.Interaction):
        await self.iniciar_cadastro(interaction) # Chamando a função iniciar_cadastro

    async def iniciar_cadastro(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        if self.cadastro_manager.esta_em_cadastro(user_id):
            await interaction.response.send_message("Você já está com um cadastro em andamento. Complete-o antes de iniciar outro.", ephemeral=True)
            return

        self.cadastro_manager.iniciar_cadastro(user_id)

        embed_inicial = discord.Embed(
            title="📝 Cadastro para Campeonato de Valorant",
            description="🚀 Vamos registrar seu time para o campeonato. Responda cada pergunta no chat.",
            color=discord.Color.from_rgb(54, 57, 63) # Cor de fundo do Discord
        )
        await interaction.response.send_message(embed=embed_inicial, ephemeral=True)
        respostas = {}
        for pergunta_info in PERGUNTAS_CADASTRO:
            campo = pergunta_info["campo"]
            texto_pergunta = pergunta_info["pergunta"]

            embed_pergunta = discord.Embed(
                title=f"❓ Pergunta: {campo.replace('_', ' ').title()}",
                description=texto_pergunta,
                color=discord.Color.from_rgb(100, 100, 250), # Roxo
            )
            pergunta_message = await interaction.followup.send(embed=embed_pergunta, ephemeral=True) # Armazena a mensagem
            def check(message):
                return message.author.id == user_id and message.channel.id == interaction.channel_id

            try:
                resposta = await self.bot.wait_for('message', check=check, timeout=120)
                respostas[campo] = resposta.content
                self.cadastro_manager.adicionar_resposta(user_id, campo, resposta.content)
                await resposta.delete() # Apaga a mensagem do usuário
                await pergunta_message.delete() # Apaga o embed de pergunta
            except asyncio.TimeoutError:
                self.cadastro_manager.finalizar_cadastro(user_id)
                embed_timeout = discord.Embed(
                    title="❌ Cadastro Cancelado",
                    description="⏰ Tempo esgotado. O cadastro foi cancelado.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed_timeout, ephemeral=True)
                return

        eventos = []
        try:
            eventos = await interaction.guild.fetch_scheduled_events()
            agora = discord.utils.utcnow()
            eventos_ativos = [
                evento for evento in eventos
                if evento.start_time > agora or (evento.end_time and evento.end_time > agora)
            ]
            if not eventos_ativos:
                eventos = []
            else:
                eventos = eventos_ativos
        except Exception as e:
            await interaction.followup.send(f"Não foi possível carregar os eventos do servidor.", ephemeral=True)
            eventos = []

        if eventos:
            embed_campeonato = discord.Embed(
                title="🏆 Em qual Camp o seu time está se inscrevendo?",
                description="Selecione um dos campeonatos disponíveis no menu abaixo:",
                color=discord.Color.gold()
            )
            view = EventoView(user_id, eventos, self,
                                        embed_cor_confirmacao=discord.Color.from_rgb(148, 103, 189),
                                        embed_titulo_confirmacao="Inscrição no Campeonato",
                                        embed_descricao_confirmacao="Por favor, escolha o campeonato desejado."
                                        )
            await interaction.followup.send(embed=embed_campeonato, view=view, ephemeral=True)
            await view.wait()
            if view.valor_selecionado is None:
                self.cadastro_manager.finalizar_cadastro(user_id)
                embed_timeout = discord.Embed(
                    title="❌ Cadastro Cancelado",
                    description="⏰ Tempo esgotado ou seleção cancelada. O cadastro foi cancelado.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed_timeout, ephemeral=True)
                return
            dados_cadastro = self.cadastro_manager.finalizar_cadastro(user_id)
            dados_cadastro["campeonato_nome"] = view.nome_selecionado
        else:
            dados_cadastro = self.cadastro_manager.finalizar_cadastro(user_id)

        embed_revisao = discord.Embed(
            title="👀 Revise seu Cadastro",
            description="Por favor, revise os dados abaixo antes de confirmar o envio:",
            color=discord.Color.from_rgb(0, 123, 255), # Azul
        )
        nome_campos = {
            "nick_capitao": "Nick do Capitão (Discord)",
            "id_capitao": "ID do Capitão (Valorant)",
            "elo_competidores": "Elo dos Competidores",
            "nome_time": "Nome do Time",
        }
        if eventos:
            nome_campos["campeonato_nome"] = "Campeonato Selecionado"
        for campo, valor in dados_cadastro.items():
            nome_exibicao = nome_campos.get(campo, campo.capitalize())
            embed_revisao.add_field(name=nome_exibicao, value=valor, inline=False)

        embed_revisao.set_footer(text=f"Revisar Cadastro de: {interaction.user.name} • ID: {interaction.user.id}")
        embed_revisao.timestamp = discord.utils.utcnow()
        if interaction.user.avatar:
            embed_revisao.set_thumbnail(url=interaction.user.avatar.url)
        embed_revisao.set_author(name="Nome do Seu Bot", icon_url="https://seu-logo.com/logo.png") # Substitua pela URL do logo do seu bot

        class ConfirmacaoView(discord.ui.View):
            def __init__(self, cadastro_cog, dados_cadastro, interaction, timeout=180):
                super().__init__(timeout=timeout)
                self.cadastro_cog = cadastro_cog
                self.dados_cadastro = dados_cadastro
                self.confirmado = None
                self.interaction = interaction # Passando a interaction para poder responder depois

            @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.green)
            async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.confirmado = True
                await interaction.response.send_message("Cadastro confirmado e enviado para o canal de anúncios!", ephemeral=True)
                self.stop()

            @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.red)
            async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.confirmado = False
                await interaction.response.send_message("Cadastro cancelado.", ephemeral=True)
                self.stop()
                
            async def on_timeout(self):
                self.confirmado = False
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)

        confirmacao_view = ConfirmacaoView(self, dados_cadastro, interaction) # Passando a interaction
        confirmacao_view.message = await interaction.followup.send(embed=embed_revisao, view=confirmacao_view)
        await confirmacao_view.wait()
        if confirmacao_view.confirmado is None:
            await interaction.followup.send("⏰ Tempo para confirmação esgotado, cadastro cancelado.", ephemeral=True)
            return

        if confirmacao_view.confirmado == False:
            return

        embed_final = discord.Embed( # Defina embed_final aqui
            title=f"🎉 Cadastro Completo - {dados_cadastro.get('nome_time', 'Time')}",
            description="✅ Cadastro concluído com sucesso!",
            color=discord.Color.from_rgb(220, 53, 69), # Vermelho
        )
        nome_campos = {
            "nick_capitao": "Nick do Capitão (Discord)",
            "id_capitao": "ID do Capitão (Valorant)",
            "elo_competidores": "Elo dos Competidores",
            "nome_time": "Nome do Time",
        }
        if eventos:
            nome_campos["campeonato_nome"] = "Campeonato Selecionado"
        for campo, valor in dados_cadastro.items():
            nome_exibicao = nome_campos.get(campo, campo.capitalize())
            embed_final.add_field(name=nome_exibicao, value=valor, inline=False)

        embed_final.set_footer(text=f"Registrado por: {interaction.user.name} • ID: {interaction.user.id}")
        embed_final.timestamp = discord.utils.utcnow()
        if interaction.user.avatar:
            embed_final.set_thumbnail(url=interaction.user.avatar.url)
        embed_final.set_author(name="Nome do Seu Bot", icon_url="https://seu-logo.com/logo.png") # Substitua pela URL do logo do seu bot

        # Adicionando o botão de revogar ao embed final
        class FinalView(discord.ui.View):
            def __init__(self, user_id, cadastro_cog, timeout=180):
                super().__init__(timeout=timeout)
                self.user_id = user_id
                self.cadastro_cog = cadastro_cog

            @discord.ui.button(label="↩️ Revogar Inscrição", style=discord.ButtonStyle.grey)
            async def revogar(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Lógica para revogar a inscrição
                # Você precisa acessar o CadastroManager para remover os dados do usuário
                self.cadastro_cog.cadastro_manager.finalizar_cadastro(self.user_id)
                await interaction.response.send_message("Sua inscrição foi revogada.", ephemeral=True)
                # Remover a mensagem do embed final após a revogação
                await interaction.message.delete()

            async def on_timeout(self):
                await self.message.delete()

        final_view = FinalView(interaction.user.id, self)
        final_message = await interaction.followup.send(embed=embed_final, view=final_view) # Armazena a mensagem para deletar depois
        final_view.message = final_message
        await asyncio.sleep(5)
        await final_message.delete()
        if self.canal_cadastros_id: # Usando o ID do canal armazenado na Cog
            try:
                canal_cadastros = self.bot.get_channel(self.canal_cadastros_id)
                if canal_cadastros:
                    await canal_cadastros.send(embed=embed_final, view=final_view) # Envia o embed com o botão de revogar
                else:
                    print(f"Canal de cadastros com ID {self.canal_cadastros_id} não encontrado")
            except Exception as e:
                print(f"Erro ao enviar cadastro para o canal: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        # Verifique se o bot é mencionado usando message.mentions
        if self.bot.user in message.mentions:
            # Remover a menção do bot para evitar problemas com o comando
            content = message.content.replace(f"<@{self.bot.user.id}>", "").strip()
            # Verificar se a mensagem é "/cadastro" ou apenas menção
            if content == "/cadastro" or content == "":
                # Simular um interaction para reaproveitar a lógica do comando
                interaction = await self.fake_interaction(message)
                await self.iniciar_cadastro(interaction)

    async def fake_interaction(self, message):
        """
        Função para simular um interaction a partir de uma mensagem.
        """
        class FakeInteraction:
            def __init__(self, message):
                self.message = message
                self.author = message.author
                self.channel = message.channel
                self.guild = message.guild

            async def response(self, *args, **kwargs):
                await message.channel.send(*args, **kwargs)

            async def followup(self, *args, **kwargs):
                return await message.channel.send(*args, **kwargs)
        return FakeInteraction(message)

# Variável global para armazenar as perguntas do cadastro
PERGUNTAS_CADASTRO = [
    {"campo": "nick_capitao", "pergunta": "Qual é o nick do capitão no Discord? 🎮"},
    {"campo": "id_capitao", "pergunta": "Qual é o ID do capitão no Valorant? 🆔"},
    {"campo": "elo_competidores", "pergunta": "Qual é o elo dos competidores? 🏅"},
    {"campo": "nome_time", "pergunta": "Qual é o nome do time?  팀"}
]

async def setup(bot):
    # Instanciando a Cog e passando o ID do canal
    canal_id = int(os.getenv('CANAL_CADASTROS_ID', 0))  # Pega do .env e converte para int
    await bot.add_cog(CadastroComandos(bot, canal_cadastros_id=canal_id))