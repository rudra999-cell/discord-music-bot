import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

queues = {}

def get_queue(guild_id):
    return queues.setdefault(guild_id, [])

ydl_opts = {
    "format": "bestaudio",
    "quiet": True,
    "noplaylist": True,
    "default_search": "ytsearch"
}

def extract(query):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            info = info["entries"][0]
        return info["url"], info.get("title", "Unknown")

async def play_next(ctx):
    queue = get_queue(ctx.guild.id)

    if not queue:
        return

    query = queue.pop(0)

    try:
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

    except Exception as e:
        await ctx.send(f"Error: {e}")
        await play_next(ctx)

@bot.command()
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send("Join VC first")

    if ctx.voice_client:
        await ctx.voice_client.move_to(ctx.author.voice.channel)
    else:
        await ctx.author.voice.channel.connect()

    await ctx.send("Joined VC")

@bot.command()
async def play(ctx, *, query):
    if not ctx.author.voice:
        return await ctx.send("Join VC first")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    queue = get_queue(ctx.guild.id)
    queue.append(query)

    await ctx.send(f"Added: {query}")

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped")

@bot.command()
async def pause(ctx):
    if ctx.voice_client:
        ctx.voice_client.pause()
        await ctx.send("Paused")

@bot.command()
async def resume(ctx):
    if ctx.voice_client:
        await ctx.voice_client.resume()
        await ctx.send("Resumed")

@bot.command()
async def queue(ctx):
    queue = get_queue(ctx.guild.id)

    if not queue:
        return await ctx.send("Queue empty")

    msg = "\n".join([f"{i+1}. {q}" for i, q in enumerate(queue)])
    await ctx.send(msg)

@bot.command()
async def clear(ctx):
    queues[ctx.guild.id] = []
    await ctx.send("Queue cleared")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        queues[ctx.guild.id] = []
        await ctx.send("Disconnected")

bot.run(os.getenv("TOKEN"))
