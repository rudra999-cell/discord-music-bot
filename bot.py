import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

queues = {}

def get_queue(gid):
    return queues.setdefault(gid, [])

ytdl = yt_dlp.YoutubeDL({
    "format": "bestaudio",
    "quiet": True,
    "default_search": "ytsearch",
    "noplaylist": True
})

def extract(query):
    info = ytdl.extract_info(query, download=False)
    if "entries" in info:
        info = info["entries"][0]
    return info["url"], info.get("title", "Unknown")

async def play_next(ctx):
    q = get_queue(ctx.guild.id)

    if not q:
        return

    query = q.pop(0)

    loop = asyncio.get_event_loop()
    url, title = await loop.run_in_executor(None, lambda: extract(query))

    source = discord.FFmpegPCMAudio(
        url,
        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        options="-vn"
    )

    ctx.voice_client.play(
        source,
        after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
    )

    await ctx.send(f"🎵 Now Playing: {title}")

async def ensure_vc(ctx):
    if not ctx.author.voice:
        return None

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    return ctx.voice_client

async def play_core(ctx, query):
    vc = await ensure_vc(ctx)
    if not vc:
        return await ctx.send("Join VC first")

    q = get_queue(ctx.guild.id)
    q.append(query)

    await ctx.send(f"Added: {query}")

    if not vc.is_playing():
        await play_next(ctx)

@bot.command()
async def play(ctx, *, query):
    await play_core(ctx, query)

@bot.command()
async def skip(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("Skipped")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        queues[ctx.guild.id] = []
        await ctx.send("Stopped")

@bot.command()
async def queue(ctx):
    q = get_queue(ctx.guild.id)
    if not q:
        return await ctx.send("Queue empty")

    await ctx.send("\n".join([f"{i+1}. {t}" for i, t in enumerate(q)]))

@bot.tree.command(name="play", description="Play a song")
async def play_slash(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    ctx = await bot.get_context(interaction)
    await play_core(ctx, query)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Ready {bot.user}")

bot.run(os.getenv("TOKEN"))