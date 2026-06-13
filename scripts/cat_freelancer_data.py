"""Cat names and demo profile pictures for freelancer demo accounts."""

from __future__ import annotations

# Playful cat names for demo freelancers (cycle if count > len).
CAT_NAMES = [
    "Puku",
    "Mochi",
    "Whiskers",
    "Luna",
    "Neko",
    "Tofu",
    "Bean",
    "Marmalade",
    "Simba",
    "Cleo",
    "Nimbus",
    "Pixel",
    "Socks",
    "Pumpkin",
    "Ziggy",
    "Biscuit",
    "Pepper",
    "Mango",
    "Oreo",
    "Tutu",
    "Miso",
    "Ginger",
    "Shadow",
    "Pickles",
    "Waffles",
]

# Stable square cat photos (CATAAS — each ID is a fixed image).
CAT_AVATAR_URLS = [
    "https://cataas.com/cat/ePjD3dUht1wKH6A2?width=400&height=400&type=square",
    "https://cataas.com/cat/tvRqj4lm91VrwsHd?width=400&height=400&type=square",
    "https://cataas.com/cat/FmTkbYVy0FSi4QBl?width=400&height=400&type=square",
    "https://cataas.com/cat/SXLh7Co7iYYEVVgi?width=400&height=400&type=square",
    "https://cataas.com/cat/QfYqnwDIr1NzbsKG?width=400&height=400&type=square",
    "https://cataas.com/cat/IP1LUbRjZik8JiJn?width=400&height=400&type=square",
    "https://cataas.com/cat/gPVgzvIs5JmCKMLQ?width=400&height=400&type=square",
    "https://cataas.com/cat/id7PTh1aMSldXfj8?width=400&height=400&type=square",
    "https://cataas.com/cat/LnGkgHMZFl5y4QYf?width=400&height=400&type=square",
    "https://cataas.com/cat/SFsjVgFoNKV5mCDO?width=400&height=400&type=square",
    "https://cataas.com/cat/er7AlLHvOkhYjiUX?width=400&height=400&type=square",
    "https://cataas.com/cat/y1sAMOXPczgTIVR1?width=400&height=400&type=square",
    "https://cataas.com/cat/HhAEBAH2VEez2tZy?width=400&height=400&type=square",
    "https://cataas.com/cat/qRbZwuXdbY8bYTSQ?width=400&height=400&type=square",
    "https://cataas.com/cat/mcjTt8SHwJWHFZw6?width=400&height=400&type=square",
    "https://cataas.com/cat/ohWvYNd6jSUTHrx4?width=400&height=400&type=square",
    "https://cataas.com/cat/nxxtDWRE2dbpfM4D?width=400&height=400&type=square",
    "https://cataas.com/cat/szIuEYxz2qJMXXyv?width=400&height=400&type=square",
    "https://cataas.com/cat/ajaON5dhPlJFXyG9?width=400&height=400&type=square",
    "https://cataas.com/cat/ShSauUmKo5niWBEt?width=400&height=400&type=square",
    "https://cataas.com/cat/pe70k3ftPwy34KsZ?width=400&height=400&type=square",
    "https://cataas.com/cat/DTzOtWOMagzssNRh?width=400&height=400&type=square",
    "https://cataas.com/cat/nzrzCnk0XJEieLzh?width=400&height=400&type=square",
    "https://cataas.com/cat/m5IV98pnZKsgPiSu?width=400&height=400&type=square",
    "https://cataas.com/cat/mrPYfaRfJqUmxHN0?width=400&height=400&type=square",
]


def cat_display_name(index: int) -> str:
    """1-based index → cat display name."""
    return CAT_NAMES[(index - 1) % len(CAT_NAMES)]


def cat_avatar_url(index: int) -> str:
    """1-based index → stable cat profile picture URL."""
    return CAT_AVATAR_URLS[(index - 1) % len(CAT_AVATAR_URLS)]
