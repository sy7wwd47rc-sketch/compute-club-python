# Hendrix Maze

A Raspberry Pi friendly first-person maze game for Computer Club.

## Game idea

- First-person maze
- Blue and green colours
- Mouse movement
- Small learned map in the top-right
- The map only reveals where the player has been
- Find the green finish square

## Controls

- Move mouse left/right: turn
- Hold left mouse button: move forwards
- Hold right mouse button: move backwards
- R: new maze
- M: toggle full map / learned map
- ESC: quit
- Arrow keys or WASD also work as backup controls

## Install on Raspberry Pi OS

Open Terminal:

```bash
mkdir -p ~/ComputeClub
cd ~/ComputeClub
```

Copy this folder to the Pi, then:

```bash
cd ~/ComputeClub/hendrix_maze_game
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Make a desktop shortcut

Create the application shortcut:

```bash
mkdir -p ~/.local/share/applications
nano ~/.local/share/applications/hendrix-maze.desktop
```

Paste this:

```ini
[Desktop Entry]
Name=Hendrix Maze
Comment=First person blue and green maze game
Exec=/home/pi/ComputeClub/hendrix_maze_game/.venv/bin/python /home/pi/ComputeClub/hendrix_maze_game/main.py
Path=/home/pi/ComputeClub/hendrix_maze_game
Icon=applications-games
Terminal=false
Type=Application
Categories=Game;
```

If your Pi username is not `pi`, replace `/home/pi` with your real home folder, for example `/home/tonypi2`.

Then refresh the menu:

```bash
chmod +x ~/.local/share/applications/hendrix-maze.desktop
```

It should appear under the Games menu.
