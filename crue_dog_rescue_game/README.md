# Crue's Dog Rescue

A child-friendly Raspberry Pi / Pygame game.

## Game idea

Crue's idea:

- A massive field
- A little boy
- A girl
- A dog
- The dog gets let off the lead
- Two suspicious men take the dog
- The family gets in a car
- The player controls the car with the mouse
- Search around a council estate to find and rescue the dog

## Controls

- Move mouse: steer the car
- Hold left mouse button: drive forward
- R: restart
- ESC: quit

## Install

From inside your `compute-club-python` repo:

```bash
cd ~/ComputeClub/compute-club-python/crue_dog_rescue_game
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Add to Raspberry Pi Games menu

```bash
cat > ~/.local/share/applications/crue-dog-rescue.desktop <<EOF
[Desktop Entry]
Name=Crue Dog Rescue
Comment=Mouse controlled dog rescue car game
Exec=$HOME/ComputeClub/compute-club-python/crue_dog_rescue_game/.venv/bin/python $HOME/ComputeClub/compute-club-python/crue_dog_rescue_game/main.py
Path=$HOME/ComputeClub/compute-club-python/crue_dog_rescue_game
Icon=applications-games
Terminal=false
Type=Application
Categories=Game;
EOF

chmod +x ~/.local/share/applications/crue-dog-rescue.desktop
lxpanelctl restart
```

Then open:

Raspberry menu -> Games -> Crue Dog Rescue
