
# Mimic Discord Bot Usage Instructions

## Table of Contents
1. [Overview](#overview)
2. [Setting Up](#setting-up)
3. [Commands](#commands)
4. [How It Works](#how-it-works)
5. [Notes](#notes)

For information on logging into your server, see the [SSH Login Instructions](ssh_login_instructions.md).


## Overview
Mimic is a Discord bot designed to use text-to-speech (TTS) functionality with custom voice settings. Each user can register their own ElevenLabs API key and set up custom voices.

## Setting Up
1. **Register for ElevenLabs**: If you don't have an ElevenLabs account, create one [here](https://elevenlabs.io).
2. **Get Your ElevenLabs API Key**: Find your API key in your ElevenLabs account settings.
3. **Access Voice Library**: Choose and manage your voices on ElevenLabs [voice library](https://elevenlabs.io/voice-library).

## Commands
1. `/register_key [api_key]` - Register your ElevenLabs API key with Mimic.
2. `/add_voice [nickname] [voice_id]` - Add a new voice with a nickname for easy reference.
3. `/change_voice [nickname]` - Switch to a different voice by its nickname.
4. `/list_voices` - List all your registered voices and their nicknames.
5. `/join` - Command Mimic to join your current voice channel.
6. `/speak [sentence]` - Mimic will speak the sentence in the voice channel using the selected voice.

## How It Works
- **Personal Voice Library**: Each user can add multiple voices to their personal library. These voices are identified by unique nicknames and correspond to specific ElevenLabs voice IDs.
- **Privacy of Voices**: You cannot use or switch to voices added by other users. Each user's voice library is private and unique to their Discord ID.
- **Switching Voices**: To switch between different voices in your library, use the `/change_voice` command with the nickname of the desired voice.
- **Speaking in Voice Channels**: Use the `/speak` command to make Mimic speak a sentence in the voice channel using your current voice preference.

## Notes
- You cannot use voices set up by other users. Each user must add their desired voices individually.
- Make sure to register your ElevenLabs API key using the `/register_key` command before using Mimic.

Enjoy using Mimic to enhance your Discord experience!
