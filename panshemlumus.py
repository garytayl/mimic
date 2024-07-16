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
import aiohttp  # Ensure you have aiohttp for asynchronous HTTP requests

load_dotenv()

RDS_HOST = 'database-1.cbguawgeickp.us-east-2.rds.amazonaws.com'
RDS_USER = 'garytayl'
RDS_PASSWORD = '20Ineedtostudymore'
RDS_DB = 'user_preferences_db'

discord_token = os.getenv('DISCORD_TOKEN')
elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
database_url = os.getenv('DATABASE_URL')

first_caller_user_id = None

fernet_key_file = 'fernet_key.txt'

# Function to read the Fernet key
def read_fernet_key():
    try:
        with open(fernet_key_file, "rb") as key_file:
            key = key_file.read()
            print(f"Read Fernet key: {key}")
            return key
    except FileNotFoundError:
        print("Fernet key file not found. Generating a new key.")
        key = Fernet.generate_key()
        with open(fernet_key_file, "wb") as key_file:
            key_file.write(key)
            print(f"Generated and saved new Fernet key: {key}")
        return key
    except Exception as e:
        print(f"Error reading Fernet key: {e}")
        exit(1)

# Read the Fernet key
fernet_key = read_fernet_key()
cipher_suite = Fernet(fernet_key)

def encrypt_api_key(api_key):
    try:
        print(f"Encrypting API key: {api_key}")
        encrypted_key = cipher_suite.encrypt(api_key.encode()).decode()
        print(f"Encrypted API key: {encrypted_key}")
        return encrypted_key
    except Exception as e:
        print(f"Error encrypting API key: {e}")
        return None

def decrypt_api_key(encrypted_api_key):
    try:
        print(f"Decrypting API key: {encrypted_api_key}")
        decrypted = cipher_suite.decrypt(encrypted_api_key.encode()).decode()
        print(f"Decrypted API key: {decrypted}")
        return decrypted
    except cryptography.fernet.InvalidToken:
        print("Error: Invalid Token for decryption.")
        return None
    except Exception as e:
        print(f"Error decrypting API key: {e}")
        return None

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix=lambda bot, msg: '', intents=intents)

# Store user voice ID preferences
user_voice_preferences = {}
DEFAULT_VOICE_ID = "hnE9AUMm7IQABazTkTGI"  # Replace with the actual default voice ID

# Load the configuration file
with open('config.json') as config_file:
    config = json.load(config_file)
    discord_token = config['discord_token']
    guild_id = config['guild_id']  # Ensure this is defined here
    voice_channel_name = "where the talking goes"
    text_channel_name = "text-to-speech"
    base_voice_id = config.get('base_voice_id', 'default_voice_id')

@bot.slash_command(name="register_key", description="Register your ElevenLabs API key")
async def register_key(ctx, api_key: str):
    user_id_str = str(ctx.author.id)
    encrypted_api_key = encrypt_api_key(api_key)
    if user_id_str in user_voice_preferences:
        user_voice_preferences[user_id_str]['api_key'] = encrypted_api_key
    else:
        user_voice_preferences[user_id_str] = {
            "voices": {"default": DEFAULT_VOICE_ID},
            "api_key": encrypted_api_key
        }
    save_user_preferences(user_voice_preferences)
    await ctx.respond("Your ElevenLabs API key has been registered.", ephemeral=True)

@bot.slash_command(name="join_channel", description="Join the current voice channel")
async def join_channel(ctx):
    global first_caller_user_id, is_bot_in_voice_channel

    voice_state = ctx.author.voice
    if not voice_state or not voice_state.channel:
        await ctx.respond("You are not in a voice channel.")
        return

    new_voice_channel = voice_state.channel

    if not first_caller_user_id:
        first_caller_user_id = ctx.author.id
        print(f"Storing first caller user ID: {first_caller_user_id}")

    try:
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

@bot.slash_command(name="add_voice", description="Add a new voice with a nickname")
async def add_voice(ctx, nickname: str, voice_id: str):
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_voice_preferences:
        user_voice_preferences[user_id_str] = {"voices": {}, "api_key": ""}
    user_voice_preferences[user_id_str]["voices"][nickname] = voice_id
    save_user_preferences(user_voice_preferences)
    await ctx.respond(f"Added voice '{nickname}' with ID '{voice_id}'")

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

@bot.slash_command(name="say_sentence", description="Speak a sentence using TTS")
async def say(ctx, sentence: str):
    await speak(sentence, ctx=ctx)

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
    return mysql.connector.connect(
        host=RDS_HOST,
        user=RDS_USER,
        password=RDS_PASSWORD,
        database=RDS_DB
    )

