# Typing Game

A Compute Club spelling and keyboard game.

## What it does

- Lets the child choose their name.
- Shows words in large letters.
- Asks the child to type one letter at a time.
- Records correct letters, wrong letters, and key press time.
- Saves results into CSV files.
- Adapts difficulty based on accuracy and typing speed.
- Allows different colour themes to compare what helps each child.

## Run on Raspberry Pi

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
