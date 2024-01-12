import discord
from discord.ext import commands
import random
import requests
import json
import asyncio
import os

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix=lambda _: '', intents=intents)

# Store user voice ID preferences
user_voice_preferences = {}

# Load the configuration file
with open('config.json') as config_file:
    config = json.load(config_file)

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


@bot.slash_command(guild_ids=[guild_id], description="Join a voice channel")
async def join(ctx):
    print("Attempting to join a voice channel.")
    voice_channel = discord.utils.get(ctx.guild.voice_channels, name=voice_channel_name)
    if voice_channel:
        print(f"Found voice channel: {voice_channel.name}, attempting to connect.")
        await voice_channel.connect()
        print(f"Connected to voice channel: {voice_channel.name}")
        await ctx.respond(f"Joined voice channel: {voice_channel.name}")
        await speak_random_saying(voice_client)
    else:
        print("Could not find the voice channel to join.")
        await ctx.respond("Voice channel not found.")

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



def load_user_preferences():
    try:
        with open('user_preferences.json', 'r') as file:
            data = file.read()
            if not data:  # File is empty
                return {}
            return json.loads(data)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_user_preferences(preferences):
    with open('user_preferences.json', 'w') as file:
        json.dump(preferences, file, indent=4)

@bot.slash_command(guild_ids=[guild_id], description="Register your ElevenLabs API key")
async def register_key(ctx, api_key: str):
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_voice_preferences:
        user_voice_preferences[user_id_str] = {"voices": {}, "api_key": ""}
    user_voice_preferences[user_id_str]['api_key'] = api_key
    save_user_preferences(user_voice_preferences)
    print(f"Registered API key for user {ctx.author}: {api_key}")  # Debugging print
    await ctx.respond("Your ElevenLabs API key has been registered.", ephemeral=True)


@bot.slash_command(guild_ids=[guild_id], description="Speak a sentence using TTS")
async def speak(ctx, sentence: str):
    try:
        await ctx.defer()
        voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        if not voice_client or not voice_client.is_connected():
            await ctx.followup.send("Bot is not connected to the voice channel.", ephemeral=True)
            return

        user_id_str = str(ctx.author.id)
        user_preference = user_voice_preferences.get(user_id_str, {})
        
        if 'api_key' not in user_preference or not user_preference['api_key']:
            await ctx.followup.send("Please register your ElevenLabs API key using /register_key.", ephemeral=True)
            return

        api_key = user_preference['api_key']
        voice_id = user_preference.get('current_voice_id', base_voice_id)

        # Get the nickname associated with the current voice ID
        nickname = next((name for name, id in user_preference.get('voices', {}).items() if id == voice_id), 'Default')

        await process_tts_and_play(voice_client, sentence, voice_id, api_key)

        text_channel = discord.utils.get(ctx.guild.text_channels, name=text_channel_name)
        if text_channel:
            await text_channel.send(f"{nickname} spoke: {sentence}")

        # Send an ephemeral confirmation response to the user
        await ctx.followup.send("Your request has been processed.", ephemeral=True)

    except Exception as e:
        print(f"An error occurred: {e}")
        await ctx.followup.send("An error occurred while processing your request.", ephemeral=True)

# Implement the blurb command
@bot.slash_command(guild_ids=[guild_id], description="Say a random blurb")
async def blurb(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_connected():
        await speak_random_saying(voice_client)

# Random speech task
@tasks.loop(minutes=random.randint(5, 30))  # Adjust time interval as needed
async def random_speech_task():
    for guild in bot.guilds:
        voice_client = discord.utils.get(bot.voice_clients, guild=guild)
        if voice_client and voice_client.is_connected():
            await speak_random_saying(voice_client)

@random_speech_task.before_loop
async def before_random_speech_task():
    await bot.wait_until_ready()

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



bot.run(discord_token)
