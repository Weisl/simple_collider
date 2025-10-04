from . import keymap, preferences

files = [
    preferences,
    keymap,
]


def register():
    for file in files:
        file.register()


def unregister():
    for file in reversed(files):
        file.unregister()
