import re
from collections.abc import Callable
from pathlib import Path

import yaml


def line_has_content(line: str) -> bool:
    return bool(line.split("#")[0].rstrip())


class TxtParser:
    @staticmethod
    def get_txt(file_path: Path) -> list[str]:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if lines:
            lines[0] = lines[0].removeprefix("\ufeff").removeprefix("\ufffe")
        return lines

    @staticmethod
    def match(lines: list[str], regex: re.Pattern[str]) -> list[list[str]]:
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


class YamlParser:
    @staticmethod
    def get_yaml(file_path: Path) -> dict:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data
