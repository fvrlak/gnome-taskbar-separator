# gnome-taskbar-separator

![separator preview](preview.png)

A simple CLI tool to add visual separators between app groups in the GNOME taskbar.

## The Problem

GNOME's taskbar (and extensions like Zorin Taskbar / Dash to Panel) don't support built-in separators between pinned app groups. If you want to visually group your browsers, tools, and communication apps, you're out of luck — until now.

## How It Works

The tool creates invisible `.desktop` entries with a custom transparent icon containing a subtle white vertical line. These are pinned into GNOME's `favorite-apps` list via `gsettings`, appearing as visual dividers between your app groups.

No root access required. Everything is installed in your home directory.

## Requirements

- GNOME Shell (tested on GNOME 46, Zorin OS 18, Ubuntu 24.04)
- Python 3
- [Pillow](https://python-pillow.org/) (`pip3 install pillow`)

## Installation

```bash
git clone https://github.com/fvrlak/gnome-taskbar-separator
cd gnome-taskbar-separator
./install.sh
```

Make sure `~/.local/bin` is in your PATH. Add this to your `~/.bashrc` if needed:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then reload your shell:

```bash
source ~/.bashrc
```

## Usage

### Add a separator

```bash
taskbar-separator add [--horizontal|-H]
```

Adds a new vertical separator to the end of the taskbar. Drag it to reposition between your app groups.
Use `--horizontal` or `-H` for a horizontal line instead.

### Remove the last separator

```bash
taskbar-separator remove
```

### List current taskbar layout

```bash
taskbar-separator list
```

Output example:

```
Current taskbar apps:
  0: org.gnome.Nautilus.desktop
  1: google-chrome.desktop
  2: taskbar-separator.desktop  ← separator
  3: org.gnome.Terminal.desktop
```

You can add as many separators as you need — each one gets a unique name (`taskbar-separator`, `taskbar-separator2`, `taskbar-separator3`, etc.).

## Uninstall

```bash
taskbar-separator remove   # repeat until all separators are gone
./install.sh --uninstall
rm -f ~/.local/share/icons/taskbar-separator.png
```

If `taskbar-separator` is "command not found", rerun install:

```bash
cd /home/fvrlak/Videos/gnome-taskbar-separator
./install.sh
```

## License

MIT — see [LICENSE](LICENSE)
