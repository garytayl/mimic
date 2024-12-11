import discord
from discord.ext import commands, tasks
import random
import requests
import json
import asyncio
import os
from cryptography.fernet import Fernet
import cryptography
from dotenv import load_dotenv
import traceback
import mysql.connector
import aiohttp
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse

# Assign the database URL from environment variables to a variable for use in the code
database_url = os.getenv("DATABASE_URL")

# Debugging: Print the database URL to ensure it is retrieved correctly
print("DATABASE_URL:", database_url)

# Load environment variables from a .env file
load_dotenv()

# Retrieve the Discord token and ElevenLabs API key from environment variables
discord_token = os.getenv('DISCORD_TOKEN')
elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')  # Use the server's API key

# Ensure the Discord token is present; otherwise, raise an error
if not discord_token:
    raise ValueError("discord_token environment variable is required.")

# Ensure the ElevenLabs API key is present; otherwise, raise an error
if not elevenlabs_api_key:
    raise ValueError("ELEVENLABS_API_KEY environment variable is required.")

# Variable to track the first user who calls the bot
first_caller_user_id = None

# Configure Discord bot intents and command prefix
intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix=lambda bot, msg: '', intents=intents)

# Dictionary to store user-specific voice preferences
user_voice_preferences = {}
DEFAULT_VOICE_ID = "NYC9WEgkq1u4jiqBseQ9"  # Replace with the actual default voice ID

# Command to join the user's current voice channel
@bot.slash_command(name="join_channel", description="Join the current voice channel")
async def join_channel(ctx):
    global first_caller_user_id, is_bot_in_voice_channel

    # Ensure the user is in a voice channel
    voice_state = ctx.author.voice
    if not voice_state or not voice_state.channel:
        await ctx.respond("You are not in a voice channel.")
        return

    new_voice_channel = voice_state.channel

    # Store the first caller's user ID for reference
    if not first_caller_user_id:
        first_caller_user_id = ctx.author.id
        print(f"Storing first caller user ID: {first_caller_user_id}")

    try:
        # Check if the bot is already connected to a voice channel
        voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        if voice_client:
            if voice_client.is_connected():
                if voice_client.channel != new_voice_channel:
                    await voice_client.move_to(new_voice_channel)
                else:
                    await ctx.respond(f"Already connected to {new_voice_channel.name}")
                    return
            else:
                await voice_client.disconnect(force=True)
        else:
            await new_voice_channel.connect()

        is_bot_in_voice_channel = True
        await ctx.respond(f"Connected to voice channel: {new_voice_channel.name}")

    except Exception as e:
        print(f"Error in join command: {e}")
        await ctx.respond(f"An error occurred: {e}")

# Command to add a new voice for a user
@bot.slash_command(name="add_voice", description="Add a new voice with a nickname")
async def add_voice(ctx, nickname: str, voice_id: str):
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_voice_preferences:
        user_voice_preferences[user_id_str] = {"voices": {}, "api_key": ""}
    user_voice_preferences[user_id_str]["voices"][nickname] = voice_id
    save_user_preferences(user_voice_preferences)
    await ctx.respond(f"Added voice '{nickname}' with ID '{voice_id}'")

# Command to switch to a different voice by nickname
@bot.slash_command(name="change_voice", description="Switch to a different voice by nickname")
async def change_voice(ctx, nickname: str):
    user_id_str = str(ctx.author.id)
    if user_id_str in user_voice_preferences:
        user_voices = user_voice_preferences[user_id_str].get("voices", {})
        if nickname in user_voices:
            user_voice_preferences[user_id_str]['current_voice_id'] = user_voices[nickname]
            save_user_preferences(user_voice_preferences)
            await ctx.respond(f"Switched to voice '{nickname}'.")
        else:
            await ctx.respond(f"No voice found with nickname '{nickname}'.")
    else:
        await ctx.respond("You have not set up any voices.")

# Command to list all voices registered by a user
@bot.slash_command(name="list_voices", description="List all voices and their nicknames")
async def list_voices(ctx):
    user_id_str = str(ctx.author.id)
    if user_id_str in user_voice_preferences:
        prefs = user_voice_preferences[user_id_str]
        response = "Your registered voices:\n"
        for nickname, voice_id in prefs.get('voices', {}).items():
            response += f"Nickname: {nickname}, Voice ID: {voice_id}\n"
    else:
        response = "You have not set up any voices."
    await ctx.respond(response)

