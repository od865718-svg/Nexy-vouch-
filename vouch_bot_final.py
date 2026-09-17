import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord import ui
import asyncio
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import random

load_dotenv()

# ==================== CONFIG ====================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "1547715438396444742"))
VOUCH_CHANNEL_ID = 1547715439700746265
CUSTOMER_ROLE_NAME = "Customer"
BANNER_URL = "https://cdn.discordapp.com/attachments/1547715439700746268/1548155496039710801/banner.png?ex=6aab4da9&is=6aa9fc29&hm=b3aa71736562c9def56ee6b44522a9d003dd3a1e0ffacaf9c80c86b9ef2352c0&"

# ==================== STATE ====================
vouch_counter = 1852
vouch_file = "vouch_data.json"
last_reminder_message_id = None

FAKE_VOUCHES = [
    {"user": "Arctic", "text": "+rep perm spoofer absolutely goated", "stars": 5},
    {"user": "ShadowX", "text": "Been using for 3 months, never caught. Insane", "stars": 5},
    {"user": "DevNull", "text": "Best investment ever made", "stars": 5},
    {"user": "CryptoKid", "text": "Support helped me in 5 minutes, legend", "stars": 5},
    {"user": "NoobMaster", "text": "Actually works unlike other garbage out there", "stars": 5},
    {"user": "PhantomCoder", "text": "Factory reset not even needed, that's crazy", "stars": 5},
    {"user": "IcebergX", "text": "Undetected for 6 months straight", "stars": 5},
    {"user": "VoidWalker", "text": "The cheats just hit different fr", "stars": 5},
    {"user": "NeonGhost", "text": "Worth every penny, no regrets", "stars": 5},
    {"user": "ThunderStrike", "text": "Better than the hype, honestly", "stars": 5},
    {"user": "SilentKnight", "text": "Setup was super easy, works instantly", "stars": 5},
    {"user": "OmegaForce", "text": "My entire squad using it now", "stars": 5},
    {"user": "CrimsonBlade", "text": "Zero kicks in a week, still running", "stars": 5},
    {"user": "FrostByte", "text": "Customer service actually responds fast", "stars": 5},
    {"user": "InfernoX", "text": "Can't believe how good this is", "stars": 5},
    {"user": "EchoKnight", "text": "Lifetime worth it, best purchase ever", "stars": 5},
    {"user": "SonicWave", "text": "Updates are so fast, impressed ngl", "stars": 5},
    {"user": "VortexForce", "text": "Told all my friends, they love it too", "stars": 5},
    {"user": "NightshadeX", "text": "Support team actually cares, rare nowadays", "stars": 5},
    {"user": "StormRider", "text": "Easy setup, instant results, 100% recommend", "stars": 5},
]

# ==================== HELPERS ====================
def has_customer_role(member: discord.Member) -> bool:
    return any(role.name == CUSTOMER_ROLE_NAME for role in member.roles)

def load_vouch_data():
    global vouch_counter
    if os.path.exists(vouch_file):
        try:
            with open(vouch_file, 'r') as f:
                data = json.load(f)
                vouch_counter = data.get("counter", 1852)
        except:
            vouch_counter = 1852
    return vouch_counter

def save_vouch_data():
    with open(vouch_file, 'w') as f:
        json.dump({"counter": vouch_counter}, f)

async def get_vouch_channel(guild):
    try:
        ch = guild.get_channel(VOUCH_CHANNEL_ID)
        return ch
    except:
        return None

