import re
from pathlib import Path


class TxtParser:
    @staticmethod
    def get_txt_lines(file_path: Path) -> list[str]:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        lines = [line.rstrip() for line in lines if not line.startswith("#") and line]
        return lines

    @staticmethod
    def parse_txt_lines(lines: list[str], regex: re.Pattern[str]) -> list[list[str]]:
        parsed: list[list[str]] = []
        for line in lines:
            result = regex.match(line)
            if not result:
                continue
            groups = result.groups()
            parsed.append([str(groups[i]) for i in range(len(groups))])
        return parsed
