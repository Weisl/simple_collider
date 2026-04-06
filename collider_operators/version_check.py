import threading
import urllib.request
import urllib.error
import json

# Module-level state — read by the panel draw function
update_available = False
latest_version_str = ""

_RELEASES_URL = "https://api.github.com/repos/Weisl/simple_collider/releases/latest"


def _parse_version(version_str):
    """Convert '2.1.4' or 'v2.1.4' to (2, 1, 4)."""
    return tuple(int(x) for x in version_str.lstrip("v").split("."))


def _fetch():
    global update_available, latest_version_str
    try:
        req = urllib.request.Request(
            _RELEASES_URL,
            headers={"User-Agent": "simple-collider-addon"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        tag = data.get("tag_name", "")
        if not tag:
            return

        latest = _parse_version(tag)

        # Read current version from blender_manifest.toml at the addon root
        import os
        manifest_path = os.path.join(os.path.dirname(__file__), "..", "blender_manifest.toml")
        current_str = ""
        with open(manifest_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("version"):
                    current_str = line.split("=")[1].strip().strip('"')
                    break

        if not current_str:
            return

        current = _parse_version(current_str)

        if latest > current:
            update_available = True
            latest_version_str = tag.lstrip("v")
        else:
            print(f"[Simple Collider] Addon is up to date (v{current_str})")

    except Exception as exc:
        print(f"[Simple Collider] version check failed: {exc}")


def start_version_check():
    """Fire a background thread to check for a newer release on GitHub."""
    t = threading.Thread(target=_fetch, daemon=True)
    t.start()