# Command to speak a user-provided sentence using text-to-speech
@bot.slash_command(name="say_sentence", description="Speak a sentence using TTS")
async def say(ctx, sentence: str):
    await speak(sentence, ctx=ctx)

# Command to say a random pre-defined phrase
@bot.slash_command(name="say_blurb", description="Say a random blurb")
async def blurb(ctx):
    await say(ctx, get_random_saying())
    
@bot.slash_command(name="check_characters", description="Check remaining characters")
async def characters_remaining(ctx):
    user_id_str = str(ctx.author.id)
    if user_id_str in user_voice_preferences:
        remaining_characters = user_voice_preferences[user_id_str].get('remaining_characters', 500)
        await ctx.respond(f"You have {remaining_characters} characters remaining for today.")
    else:
        await ctx.respond("You have not set up any limits.")
        
@tasks.loop(hours=720)
async def reset_character_limits():
    print("Resetting character limits for all users")
    for user_id in user_voice_preferences:
        user_voice_preferences[user_id]['remaining_characters'] = user_voice_preferences[user_id].get('character_limit', 500)
    save_user_preferences(user_voice_preferences)
    print("Character limits reset successfully")

@reset_character_limits.before_loop
async def before_reset_character_limits():
    await bot.wait_until_ready()

reset_character_limits.start()

def get_db_connection():
    dsn = os.environ.get("DATABASE_URL")
    print("DATABASE_URL inside function:", dsn)
    if not dsn:
        raise ValueError("DATABASE_URL is not set! Make sure the Postgres plugin is attached in Railway.")
    
    # Connect to the database and set the default cursor factory to DictCursor
    return psycopg2.connect(dsn, cursor_factory=psycopg2.extras.DictCursor)



def save_user_preferences(preferences):
    conn = get_db_connection()
    cursor = conn.cursor()

    for user_id, data in preferences.items():
        voices = json.dumps(data.get('voices', {}))
        current_voice_id = data.get('current_voice_id', '')
        character_limit = data.get('character_limit', 500)
        remaining_characters = data.get('remaining_characters', 500)
        subscription_tier = data.get('subscription_tier', 'free')
        subscription_expiry = data.get('subscription_expiry', None)

        cursor.execute('''
            INSERT INTO user_preferences (user_id, voices, current_voice_id, character_limit, remaining_characters, subscription_tier, subscription_expiry)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
            voices = EXCLUDED.voices,
            current_voice_id = EXCLUDED.current_voice_id,
            character_limit = EXCLUDED.character_limit,
            remaining_characters = EXCLUDED.remaining_characters,
            subscription_tier = EXCLUDED.subscription_tier,
            subscription_expiry = EXCLUDED.subscription_expiry
        ''', (user_id, voices, current_voice_id, character_limit, remaining_characters, subscription_tier, subscription_expiry))

    conn.commit()
    cursor.close()
    conn.close()


def load_user_preferences():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user_preferences')
    rows = cursor.fetchall()
    preferences = {}

    for row in rows:
        preferences[row['user_id']] = {
            'voices': json.loads(row['voices']),
            'current_voice_id': row['current_voice_id'],
            'character_limit': row['character_limit'],
            'remaining_characters': row['remaining_characters'],
            'subscription_tier': row['subscription_tier'],
            'subscription_expiry': row['subscription_expiry']
        }

    cursor.close()
    conn.close()
    return preferences


