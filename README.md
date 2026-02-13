# Ramses Out

**Preview collection and review preparation tool for Ramses pipeline.**

Ramses Out scans your Ramses project for preview files, tracks upload history, and helps you collect and package previews for fTrack review submission.

## Features

- 🔍 **Smart Scanning** - Automatically finds all preview files in project structure
- ✅ **Status Tracking** - Marks which previews have been sent for review
- 📦 **Collection** - Collects selected previews into a review package folder
- 📝 **Shot Lists** - Generates manifest of collected shots
- 🎯 **Filtering** - Filter by date, sequence, or step
- 📊 **Upload History** - Tracks all review submissions with timestamps
- 💡 **Smart Defaults** - Auto-selects "Ready" previews for convenience

## Project Structure

Ramses Out scans for preview files in the standard Ramses structure:

```
PROJECT/
  05-SHOTS/
    PROJECT_S_SHOT/
      PROJECT_S_SHOT_STEP/
        _preview/
          PROJECT_S_SHOT_STEP.mp4    # Video preview
          PROJECT_S_SHOT_STEP.jpg    # Thumbnail
          .review_sent_2026-02-11.txt # Marker file (created by tool)
```

## Installation

### From Source (Development)

```bash
cd Ramses-Out
pip install -r requirements.txt
python -m ramses_out
```

### Compiled Executable

Download `RamsesOut.exe` from releases and place it in your Ramses tools directory.

## Usage

### Launching

**From Python:**
```bash
python -m ramses_out
```

**From exe:**
```bash
RamsesOut.exe
```

### Workflow

1. **Open Project** - Make sure you have an active project in Ramses Client
2. **Scan** - Tool automatically scans on launch, or click "Refresh"
3. **Filter** - Use dropdowns to filter by date, sequence, or step
4. **Select** - Check previews you want to collect (Ready items auto-selected)
5. **Collect** - Click "Collect to Folder" and choose destination
6. **Review Package Created** - Previews copied with shot list manifest
7. **Upload to fTrack** - Manually upload the package to fTrack
8. **Mark as Sent** - Click "Mark as Sent" to create tracking markers

### Review Package Contents

After collection, your folder contains:

```
ReviewPackage_20260211/
  ├── PROJECT_S_SH010_COMP.mp4
  ├── PROJECT_S_SH020_COMP.mp4
  ├── PROJECT_S_SH030_ANIM.mp4
  └── shot_list.txt              # Manifest
```

### Shot List Format

```
Review Package - AWESOME_PROJECT
Generated: 2026-02-11 14:30

# SEQ01

SH010 - COMP - MP4 (23.4 MB)
SH020 - COMP - MP4 (45.2 MB)

# SEQ02

SH030 - ANIM - MP4 (12.8 MB)

────────────────────────────────────────────────────────────
Total: 3 shots
```

## Upload Tracking

### Marker Files

When you mark previews as sent, the tool creates marker files:

**Location:** `_preview/.review_sent_2026-02-11.txt`

**Contents:**
```
Uploaded: 2026-02-11 14:35:22
Destination: fTrack Review
User: username
Package: AWESOME_20260211
Notes: Initial review submission
```

### Upload History Log

All submissions are logged to: `~/.ramses/upload_history.log`

**Format:** `timestamp|Review|shot_id|step|fTrack|username|package_name`

**Example:**
```
2026-02-11 14:35|Review|SH010|COMP|fTrack|username|AWESOME_20260211
2026-02-11 14:35|Review|SH020|COMP|fTrack|username|AWESOME_20260211
```

## Configuration

Ramses Out uses the common Ramses configuration:

- **Windows**: `%appdata%/Ramses/Config/ramses_addons_settings.json`
- **Linux**: `~/.config/Ramses/Config/ramses_addons_settings.json`
- **macOS**: `~/Library/Application Support/Ramses/Config/ramses_addons_settings.json`

## Keyboard Shortcuts

- **F5** - Refresh scan
- **Ctrl+A** - Select all
- **Ctrl+D** - Deselect all
- **Space** - Toggle selected row

## Troubleshooting

**No previews found:**
- Verify active project is selected in Ramses Client
- Check that `_preview/` folders exist in shot step directories
- Ensure preview files are named correctly: `PROJECT_S_SHOT_STEP.mp4`

**Cannot mark as sent:**
- Check file permissions in `_preview/` folders
- Verify you have write access to project directory

**Previews not auto-selected:**
- Already-sent previews are not auto-selected
- Use filters to show only "Ready" items

## Development

### Project Structure

```
Ramses-Out/
├── ramses_out/
│   ├── __init__.py
│   ├── __main__.py         # Entry point
│   ├── gui.py              # Main UI
│   ├── models.py           # Data structures
│   ├── scanner.py          # Preview scanning
│   ├── tracker.py          # Upload tracking
│   ├── collector.py        # File collection
│   └── stylesheet.py       # UI styling
├── lib/
│   └── ramses/             # Ramses API library
├── requirements.txt
├── setup.py
└── README.md
```

### Dependencies

- **PySide6** - Qt bindings for Python (GUI framework)
- **Ramses API** - From lib/ramses/ (included)

### Testing

```bash
# Run in development mode
cd Ramses-Out
python -m ramses_out
```

## Building Executable

### Using PyInstaller

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name RamsesOut ramses_out/__main__.py
```

The executable will be created in `dist/RamsesOut.exe`.

## Integration with Ramses Hub

Place `RamsesOut.exe` in the same directory as `RamsesHub.exe` for automatic detection and launching from the Hub.

## Author

**Overmind Studios**

## Links

- [Ramses Asset Manager](https://ramses.rxlab.io/)
- [Documentation](https://ramses-docs.rxlab.io/)
