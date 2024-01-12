
# TMUX Session Management Instructions

## Creating a New Session
To create a new TMUX session, use the following command:
```
tmux new -s my_discord_bot
```
Replace `my_discord_bot` with your desired session name.

## Running the Bot
Within the TMUX session, navigate to your bot's directory and start the bot:
```
python3 panshemlumus.py
```

## Detaching from the Session
To detach from the TMUX session and leave the bot running in the background, use:
```
tmux detach
```
or you can simply press `Ctrl+B` followed by `D`.

## Reattaching to the Session
To reattach to a TMUX session, use:
```
tmux attach -t my_discord_bot
```
Replace `my_discord_bot` with the name of your session.

## Viewing Active Sessions
To view all active TMUX sessions, use:
```
tmux list-sessions
```
## Disable Active Session
To Disable a Active Session, first list all sessions:
```
tmux ls
```
Then Attach to the Session:
```
tmux attach -t my_discord_bot
```
Replace `my_discord_bot` with the name of your session.

Finally Type `exit` to disable the session