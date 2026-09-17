import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord import ui
import asyncio
import os
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ==================== CONFIG ====================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "1547715438396444742"))
VOUCH_CHANNEL_ID = 1547715439700746265
CUSTOMER_ROLE_ID = 1547715438396444750
BANNER_URL = "https://cdn.discordapp.com/attachments/1547715439700746268/1548155496039710801/banner.png?ex=6aab4da9&is=6aa9fc29&hm=b3aa71736562c9def56ee6b44522a9d003dd3a1e0ffacaf9c80c86b9ef2352c0&"

# ==================== STATE ====================
vouch_counter = 0
vouch_file = "vouch_data.json"
reminder_message_id = None

# ==================== HELPERS ====================
def has_customer_role(member: discord.Member) -> bool:
    return any(role.id == CUSTOMER_ROLE_ID for role in member.roles)

def load_vouch_data():
    global vouch_counter
    if os.path.exists(vouch_file):
        try:
            with open(vouch_file, 'r') as f:
                data = json.load(f)
                vouch_counter = data.get("counter", 0)
        except:
            vouch_counter = 0
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

async def post_reminder(guild, vouch_ch):
    """Delete old reminder and post new one"""
    global reminder_message_id
    
    # Delete old reminder
    if reminder_message_id:
        try:
            old_msg = await vouch_ch.fetch_message(reminder_message_id)
            await old_msg.delete()
        except:
            pass
    
    # Send new reminder
    embed = discord.Embed(
        title="📋 Leave a Vouch!",
        description="Use `/vouch` to share your experience with Nexy services!\n\nYour feedback helps the community!",
        color=discord.Color.blurple()
    )
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Powered by Nexy")
    
    msg = await vouch_ch.send(embed=embed)
    reminder_message_id = msg.id

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
        
        # Add stars field
        embed.add_field(name=stars_display, value="", inline=False)
        
        # Add vouch text
        embed.add_field(name="Vouch:", value=self.vouch_text.value, inline=False)
        
        # Add details in one row
        embed.add_field(name="Vouch Nº:", value=str(vouch_counter), inline=True)
        embed.add_field(name="Vouched by:", value=interaction.user.mention, inline=True)
        embed.add_field(name="Vouched at:", value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=True)
        
        # Add user avatar on right
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        
        embed.set_footer(text="Service provided by Nexy")
        
        await vouch_ch.send(embed=embed)
        
        # Delete old reminder and post new one
        await post_reminder(guild, vouch_ch)
        
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
            
            await post_reminder(guild, vouch_ch)
    except Exception as e:
        print(f"Reminder task error: {e}")

@reminder_task.before_loop
async def before_reminder():
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
