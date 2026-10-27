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

    @staticmethod
    def get_sections(file_path: Path) -> dict[str, list[list[str]]]:
        """Parse a TSV file split into ``[name]`` blocks.

        ``#`` lines (the file header and the per-block column headers) and blank
        lines are skipped.  Only the line terminator is stripped from data rows,
        so a field may be empty or consist of whitespace.
        """
        sections: dict[str, list[list[str]]] = {}
        current: list[list[str]] | None = None
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\r\n")
                if not line.strip() or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    current = sections.setdefault(line[1:-1], [])
                    continue
                if current is None:
                    raise ValueError(f"{file_path.name}: data row outside a [section]: {line!r}")
                current.append(line.split("\t"))
        return sections
