import re
from collections.abc import Callable, Iterable
from pathlib import Path

_HEX_CODEPOINT = re.compile(r"^(?:[Uu]\+|0[xX])?([0-9A-Fa-f]{1,6})$")


def line_has_content(line: str) -> bool:
    return bool(line.split("#")[0].rstrip())


def parse_codepoint(value: str) -> int:
    """Parse a hexadecimal code point field.

    Accepts the ``U+4E00``, ``0x4E00`` and bare ``4E00`` spellings and raises
    ``ValueError`` for anything else, so a malformed data row is reported
    instead of silently turning into code point 0.
    """
    match = _HEX_CODEPOINT.match(value.strip())
    if not match:
        raise ValueError(f"invalid code point: {value!r}")
    return int(match.group(1), 16)


class TxtParser:
    @staticmethod
    def get_txt(file_path: Path) -> list[str]:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if lines:
            lines[0] = lines[0].removeprefix("\ufeff").removeprefix("\ufffe")
        return lines

    @staticmethod
    def match(lines: Iterable[str], regex: re.Pattern[str]) -> list[list[str]]:
        parsed: list[list[str]] = []
        for line in lines:
            result = regex.match(line)
            if not result:
                continue
            groups = result.groups()
            parsed.append([str(groups[i]) for i in range(len(groups))])
        return parsed

    @staticmethod
    def filter(lines: list[str], func: Callable[[str], bool]) -> list[str]:
        return list(filter(func, lines))


class TsvParser:
    """Parse TSV files with comment lines (starting with #)."""

    @staticmethod
    def get_tsv(file_path: Path) -> list[list[str]]:
        rows: list[list[str]] = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                rows.append(line.split("\t"))
        return rows
