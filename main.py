import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
import io
import requests
import os
from PIL import Image

# --- CONFIGURATION ---
TOKEN = os.getenv('DISCORD_TOKEN')
WELCOME_CH_ID = 1479911571865206804
RULES_CH_ID = 1479912156811231233
BATTLE_CH_ID = 1479914097285005363
LEADERBOARD_CH_ID = 1479923157249822891
RATING_SUBMIT_CH = 1479924175329169458
RATING_VOTE_CH = 1479924157809557689
BATTLE_ROLE_ID = 1479922753225232515
RATER_ROLE_ID = 1479924491000877287

# Role Mappings
MALE_ROLES = {"LTN": 1479923820793041130, "MTN": 1479923847569608795, "HTN": 1479923874954215505, "CHADLITE": 1479923900417572874, "CHAD": 1479923892876349661}
FEMALE_ROLES = {"LTB": 1479925354402545898, "MTB": 1479925361977594009, "HTB": 1479925365815119954, "STACYLITE": 1479925369057312818, "STACY": 1479925371439681699}

class RatingButton(ui.Button):
    def __init__(self, label, role_id):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, custom_id=f"rate_{label}_{role_id}")
        self.votes = 0

    async def callback(self, interaction: discord.Interaction):
        self.votes += 1
        await interaction.response.send_message(f"Vote recorded for {self.label}!", ephemeral=True)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.battle_queue = []

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# --- UTILS ---
def stitch_images(url1, url2):
    img1 = Image.open(requests.get(url1, stream=True).raw)
    img2 = Image.open(requests.get(url2, stream=True).raw)
    h = 500
    img1 = img1.resize((int(img1.width * h / img1.height), h))
    img2 = img2.resize((int(img2.width * h / img2.height), h))
    new_img = Image.new('RGB', (img1.width + img2.width + 10, h), (0, 0, 0))
    new_img.paste(img1, (0, 0))
    new_img.paste(img2, (img1.width + 10, 0))
    img_byte_arr = io.BytesIO()
    new_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

# --- EVENTS ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CH_ID)
    if channel:
        embed = discord.Embed(title="Welcome to our Community", description=f"Greetings {member.mention}!\n\nPlease review <#{RULES_CH_ID}>.", color=discord.Color.blue())
        await channel.send(content=member.mention, embed=embed)

# --- COMMANDS ---
@bot.tree.command(name="ratingmale")
async def ratingmale(interaction: discord.Interaction, img1: discord.Attachment):
    await handle_rating(interaction, img1, "male", MALE_ROLES)

@bot.tree.command(name="ratingfemale")
async def ratingfemale(interaction: discord.Interaction, img1: discord.Attachment):
    await handle_rating(interaction, img1, "female", FEMALE_ROLES)

async def handle_rating(interaction, img, gender, role_map):
    if interaction.channel_id != RATING_SUBMIT_CH: return
    channel = bot.get_channel(RATING_VOTE_CH)
    view = ui.View(timeout=14400)
    
    buttons = []
    for label, r_id in role_map.items():
        btn = RatingButton(label, r_id)
        view.add_item(btn)
        buttons.append(btn)

    embed = discord.Embed(title=f"{gender.capitalize()} Rating", description=f"User: {interaction.user.mention}")
    embed.set_image(url=img.url)
    msg = await channel.send(content=f"<@&{RATER_ROLE_ID}>", embed=embed, view=view)
    await interaction.response.send_message("Submitted!", ephemeral=True)

    await asyncio.sleep(14400) # 4 Hours
    winner_btn = max(buttons, key=lambda b: b.votes)
    role = interaction.guild.get_role(int(winner_btn.custom_id.split('_')[2]))
    await interaction.user.add_roles(role)
    await channel.send(f"Rating finished for {interaction.user.mention}. Rank assigned: **{winner_btn.label}**")

@bot.tree.command(name="mogbattle")
async def mogbattle(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    bot.battle_queue.append({"user": interaction.user, "url": image.url})
    
    if len(bot.battle_queue) >= 2:
        p1, p2 = bot.battle_queue.pop(0), bot.battle_queue.pop(0)
        stitched = stitch_images(p1['url'], p2['url'])
        channel = bot.get_channel(BATTLE_CH_ID)
        file = discord.File(stitched, filename="battle.png")
        msg = await channel.send(content=f"<@&{BATTLE_ROLE_ID}> ⚔️ **MOG BATTLE**", file=file)
        await msg.add_reaction("⬅️")
        await msg.add_reaction("➡️")
        
        await asyncio.sleep(10800) # 3 Hours
        updated_msg = await channel.fetch_message(msg.id)
        left_v = next(r.count for r in updated_msg.reactions if str(r.emoji) == "⬅️") - 1
        right_v = next(r.count for r in updated_msg.reactions if str(r.emoji) == "➡️") - 1
        
        winner = p1['user'] if left_v > right_v else p2['user']
        lb_channel = bot.get_channel(LEADERBOARD_CH_ID)
        await lb_channel.send(f"🏆 **{winner.name}** won a Mog Battle!")

@bot.tree.command(name="giveaway")
@app_commands.checks.has_permissions(administrator=True)
async def giveaway(interaction: discord.Interaction, prize: str, hours: int, image: discord.Attachment = None):
    embed = discord.Embed(title="🎁 GIVEAWAY", description=f"**Prize:** {prize}\n**Time:** {hours}h", color=0x00ff00)
    if image: embed.set_image(url=image.url)
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("Giveaway started!", ephemeral=True)

bot.run(TOKEN)