def save_user_preferences(preferences):
    conn = get_db_connection()
    cursor = conn.cursor()

    for user_id, data in preferences.items():
        voices = json.dumps(data.get('voices', {}))
        current_voice_id = data.get('current_voice_id', '')
        api_key = data.get('api_key', '')
        character_limit = data.get('character_limit', 500)
        remaining_characters = data.get('remaining_characters', 500)
        subscription_tier = data.get('subscription_tier', 'free')
        subscription_expiry = data.get('subscription_expiry', None)

        cursor.execute('''INSERT INTO user_preferences (user_id, api_key, voices, current_voice_id, character_limit, remaining_characters, subscription_tier, subscription_expiry)
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                          ON DUPLICATE KEY UPDATE
                          api_key=VALUES(api_key),
                          voices=VALUES(voices),
                          current_voice_id=VALUES(current_voice_id),
                          character_limit=VALUES(character_limit),
                          remaining_characters=VALUES(remaining_characters),
                          subscription_tier=VALUES(subscription_tier),
                          subscription_expiry=VALUES(subscription_expiry)''',
                       (user_id, api_key, voices, current_voice_id, character_limit, remaining_characters, subscription_tier, subscription_expiry))

    conn.commit()
    cursor.close()
    conn.close()


def load_user_preferences():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM user_preferences')
    rows = cursor.fetchall()
    preferences = {}

    for row in rows:
        preferences[row['user_id']] = {
            'api_key': row['api_key'],
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
def check_subscription(user_id):
    url = f"https://discord.com/api/v9/users/@me/guilds/{guild_id}/premium"
    headers = {
        "Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        entitlements = response.json()
        for entitlement in entitlements:
            if entitlement['user_id'] == user_id and entitlement['sku_id'] == 'YOUR_PREMIUM_SKU_ID':
                return True
    return False


# Command to check remaining characters and subscription status
@bot.slash_command(name="check_sub", description="Check remaining characters and subscription status")
async def check_subscription(ctx):
    user_id_str = str(ctx.author.id)
    if check_subscription(ctx.author.id):
        if user_id_str in user_voice_preferences:
            remaining_characters = user_voice_preferences[user_id_str].get('remaining_characters', 15000)
            subscription_tier = user_voice_preferences[user_id_str].get('subscription_tier', 'premium')
            await ctx.respond(f"Subscription Tier: {subscription_tier}\nRemaining Characters: {remaining_characters}")
        else:
            await ctx.respond("You have not set up any limits.")
    else:
        await ctx.respond("You do not have a premium subscription.")



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

        user_preference['remaining_characters'] -= len(sentence)
        save_user_preferences(user_voice_preferences)

        if ctx:
            text_channel = discord.utils.get(ctx.guild.text_channels, name=text_channel_name)
            if not text_channel:
                text_channel = next((channel for channel in ctx.guild.text_channels if channel.permissions_for(ctx.guild.me).send_messages), None)
                if text_channel:
                    print(f"Fallback to general text channel: {text_channel.name}")
                else:
                    print("No available text channels found for sending a message.")

            if text_channel:
                await text_channel.send(f"{nickname} spoke: {sentence}")

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

@bot.event
async def on_ready():
    global user_voice_preferences
    user_voice_preferences = load_user_preferences()
    print(f'We have logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    print("Bot is ready.")


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

    **Setting Up**
    1. **Register for ElevenLabs**: If you don't have an ElevenLabs account, create one [here](https://elevenlabs.io).
    2. **Get Your ElevenLabs API Key**: Find your API key in your ElevenLabs account settings.
    3. **Access Voice Library**: Choose and manage your voices on ElevenLabs [voice library](https://elevenlabs.io/voice-library).

    **Commands**
    1. `/register_key [api_key]` - Register your ElevenLabs API key with Mimic.
    2. `/add_voice [nickname] [voice_id]` - Add a new voice with a nickname for easy reference.
    3. `/change_voice [nickname]` - Switch to a different voice by its nickname.
    4. `/list_voices` - List all your registered voices and their nicknames.
    5. `/join_channel` - Command Mimic to join your current voice channel.
    6. `/say [sentence]` - Mimic will speak the sentence in the voice channel using the selected voice.
    7. `/blurb` - Mimic will say a random saying.

    **How It Works**
    - **Personal Voice Library**: Each user can add multiple voices to their personal library. These voices are identified by unique nicknames and correspond to specific ElevenLabs voice IDs.
    - **Privacy of Voices**: You cannot use or switch to voices added by other users. Each user's voice library is private and unique to their Discord ID.
    - **Switching Voices**: To switch between different voices in your library, use the `/change_voice` command with the nickname of the desired voice.
    - **Speaking in Voice Channels**: Use the `/say` command to make Mimic speak a sentence in the voice channel using your current voice preference.

    **Notes**
    - You cannot use voices set up by other users. Each user must add their desired voices individually.
    - Make sure to register your ElevenLabs API key using the `/register_key` command before using Mimic.

    Enjoy using Mimic to enhance your Discord experience!
    """
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send(welcome_message)
            break

bot.run(discord_token)
