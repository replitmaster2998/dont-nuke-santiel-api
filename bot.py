import os
import uuid
import json
import discord
import logging
import santiel
import numpy as np
import cloudscraper
import xgboost as xgb
from datetime import datetime
from discord import app_commands
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

logging.basicConfig(filename='santiel.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

class AClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.synced = False

    async def on_ready(self):
        if not self.synced:
            await tree.sync()
            self.synced = True
        os.system('cls' if os.name == 'nt' else 'clear')
        logging.info(f'Logged in as {self.user.name}')

client = AClient()
tree = app_commands.CommandTree(client)
scraper = cloudscraper.create_scraper(browser={'custom': 'ScraperBot/1.0'})

def load_tokens():
    try:
        with open('token.json', 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def validate_token(token):
    return token.startswith("3CM+Jf14kZOXz7AtQ2pR9jzH4UVm9d5Ro2zM")

def unrig(token):
    try:
        response = scraper.get("https://api.bloxflip.com/provably-fair", headers={"x-auth-token": token})
        response.raise_for_status()
        old_seed = response.json().get("clientSeed", "Unknown")
        new_seed = str(uuid.uuid4())
        scraper.post("https://api.bloxflip.com/provably-fair/clientSeed", headers={"x-auth-token": token}, json={"clientSeed": new_seed})
        return discord.Embed(title="Unrigged Successfully", color=0x1E90FF, description=f"Old Seed: ```{old_seed}```\nNew Seed: ```{new_seed}```")
    except Exception as e:
        logging.error(f'Unrig Error: {e}')
        return discord.Embed(title='Error', color=0xff0000, description="Exception Error: Code (101)")

async def predict_safe_spots(safe_amount, token):
    try:
        response = scraper.get("https://api.bloxflip.com/games/mines/history?size=50&page=0", headers={'X-Auth-Token': token})
        response.raise_for_status()
        features = [
            [1 if i in game.get('mineLocations', []) else 0 for i in range(25)]
            for game in response.json().get('data', [])
        ]
        scaler = StandardScaler()
        X_train, _, y_train, _ = train_test_split(scaler.fit_transform(np.array(features)), features, test_size=0.2, random_state=42)
        model = xgb.XGBClassifier(random_state=0).fit(X_train, y_train)
        predictions = model.predict_proba(scaler.transform(np.zeros((1, 25))))[0]
        predicted_safe_spots = np.argsort(predictions)[-safe_amount:]
        return '\n'.join(''.join(['✓' if (i * 5 + j) in predicted_safe_spots else '✗' for j in range(5)]) for i in range(5))
    except Exception as e:
        logging.error(f'Predict Safe Spots Error: {e}')
        return "Contact support for help"

async def check_channel(interaction):
    return interaction.channel.id == 1234573327675166781

@tree.command(name='freemines', description='Mines game mode')
async def mines(interaction: discord.Interaction, tile_amt: int):
    await interaction.response.defer()
    if not await check_channel(interaction):
        return await interaction.followup.send(embed=discord.Embed(title='Error', color=0xff0000, description="Please use command in the correct channel."))

    auth = load_tokens().get(str(interaction.user.id))
    if not auth:
        return await interaction.followup.send(embed=discord.Embed(title='Error', color=0xff0000, description="Please link your account first."))

    try:
        response = scraper.get("https://api.bloxflip.com/games/mines", headers={"x-auth-token": auth})
        response.raise_for_status()
        gamebase = response.json()

        if gamebase.get("hasGame", False):
            data = gamebase.get('game', {})
            em = discord.Embed(title="Santiel's Predictor | Free", color=0x1E90FF)
            em.add_field(name='Grid:', value=f"```\n{await predict_safe_spots(tile_amt, auth)}\n```")
            em.add_field(name='Safe Clicks:', value=str(tile_amt), inline=True)
            em.add_field(name='Mines Amount:', value=str(data.get('minesAmount', 'Unknown')), inline=True)
            em.add_field(name='Bet Amount:', value=str(data.get('betAmount', 'Unknown')), inline=True)
            em.add_field(name='Round ID:', value=data.get('uuid', 'Unknown'), inline=True)
            em.add_field(name='Method:', value="Zodiac Log", inline=True)
            em.add_field(name='Requested by:', value=f"<@{interaction.user.id}>", inline=True)
            em.set_footer(text=datetime.now().strftime("%m/%d/%Y %I:%M %p"))
            await interaction.followup.send(embed=em)
        else:
            await interaction.followup.send(embed=discord.Embed(title='Error', color=0xff0000, description="No active game found."))
    except Exception as e:
        logging.error(f'Mines Command Error: {e}')
        await interaction.followup.send(embed=discord.Embed(title='Error', color=0xff0000, description="An error occurred. Please try again later."))

@tree.command(name='freelink', description='Link your Bloxflip account')
async def link(interaction: discord.Interaction, token: str):
    if not await check_channel(interaction):
        return await interaction.followup.send(embed=discord.Embed(title='Error', color=0xff0000, description="Please use command in the correct channel."))

    tokens = load_tokens()
    user_id = str(interaction.user.id)

    if user_id in tokens:
        return await interaction.user.send(embed=discord.Embed(title='Error', color=0xff0000, description="Your account is already linked. Use `/freeunlink` to unlink before linking a new one."))

    if validate_token(token):
        tokens[user_id] = token
        with open('token.json', 'w') as file:
            json.dump(tokens, file, indent=4)
        await interaction.user.send(embed=discord.Embed(title='Success', color=0x00ff00, description="Your account has been successfully linked."))
    else:
        await interaction.user.send(embed=discord.Embed(title='Invalid Token', color=0xff0000, description="The provided token is invalid."))

@tree.command(name='freeunlink', description='Unlink your Bloxflip account')
async def unlink(interaction: discord.Interaction):
    if not await check_channel(interaction):
        return await interaction.followup.send(embed=discord.Embed(title='Error', color=0xff0000, description="Please use command in the correct channel."))

    tokens = load_tokens()
    user_id = str(interaction.user.id)
    
    if user_id in tokens:
        tokens.pop(user_id)
        with open('token.json', 'w') as file:
            json.dump(tokens, file, indent=4)
        await interaction.user.send(embed=discord.Embed(title='Success', color=0x00ff00, description="Your account has been successfully unlinked."))
    else:
        await interaction.user.send(embed=discord.Embed(title='Error', color=0xff0000, description="No token found."))

@tree.command(name='freeunrig', description='Feeling unlucky? Use the unrig command now')
async def unrig_command(interaction: discord.Interaction):
    await interaction.response.defer()
    if not await check_channel(interaction):
        return await interaction.followup.send(embed=discord.Embed(title='Error', color=0xff0000, description="Please use command in the correct channel."))

    token = load_tokens().get(str(interaction.user.id))
    if token:
        await interaction.followup.send(embed=unrig(token))
    else:
        await interaction.followup.send(embed=discord.Embed(title='Error', color=0xff0000, description="Please link your account first."))

if __name__ == "__main__":
    santiel.keep_alive()
    client.run(os.environ['SANTIEL_DISCORD_TOKEN'])

