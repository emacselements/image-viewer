## Support & Donations

If you find this project helpful, consider supporting it!

[Donate via PayPal](https://www.paypal.com/paypalme/revrari)

# Image Viewer

A powerful, user-friendly image viewer for Linux, written in Python with Tkinter and Pillow. It supports fast navigation, zoom, pan, crop, GIF animation, folder history, copy/move/duplicate/delete, background options, and more.

## Features

- **Image Navigation:** Next/Previous, First/Last, Random, Slideshow, and folder navigation.
- **Zoom & Pan:** Smooth zoom in/out, fit-to-window, pan with mouse or arrow keys, and per-image zoom memory.
- **Animated GIFs:** Full support for animated GIFs with play/pause.
- **Crop Tool:** Crop images interactively and save as new files.
- **Image Operations:** Delete (to trash), duplicate, copy, move, and remove duplicates (via `fdupes`).
- **Folder Management:** Browse folders, history of recent folders, delete entire folder (with safety checks).
- **Backgrounds:** Switch between white, gray, black, or checkered backgrounds for transparency.
- **Customizable UI:** Fullscreen toggle, border toggle, toolbar hide/show, status messages, and keyboard shortcuts for all actions.
- **Persistence:** Remembers last viewed image, zoom/pan per image, and folder/copy/move history.

## Requirements

- Python 3.x
- [Pillow](https://python-pillow.org/) (`pip install pillow`)
- [send2trash](https://pypi.org/project/Send2Trash/) (`pip install send2trash`)
- (Optional) [fdupes](https://github.com/adrianlopezroche/fdupes) for duplicate removal (`sudo apt install fdupes`)

## Usage

```bash
pip install pillow send2trash
python3 image_viewer.py
```

You can also open a specific image:

```bash
python3 image_viewer.py /path/to/image.jpg
```

## Keyboard Shortcuts

- **Navigation:**
	- Next: `N` or `PgDn`
	- Previous: `P` or `PgUp`
	- First: `H` or `Home`
	- Last: `E` or `End`
	- Random: `R`
	- Slideshow: `W` (Space to pause/resume)
- **Zoom & Pan:**
	- Zoom In/Out: `+` / `-`
	- Fit: `0`
	- Save View: `S` or `9`
	- Clear View: `8`
	- Pan: Arrow keys or mouse drag
- **Image Operations:**
	- Delete: `D` or `Del`
	- Duplicate: `D`
	- Copy: `C`
	- Move: `V`
	- Remove Duplicates: Button only
- **Folder Operations:**
	- Select Folder: Button only
	- Next/Prev Folder: `Ctrl+→` / `Ctrl+←`
	- Delete Folder: `Ctrl+Shift+Del`
- **Other:**
	- Fullscreen: `F` or `F11`
	- Toggle Toolbar: `F9`
	- Exit: `Q`
	- Refresh: `F5`
	- Toggle Border: `O`
	- Change Background: `G`

## Notes

- The app stores settings and history in your home directory (e.g., `~/.image_viewer_zoom.json`).
- For best experience, use on Linux with Nemo or a compatible file manager.
- All destructive actions (delete, remove duplicates, delete folder) have safety checks and confirmations.

## License

MIT License