# ==================== MODAL ====================
class VouchModal(ui.Modal, title="Leave a Vouch"):
    stars = ui.TextInput(
        label="Rating (1-5 stars)",
        placeholder="1, 2, 3, 4, or 5",
        min_length=1,
        max_length=1
    )
    vouch_text = ui.TextInput(
        label="Your vouch",
        placeholder="Share your experience with Nexy...",
        style=discord.TextStyle.long,
        min_length=5,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            star_rating = int(self.stars.value)
            if star_rating < 1 or star_rating > 5:
                await interaction.response.send_message("❌ Stars must be 1-5", ephemeral=True)
                return
        except:
            await interaction.response.send_message("❌ Stars must be a number (1-5)", ephemeral=True)
            return
        
        # Create vouch embed
        guild = interaction.guild
        vouch_ch = await get_vouch_channel(guild)
        if not vouch_ch:
            await interaction.response.send_message("❌ Vouch channel not found", ephemeral=True)
            return
        
        global vouch_counter
        vouch_counter += 1
        save_vouch_data()
        
        stars_display = "⭐" * star_rating
        
        embed = discord.Embed(
            title="New vouch created!",
            color=discord.Color.gold()
        )
        embed.add_field(name=stars_display, value="", inline=False)
        embed.add_field(name="Vouch:", value=self.vouch_text.value, inline=False)
        embed.add_field(name="Vouch Nº:", value=str(vouch_counter), inline=True)
        embed.add_field(name="Vouched by:", value=interaction.user.mention, inline=True)
        embed.add_field(name="Vouched at:", value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)
        embed.set_footer(text="Service provided by Nexy")
        
        await vouch_ch.send(embed=embed)
        await interaction.response.send_message("✅ Vouch posted!", ephemeral=True)

# ==================== BOT SETUP ====================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} online")
    load_vouch_data()
    reminder_task.start()
    fake_vouch_task.start()
    auto_delete_task.start()
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Sync error: {e}")

# ==================== SLASH COMMAND ====================
@bot.tree.command(name="vouch", description="Leave a vouch for Nexy")
async def vouch(interaction: discord.Interaction):
    if not has_customer_role(interaction.user):
        embed = discord.Embed(
            title="❌ Customer Role Required",
            description="Only customers can leave vouches.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.send_modal(VouchModal())

# ==================== AUTO-DELETE NON-SLASH MESSAGES ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    vouch_ch = await get_vouch_channel(message.guild)
    if not vouch_ch:
        await bot.process_commands(message)
        return
    
    # If in vouch channel and not a slash command
    if message.channel == vouch_ch and not message.content.startswith("/"):
        try:
            await message.delete()
        except:
            pass
    
    await bot.process_commands(message)

# ==================== REMINDER TASK (35 MIN) ====================
@tasks.loop(minutes=35)
async def reminder_task():
    try:
        for guild in bot.guilds:
            vouch_ch = await get_vouch_channel(guild)
            if not vouch_ch:
                continue
            
            global last_reminder_message_id
            
            # Delete old reminder
            if last_reminder_message_id:
                try:
                    old_msg = await vouch_ch.fetch_message(last_reminder_message_id)
                    await old_msg.delete()
                except:
                    pass
            
            # Send new reminder
            embed = discord.Embed(
                title="📋 Leave a Vouch!",
                description=f"Use `/vouch` to share your experience with Nexy services!\n\n**Total Vouches: {vouch_counter}**",
                color=discord.Color.blurple()
            )
            embed.set_image(url=BANNER_URL)
            embed.set_footer(text="Your feedback helps the community!")
            
            msg = await vouch_ch.send(embed=embed)
            last_reminder_message_id = msg.id
    except Exception as e:
        print(f"Reminder task error: {e}")

@reminder_task.before_loop
async def before_reminder():
    await bot.wait_until_ready()

# ==================== FAKE VOUCH TASK (5 HOURS) ====================
@tasks.loop(hours=5)
async def fake_vouch_task():
    try:
        for guild in bot.guilds:
            vouch_ch = await get_vouch_channel(guild)
            if not vouch_ch:
                continue
            
            global vouch_counter
            vouch_counter += 1
            save_vouch_data()
            
            fake = random.choice(FAKE_VOUCHES)
            stars_display = "⭐" * fake["stars"]
            
            embed = discord.Embed(
                title="New vouch created!",
                color=discord.Color.gold()
            )
            embed.add_field(name=stars_display, value="", inline=False)
            embed.add_field(name="Vouch:", value=fake["text"], inline=False)
            embed.add_field(name="Vouch Nº:", value=str(vouch_counter), inline=True)
            embed.add_field(name="Vouched by:", value=f"@{fake['user']}", inline=True)
            embed.add_field(name="Vouched at:", value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)
            embed.set_footer(text="Service provided by Nexy")
            
            await vouch_ch.send(embed=embed)
    except Exception as e:
        print(f"Fake vouch task error: {e}")

@fake_vouch_task.before_loop
async def before_fake_vouch():
    await bot.wait_until_ready()

# ==================== AUTO-DELETE TASK (CHECK EVERY 5 MIN) ====================
@tasks.loop(minutes=5)
async def auto_delete_task():
    try:
        for guild in bot.guilds:
            vouch_ch = await get_vouch_channel(guild)
            if not vouch_ch:
                continue
            
            async for message in vouch_ch.history(limit=50):
                # Skip bot messages and vouch embeds
                if message.author.bot:
                    continue
                if message.embeds:
                    continue
                # Delete non-command messages
                if not message.content.startswith("/"):
                    try:
                        await message.delete()
                    except:
                        pass
    except Exception as e:
        print(f"Auto-delete task error: {e}")

@auto_delete_task.before_loop
async def before_auto_delete():
    await bot.wait_until_ready()

# ==================== RUN ====================
if __name__ == "__main__":
    bot.run(TOKEN)
