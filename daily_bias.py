
import requests
import pandas as pd
import mplfinance as mpf
from datetime import datetime
import discord
from discord.ext import tasks
import os

# -----------------------------
# CONFIG
# -----------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1445836334630699083  # your channel ID

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

# -----------------------------
# CUSTOM CHART STYLE
# -----------------------------
# Bullish = light blue
# Bearish = white
my_style = mpf.make_mpf_style(
    base_mpf_style="nightclouds",
    facecolor="black",
    edgecolor="black",
    gridcolor="black",
    gridstyle="-",
    y_on_right=False,
)

my_colors = mpf.make_marketcolors(
    up="lightblue",
    down="white",
    wick={"up": "lightblue", "down": "white"},
    edge={"up": "lightblue", "down": "white"},
    volume={"up": "lightblue", "down": "white"},
)

my_style = mpf.make_mpf_style(
    marketcolors=my_colors,
    facecolor="black",
    edgecolor="black",
    figcolor="black",
    gridcolor="black",
    gridstyle="-"
)

# -----------------------------
# GENERATE CHART + BIAS
# -----------------------------
def generate_data_and_bias():

    # Fetch OHLC (30 candles)
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 30}
    raw = requests.get(url, params=params).json()

    rows = []
    for k in raw:
        ts = datetime.fromtimestamp(k[0] / 1000)
        o, h, l, c = map(float, k[1:5])
        rows.append([ts, o, h, l, c])

    df = pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close"])
    df.set_index("Date", inplace=True)

    # Save chart (pure black background)
    mpf.plot(
        df,
        type="candle",
        style=my_style,
        savefig="btc_daily.png",
        tight_layout=True,
        figsize=(12, 8)
    )

    # -----------------------------
    # Bias calculation
    # -----------------------------
    C1 = df["Close"].iloc[-2]
    O1 = df["Open"].iloc[-2]
    H1 = df["High"].iloc[-2]
    L1 = df["Low"].iloc[-2]

    C2 = df["Close"].iloc[-3]

    if C1 > O1 and C1 > C2 and (H1 - C1) < (C1 - L1) * 0.4:
        bias = "STRONG BULLISH"
        reason = "Strong close near the high, breaking above previous structure."
    elif C1 > O1 and C1 >= C2:
        bias = "BULLISH"
        reason = "Closed above previous close and above the open."
    elif C1 < O1 and C1 < C2 and (C1 - L1) < (H1 - C1) * 0.4:
        bias = "STRONG BEARISH"
        reason = "Closed weak near the low and below previous close."
    elif C1 < O1 and C1 <= C2:
        bias = "BEARISH"
        reason = "Closed below both the open and previous close."
    else:
        bias = "NEUTRAL"
        reason = "Indecisive structure with no clear directional pressure."

    return bias, reason


# -----------------------------
# TASK: SEND DAILY MESSAGE
# -----------------------------
@tasks.loop(hours=24)
async def send_daily_bias():
    channel = bot.get_channel(CHANNEL_ID)
    bias, reason = generate_data_and_bias()

    message = (
        f"📊 **Daily BTCUSDT Bias**\n"
        f"**Bias:** {bias}\n"
        f"**Reason:** {reason}"
    )

    await channel.send(message)
    await channel.send(file=discord.File("btc_daily.png"))


# -----------------------------
# START WHEN READY
# -----------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    # Send immediately
    await send_daily_bias()

    # Then repeat daily forever
    send_daily_bias.start()


# -----------------------------
# RUN BOT
# -----------------------------
bot.run(TOKEN)
