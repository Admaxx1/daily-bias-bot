import requests
import pandas as pd
from datetime import datetime, time, timezone
import discord
from discord.ext import tasks
import os

# -----------------------------
# CONFIG
# -----------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1445836334630699083   # Your channel ID

ASSETS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT", "PAXGUSDT"]

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

# -----------------------------
# FETCH DATA + CALCULATE BIAS
# -----------------------------
def get_data(symbol):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": "1d", "limit": 30}
    raw = requests.get(url, params=params).json()

    rows = []
    for k in raw:
        ts = datetime.fromtimestamp(k[0] / 1000)
        o, h, l, c = map(float, k[1:5])
        rows.append([ts, o, h, l, c])

    df = pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close"])
    df.set_index("Date", inplace=True)
    return df


def calculate_bias(df):
    C1 = df["Close"].iloc[-2]
    O1 = df["Open"].iloc[-2]
    H1 = df["High"].iloc[-2]
    L1 = df["Low"].iloc[-2]
    C2 = df["Close"].iloc[-3]

    if C1 > O1 and C1 > C2 and (H1 - C1) < (C1 - L1) * 0.4:
        return "STRONG BULLISH", "Strong close near the high, breaking above previous structure."
    elif C1 > O1 and C1 >= C2:
        return "BULLISH", "Closed above previous close and above the open."
    elif C1 < O1 and C1 < C2 and (C1 - L1) < (H1 - C1) * 0.4:
        return "STRONG BEARISH", "Closed weak near the low and below previous close."
    elif C1 < O1 and C1 <= C2:
        return "BEARISH", "Closed below both the open and previous close."
    else:
        return "NEUTRAL", "Indecisive structure with no clear directional pressure."


# -----------------------------
# DAILY MIDNIGHT UTC TASK
# -----------------------------
@tasks.loop(time=time(0, 0, tzinfo=timezone.utc))
async def send_daily_bias():
    channel = bot.get_channel(CHANNEL_ID)

    embed = discord.Embed(
        title="📊 Daily Crypto Market Bias",
        description="Automatically calculated at the daily bar close.\n\nAssets: BTC, ETH, BNB, XRP, SOL, PAXG",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Uptrick Daily Bias System")

    for asset in ASSETS:
        df = get_data(asset)
        bias, reason = calculate_bias(df)

        embed.add_field(
            name=f"**{asset}**",
            value=f"**Bias:** {bias}\n**Reason:** {reason}",
            inline=False
        )

    await channel.send(embed=embed)


# -----------------------------
# BOT READY
# -----------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Bot is online. Daily bias system activated. Next post at 00:00 UTC.")

    # Start loop safely once the bot's event loop exists
    if not send_daily_bias.is_running():
        bot.loop.create_task(send_daily_bias())


# -----------------------------
# RUN BOT
# -----------------------------
bot.run(TOKEN)