# Check subscription status using Discord API
async def check_user_subscription(user_id):
    url = f"https://discord.com/api/v9/users/@me/guilds/{guild_id}/premium"
    headers = {
        "Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                entitlements = await response.json()
                for entitlement in entitlements:
                    if entitlement['user_id'] == str(user_id) and entitlement['sku_id']:
                        return True
            return False

@bot.slash_command(name="check_sub", description="Check remaining characters and subscription status")
async def check_sub(ctx):
    try:
        user_id_str = str(ctx.author.id)
        print(f"Checking subscription for user ID: {user_id_str}")
        
        if await check_user_subscription(ctx.author.id):
            if user_id_str in user_voice_preferences:
                remaining_characters = user_voice_preferences[user_id_str].get('remaining_characters', 500)
                subscription_tier = user_voice_preferences[user_id_str].get('subscription_tier', 'premium')
                await ctx.respond(f"Subscription Tier: {subscription_tier}\nRemaining Characters: {remaining_characters}")
            else:
                await ctx.respond("You have not set up any limits.")
        else:
            await ctx.respond("You do not have a premium subscription.")
    except Exception as e:
        print(f"Error in check_sub command: {e}")
        await ctx.respond("An error occurred while checking your subscription status.")



@bot.command(name="set_voice_channel")
@commands.has_permissions(administrator=True)
async def set_voice_channel(ctx, channel_name):
    """Set the bot's default voice channel for this server."""
    guild = ctx.guild
    voice_channel = discord.utils.get(guild.voice_channels, name=channel_name)
    if voice_channel:
        await ctx.send(f"Voice channel set to: {voice_channel.name}")
        # Store this configuration in a database or in-memory dictionary
    else:
        await ctx.send(f"Voice channel {channel_name} not found.")

@bot.command(name="set_text_channel")
@commands.has_permissions(administrator=True)
async def set_text_channel(ctx, channel_name):
    """Set the bot's default text channel for this server."""
    guild = ctx.guild
    text_channel = discord.utils.get(guild.text_channels, name=channel_name)
    if text_channel:
        await ctx.send(f"Text channel set to: {text_channel.name}")
        # Store this configuration in a database or in-memory dictionary
    else:
        await ctx.send(f"Text channel {channel_name} not found.")


async def speak(sentence: str, ctx=None, voice_client=None):
    try:
        print("speak function called")
        if ctx:
            print("Context provided, deferring response")
            await ctx.defer()
            voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
            print(f"Voice client from context: {voice_client}, Guild: {ctx.guild}")

        if not voice_client or not voice_client.is_connected():
            print("No voice client or not connected")
            if ctx:
                await ctx.respond("Bot is not connected to the voice channel.", ephemeral=True)
            return

        user_id_str = str(ctx.author.id) if ctx else str(first_caller_user_id)
        print(f"User ID: {user_id_str}")

        user_preference = user_voice_preferences.get(user_id_str, {})
        print(f"User preferences: {user_preference}")

        if 'api_key' not in user_preference or not user_preference['api_key']:
            print("API key not found in user preferences")
            if ctx:
                await ctx.respond("Please register your ElevenLabs API key using /register_key.", ephemeral=True)
            return

        encrypted_api_key = user_preference['api_key']
        print(f"Encrypted API key: {encrypted_api_key}")

        api_key = encrypted_api_key
        if api_key and api_key.startswith("gAAAAA"):
            print("API key appears to be encrypted, decrypting.")
            api_key = decrypt_api_key(encrypted_api_key)

        print(f"API key used for request: {api_key}")

        if not api_key:
            print("API key is None or invalid")
            if ctx:
                await ctx.respond("Invalid API key. Please re-register your ElevenLabs API key.", ephemeral=True)
            return

        voice_id = user_preference.get('current_voice_id', user_preference.get('voices', {}).get('default', DEFAULT_VOICE_ID))
        nickname = next((name for name, id in user_preference.get('voices', {}).items() if id == voice_id), 'Default')
        print(f"Voice ID: {voice_id}, Nickname: {nickname}")

        if ctx:
            print("Responding with custom message")
            await ctx.respond(f"{nickname} is speaking")

        remaining_characters = user_preference.get('remaining_characters', 500)
        if len(sentence) > remaining_characters:
            await ctx.respond("Character limit exceeded. Please purchase more characters or upgrade your plan.")
            return

        print(f"Processing TTS and playing audio: Voice ID: {voice_id}, API Key: {api_key}")
        await process_tts_and_play(voice_client, sentence, voice_id, api_key)

        if 'remaining_characters' not in user_preference:
            user_preference['remaining_characters'] = 500  # or whatever your default is

        user_preference['remaining_characters'] -= len(sentence)
        save_user_preferences(user_voice_preferences)

        if ctx:
            # Directly send the follow-up message in the current channel
            await ctx.channel.send(f"{nickname} spoke: {sentence}")

    except Exception as e:
        print(f"An error occurred in speak function: {e}")
        traceback.print_exc()
        if ctx:
            await ctx.respond("An error occurred while processing your request.", ephemeral=True)


# Slash command for speaking a sentence using TTS
@bot.slash_command(description="Speak a sentence using TTS")
async def say(ctx, sentence: str):
    await speak(sentence, ctx=ctx)

# Slash command for saying a random blurb
@bot.slash_command(description="Say a random blurb")
async def blurb(ctx):
    await say(ctx, get_random_saying())

# Global variable to track if the bot is in a voice channel
is_bot_in_voice_channel = False

# Random speech task
@tasks.loop(minutes=random.randint(1, 60))
async def random_speech_task():
    if not is_bot_in_voice_channel:
        print("Bot is not in a voice channel. Skipping random speech task.")
        return
    print("Random speech task started.")
    for guild in bot.guilds:
        print(f"Checking guild: {guild.name}")
        voice_client = discord.utils.get(bot.voice_clients, guild=guild)
        if voice_client and voice_client.is_connected():
            print(f"Found connected voice client in guild: {guild.name}")
            saying = get_random_saying()
            print(f"Random saying selected: {saying}")
            await speak(saying, voice_client=voice_client)

@random_speech_task.before_loop
async def before_random_speech_task():
    print("Waiting for bot to be ready before starting random speech task.")
    await bot.wait_until_ready()
    print("Bot is ready, starting random speech task.")

random_speech_task.start()

# Function to process TTS and play audio
async def process_tts_and_play(voice_client, text, voice_id, api_key):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",  # You might want to make this configurable as well
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            if response.status == 200:
                audio_file = 'output.mp3'
                with open(audio_file, 'wb') as f:
                    f.write(await response.read())
                await play_audio_in_vc(voice_client, audio_file)
                os.remove(audio_file)
            else:
                print("Failed to generate speech:")
                print(await response.text())

async def sync_commands():
    try:
        await bot.sync_commands()
        print("Slash commands synchronized successfully.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_ready():
    global user_voice_preferences
    user_voice_preferences = load_user_preferences()
    print(f'We have logged in as {bot.user}')
    print("Bot is ready.")
    await sync_commands()


# Function to play audio in voice channel
async def play_audio_in_vc(voice_client, audio_file):
    print("Playing audio in the voice channel.")
    voice_client.play(discord.FFmpegPCMAudio(audio_file))
    while voice_client.is_playing():
        await asyncio.sleep(1)
    print("Finished playing audio in the voice channel.")
    
# Load sayings from the JSON file
with open('bot_sayings.json', 'r') as file:
    bot_sayings = json.load(file)["sayings"]

# Function to get a random saying
def get_random_saying():
    return random.choice(bot_sayings)

# Function to speak a random saying in a voice channel
async def speak_random_saying(voice_client):
    saying = get_random_saying()
    await speak(voice_client, saying)  # Assuming your speak function works with this signature


@bot.event
async def on_voice_state_update(member, before, after):
    global is_bot_in_voice_channel, first_caller_user_id
    if member == bot.user:
        if after.channel is None:
            is_bot_in_voice_channel = False
            first_caller_user_id = None  # Reset first caller user ID
            print(f"Bot has disconnected from a voice channel in {member.guild.name}.")
        else:
            is_bot_in_voice_channel = True

@bot.event
async def on_guild_join(guild):
    welcome_message = """
    **Mimic Discord Bot Usage Instructions**

    **Overview**
    Mimic is a Discord bot designed to use text-to-speech (TTS) functionality with custom voice settings. Each user can register their own ElevenLabs API key and set up custom voices.

    **Default Setup**
    - Mimic will attempt to use the first available text and voice channels.
    - You can customize channels using the `/set_voice_channel` and `/set_text_channel` commands.

    **Commands**
    1. `/register_key [api_key]` - Register your ElevenLabs API key.
    2. `/add_voice [nickname] [voice_id]` - Add a new voice with a nickname.
    3. `/change_voice [nickname]` - Switch to a different voice.
    4. `/list_voices` - List all your registered voices.
    5. `/set_voice_channel [channel_name]` - Set the bot's default voice channel.
    6. `/set_text_channel [channel_name]` - Set the bot's default text channel.

    Enjoy using Mimic!
    """

    # Dynamically detect text and voice channels
    text_channel = discord.utils.get(guild.text_channels, permissions_for=guild.me, send_messages=True)
    voice_channel = discord.utils.get(guild.voice_channels, permissions_for=guild.me, connect=True)

    # Log detected channels
    print(f"Joined guild: {guild.name}")
    if text_channel:
        print(f"Detected text channel: {text_channel.name}")
        await text_channel.send(welcome_message)
    else:
        print("No suitable text channel found.")

    if voice_channel:
        print(f"Detected voice channel: {voice_channel.name}")
    else:
        print("No suitable voice channel found.")

bot.run(discord_token)
