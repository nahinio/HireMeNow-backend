from enum import Enum


def enum_to_str(value: Enum | str) -> str:
    if isinstance(value, Enum):
        return value.value
    return str(value)
