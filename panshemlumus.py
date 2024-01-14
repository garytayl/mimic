import discord
from discord.ext import commands, tasks
import random
import requests
import json
import asyncio
import os
from cryptography.fernet import Fernet
import cryptography

first_caller_user_id = None


fernet_key_file = 'fernet_key.txt'

# Function to read the Fernet key
def read_fernet_key():
    try:
        with open("fernet_key.txt", "rb") as key_file:
            key = key_file.read()
            print(f"Read Fernet key: {key}")
            return key
    except FileNotFoundError:
        print("Fernet key file not found. Generating a new key.")
        key = Fernet.generate_key()
        with open("fernet_key.txt", "wb") as key_file:
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
bot = commands.Bot(command_prefix=lambda _: '', intents=intents)

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

@bot.slash_command(guild_ids=[guild_id], description="Register your ElevenLabs API key")
async def register_key(ctx, api_key: str):
    user_id_str = str(ctx.author.id)
    encrypted_api_key = encrypt_api_key(api_key)

    # If the user is already in the preferences, update their API key
    # If not, create a new entry with the default voice ID
    if user_id_str in user_voice_preferences:
        user_voice_preferences[user_id_str]['api_key'] = encrypted_api_key
    else:
        user_voice_preferences[user_id_str] = {
            "voices": {"default": DEFAULT_VOICE_ID},
            "api_key": encrypted_api_key
        }

    save_user_preferences(user_voice_preferences)
    await ctx.respond("Your ElevenLabs API key has been registered.", ephemeral=True)


# Use the keys from the configuration file
discord_token = config['discord_token']
guild_id = config['guild_id']
voice_channel_name = "where the talking goes"
text_channel_name = "text-to-speech"
base_voice_id = config.get('base_voice_id', 'default_voice_id')  # Set a default value

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

@bot.slash_command(guild_ids=[guild_id], description="Join the current voice channel")
async def join(ctx):
    global first_caller_user_id, is_bot_in_voice_channel

    # Check if the user is in a voice channel
    voice_state = ctx.author.voice
    if not voice_state or not voice_state.channel:
        await ctx.respond("You are not in a voice channel.")
        return

    # Get the voice channel of the command-invoking user
    voice_channel = voice_state.channel

    if not first_caller_user_id:
        first_caller_user_id = ctx.author.id
        print(f"Storing first caller user ID: {first_caller_user_id}")

    try:
        voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        if voice_client and voice_client.channel == voice_channel:
            if not voice_client.is_connected():
                await voice_client.disconnect(force=True)
            else:
                await ctx.respond(f"Already connected to {voice_channel.name}")
                return

        await voice_channel.connect()
        is_bot_in_voice_channel = True
        await ctx.respond(f"Connected to voice channel: {voice_channel.name}")

    except Exception as e:
        print(f"Error in join command: {e}")
        await ctx.respond(f"An error occurred: {e}")








@bot.slash_command(guild_ids=[guild_id], description="Add a new voice with a nickname")
async def add_voice(ctx, nickname: str, voice_id: str):
    user_id_str = str(ctx.author.id)
    
    # Check if the user is already in the user_voice_preferences dictionary
    if user_id_str not in user_voice_preferences:
        user_voice_preferences[user_id_str] = {"voices": {}, "api_key": ""}

    # Add or update the voice nickname and ID in the user's preferences
    user_voice_preferences[user_id_str]["voices"][nickname] = voice_id
    save_user_preferences(user_voice_preferences)
    
    await ctx.respond(f"Added voice '{nickname}' with ID '{voice_id}'")


@bot.slash_command(guild_ids=[guild_id], description="Switch to a different voice by nickname")
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


@bot.slash_command(guild_ids=[guild_id], description="List all voices and their nicknames")
async def list_voices(ctx):
    user_id_str = str(ctx.author.id)
    if user_id_str in user_voice_preferences:
        prefs = user_voice_preferences[user_id_str]
        nickname = prefs.get('nickname', 'No nickname set')
        voice_id = prefs.get('voice_id', 'No voice ID set')
        response = f"Your registered voice:\nNickname: {nickname}\nVoice ID: {voice_id}"
    else:
        response = "You have not set up any voices."

    await ctx.respond(response)



def save_user_preferences(preferences):
    # Encrypt API keys before saving
    for user_id, data in preferences.items():
        if 'api_key' in data:
            encrypted_api_key = (data['api_key'])
            data['api_key'] = encrypted_api_key
    
    with open('user_preferences.json', 'w') as file:
        json.dump(preferences, file, indent=4)

def load_user_preferences():
    try:
        with open('user_preferences.json', 'r') as file:
            data = json.load(file)
            for user_id, preferences in data.items():
                if 'api_key' in preferences:
                    preferences['api_key'] = decrypt_api_key(preferences['api_key'])
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


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

        # Check if the key appears to be encrypted
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

        print(f"Processing TTS and playing audio: {sentence}, Voice ID: {voice_id}, API Key: {api_key}")
        await process_tts_and_play(voice_client, sentence, voice_id, api_key)

        if ctx:
            # Try to find the specific 'text-to-speech' channel
            text_channel = discord.utils.get(ctx.guild.text_channels, name=text_channel_name)
            
            # Fallback to the first text channel if 'text-to-speech' is not found
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
        if ctx:
            await ctx.respond("An error occurred while processing your request.", ephemeral=True)

# Slash command for speaking a sentence using TTS
@bot.slash_command(guild_ids=[guild_id], description="Speak a sentence using TTS")
async def say(ctx, sentence: str):
    await speak(sentence, ctx=ctx)

# Slash command for saying a random blurb
@bot.slash_command(guild_ids=[guild_id], description="Say a random blurb")
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
    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        audio_file = 'output.mp3'
        with open(audio_file, 'wb') as f:
            f.write(response.content)
        await play_audio_in_vc(voice_client, audio_file)
        os.remove(audio_file)
    else:
        print("Failed to generate speech:")
        print(response.text)

@bot.event
async def on_ready():
    global user_voice_preferences
    user_voice_preferences = load_user_preferences()
    print(f'We have logged in as {bot.user}')

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


bot.run(discord_token)
