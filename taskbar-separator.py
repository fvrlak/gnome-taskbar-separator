#!/usr/bin/env python3
"""
gnome-taskbar-separator - Add visual separators to the GNOME taskbar
https://github.com/fvrlak/gnome-taskbar-separator
"""

import ast
import sys
import subprocess
from pathlib import Path

ICON_DIR = Path.home() / ".local/share/icons"
APPS_DIR = Path.home() / ".local/share/applications"

ICON_PATH_V = ICON_DIR / "taskbar-separator.png"
ICON_PATH_H = ICON_DIR / "taskbar-separator-h.png"


def create_icon(horizontal=False):
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    icon_path = ICON_PATH_H if horizontal else ICON_PATH_V
    if icon_path.exists():
        return icon_path
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        if horizontal:
            for x in range(8, 56):
                alpha = int(180 * (1 - abs(x - 32) / 32))
                draw.point((x, 31), fill=(255, 255, 255, alpha))
                draw.point((x, 32), fill=(255, 255, 255, alpha))
        else:
            for y in range(8, 56):
                alpha = int(180 * (1 - abs(y - 32) / 32))
                draw.point((31, y), fill=(255, 255, 255, alpha))
                draw.point((32, y), fill=(255, 255, 255, alpha))
        img.save(str(icon_path))
    except ImportError:
        print("Error: Pillow is required. Install it with: pip3 install pillow")
        sys.exit(1)
    return icon_path


def get_favorites():
    result = subprocess.run(
        ['gsettings', 'get', 'org.gnome.shell', 'favorite-apps'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        err = (result.stderr or "gsettings command failed").strip()
        print(f"Error: cannot read favorite apps from gsettings: {err}", file=sys.stderr)
        return []
    raw = result.stdout.strip()
    # Parse GVariant string array like "['app1.desktop', 'app2.desktop']"
    if not raw:
        return []
    try:
        parsed = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        apps = [s.strip().strip("'") for s in raw.strip("[]").split(",")]
        return [a for a in apps if a]
    if not isinstance(parsed, list):
        return []
    return [a for a in parsed if a]


def set_favorites(apps):
    formatted = "[" + ", ".join(f"'{app}'" for app in apps) + "]"
    result = subprocess.run(['gsettings', 'set', 'org.gnome.shell', 'favorite-apps', formatted], capture_output=True, text=True)
    if result.returncode != 0:
        err = (result.stderr or "gsettings command failed").strip()
        print(f"Error: cannot write favorite apps to gsettings: {err}", file=sys.stderr)
        sys.exit(1)


def next_separator_name():
    existing = list(APPS_DIR.glob('taskbar-separator*.desktop'))
    nums = []
    for f in existing:
        name = f.stem
        if name == 'taskbar-separator':
            nums.append(1)
        elif name.startswith('taskbar-separator') and name[17:].isdigit():
            nums.append(int(name[17:]))
    if not nums:
        return 'taskbar-separator'
    return f'taskbar-separator{max(nums) + 1}'


def create_desktop_file(name, icon_path):
    APPS_DIR.mkdir(parents=True, exist_ok=True)
    content = f"""[Desktop Entry]
Name=
Type=Application
Exec=true
Icon={icon_path}
NoDisplay=false
Categories=
"""
    path = APPS_DIR / f"{name}.desktop"
    path.write_text(content)
    return f"{name}.desktop"


def cmd_add(args):
    horizontal = '--horizontal' in args or '-H' in args
    icon_path = create_icon(horizontal=horizontal)
    name = next_separator_name()
    desktop_file = create_desktop_file(name, icon_path)
    favorites = get_favorites()
    favorites.append(desktop_file)
    set_favorites(favorites)
    orientation = "horizontal" if horizontal else "vertical"
    print(f"Added {orientation} separator '{name}' — drag it to reposition in the taskbar.")


def cmd_remove(args):
    favorites = get_favorites()
    separators = [(i, app) for i, app in enumerate(favorites) if app.startswith('taskbar-separator')]
    if not separators:
        print("No separators found in taskbar.")
        return
    # Remove last separator by default
    i, app = separators[-1]
    favorites.pop(i)
    set_favorites(favorites)
    desktop_path = APPS_DIR / app
    if desktop_path.exists():
        desktop_path.unlink()
    print(f"Removed separator '{app}'.")


def cmd_list(args):
    favorites = get_favorites()
    print("Current taskbar apps:")
    for i, app in enumerate(favorites):
        tag = " ← separator" if app.startswith('taskbar-separator') else ""
        print(f"  {i}: {app}{tag}")


def usage():
    print("Usage: taskbar-separator <command>")
    print("")
    print("Commands:")
    print("  add [--horizontal|-H]  Add a new separator (vertical by default)")
    print("  remove                 Remove the last separator from the taskbar")
    print("  list                   List all taskbar apps with their positions")


def main():
    commands = {'add': cmd_add, 'remove': cmd_remove, 'list': cmd_list}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        usage()
        sys.exit(1)
    commands[sys.argv[1]](sys.argv[2:])


if __name__ == '__main__':
    main()
