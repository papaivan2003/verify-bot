import os
import threading
import discord
from discord import app_commands
from discord.ext import commands
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
VERIFY_CHANNEL_ID = int(os.getenv("VERIFY_CHANNEL_ID", "0"))
VERIFY_ROLE_ID = int(os.getenv("VERIFY_ROLE_ID", "0"))


# --- Мини-сервер, чтобы Render не усыплял бота ---
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass  # чтобы не засорять логи


def run_server():
    port = int(os.getenv("PORT", "10000"))
    print(f"Мини-сервер запущен на порту {port}")
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    server.serve_forever()


# --- Бот ---
intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.success,
        emoji=" ",
        custom_id="verify_button",
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        role = guild.get_role(VERIFY_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "Роль для верификации не найдена. Сообщи администратору.",
                ephemeral=True,
            )
            return

        if role in member.roles:
            await interaction.response.send_message(
                "Ты уже верифицирован!", ephemeral=True
            )
            return

        try:
            await member.add_roles(role, reason="Verification")
            await interaction.response.send_message(
                f"Готово! Тебе выдана роль **{role.name}**.", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "У бота нет прав выдать эту роль. Проверь, что роль бота стоит ВЫШЕ роли member.",
                ephemeral=True,
            )


@bot.event
async def on_ready():
    bot.add_view(VerifyView())
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Синхронизировано команд: {len(synced)}")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")
    print(f"Бот запущен как {bot.user}")


@bot.tree.command(
    name="setup_verify",
    description="Отправить сообщение верификации в канал",
    guild=discord.Object(id=GUILD_ID),
)
@app_commands.checks.has_permissions(administrator=True)
async def setup_verify(interaction: discord.Interaction):
    channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if channel is None:
        await interaction.response.send_message(
            "Канал не найден. Проверь VERIFY_CHANNEL_ID.", ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Верификация",
        description="Нажми кнопку ниже, чтобы получить доступ к серверу.",
        color=discord.Color.green(),
    )
    embed.set_image(url="https://i.imgur.com/8NYS33t.jpeg")
    embed.set_footer(text="Verification System")

    await channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message(
        f"Сообщение отправлено в {channel.mention}", ephemeral=True
    )


if __name__ == "__main__":
    # запускаем мини-сервер в отдельном потоке
    threading.Thread(target=run_server, daemon=True).start()
    # запускаем бота
    bot.run(TOKEN)
