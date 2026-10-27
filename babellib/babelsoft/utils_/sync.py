import re
import time
from pathlib import Path

import requests
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from .dirs import Dirs


class UnicodeDataDownloader:
    console = Console()

    # unicode.org/Public root — used by sync_unicode to download a remote folder.
    UNICODE_BASE = "https://www.unicode.org/Public"

    # Extensions we keep (skip archives, PDFs and derived docs: zip/jar/gz/pdf/html).
    _KEEP_RE = re.compile(r"\.(?:txt|TXT|tsv|TSV)$")

    @classmethod
    def _ensure_folder(cls, folder: Path) -> None:
        """Create a folder if missing; never wipe existing data."""
        folder.mkdir(parents=True, exist_ok=True)

    #: unicode.org intermittently answers 502/503 and drops long transfers, so
    #: every request is retried a few times before the sync is abandoned.
    RETRIES = 4
    RETRY_DELAY = 3.0

    @classmethod
    def _get(cls, url: str, *, stream: bool = False, timeout: int = 600) -> requests.Response:
        """GET with backoff on transient failures; a 404 is returned to the caller."""
        last: Exception | None = None
        for attempt in range(1, cls.RETRIES + 1):
            try:
                response = requests.get(url, stream=stream, timeout=timeout)
                if response.status_code == 404:
                    return response
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last = exc
                if attempt == cls.RETRIES:
                    break
                cls.console.print(f"[yellow]  retry {attempt}/{cls.RETRIES - 1} after {type(exc).__name__}[/yellow]")
                time.sleep(cls.RETRY_DELAY * attempt)
        assert last is not None
        raise last

    @classmethod
    def _download(cls, url: str, output: Path, debug: bool = True, force: bool = False) -> None:
        if not force and output.exists() and output.stat().st_size > 0:
            if debug:
                print(f"    (skip, already downloaded) {output.name}")
            return
        output.parent.mkdir(parents=True, exist_ok=True)

        progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=cls.console,
            disable=not debug,
        )

        with progress:
            response = cls._get(url, stream=True)
            total_size = int(response.headers.get("content-length", 0))
            task = progress.add_task(f"Downloading {output.name}", total=total_size)

            with output.open("wb") as output_file:
                for chunk in response.iter_content(chunk_size=1024 * 64):
                    if not chunk:
                        continue
                    output_file.write(chunk)
                    progress.update(task, advance=len(chunk))

        if debug:
            cls.console.print(f"[green]Downloaded[/green] -> {output}")

    @classmethod
    def _dir_listing(cls, url: str) -> list[str]:
        """Return file names (no subdirs) for a plain unicode.org directory listing."""
        r = cls._get(url, timeout=120)
        if r.status_code == 404:  # a release that simply has no such folder
            return []
        names: list[str] = []
        for m in re.finditer(r"href=\"([^\"]+)\"", r.text):
            name = m.group(1)
            if name in (".", "..") or name.endswith("/"):
                continue
            names.append(name)
        return names

    @classmethod
    def _download_one(cls, url: str, dest: Path, debug: bool = True, force: bool = False) -> bool:
        """Download one file into dest.

        Idempotent: if dest already exists and is non-empty, it is skipped entirely
        (no network request at all).  Pass ``force=True`` to re-download anyway.
        Returns True if a download happened, False if skipped (already present).
        """
        if not force and dest.exists() and dest.stat().st_size > 0:
            if debug:
                print(f"    (skip, already downloaded) {dest.name}")
            return False
        r = cls._get(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        if debug:
            print(f"    {dest.name} ({len(r.content):,} B)")
        return True

    @classmethod
    def sync_ids(cls, debug: bool = True, force: bool = False) -> None:
        cls._ensure_folder(Dirs.BABELSTONE)
        ids_url: str = "https://www.babelstone.co.uk/CJK/IDS.TXT"
        cls.console.print("[bold yellow]=== Download IDS data ===")
        cls._download(url=ids_url, output=Dirs.BABELSTONE / "IDS.TXT", debug=debug, force=force)

    @classmethod
    def sync_ivd(cls, debug: bool = True, force: bool = False) -> None:
        """Download IVD (Ideographic Variation Database) data from unicode.org."""
        cls._ensure_folder(Dirs.IVD)
        base_url = "https://www.unicode.org/ivd/data/latest"
        files = ["IVD_Sequences.txt", "IVD_Collections.txt", "IVD_Stats.txt"]
        cls.console.print("[bold yellow]=== Download IVD data ===")
        for filename in files:
            cls._download(url=f"{base_url}/{filename}", output=Dirs.IVD / filename, debug=debug, force=force)

    @classmethod
    def sync_unicode(cls, folder: str, debug: bool = True, force: bool = False) -> None:
        """Download every keepable file under unicode.org/Public/<folder>/.

        Mirrors the remote folder into ``data/unicode/<folder>/``, skipping
        archives and derived docs (zip / jar / gz / pdf / html / …).

        Examples:
            sync_unicode("17.0.0/ucd")          # current UCD data files
            sync_unicode("17.0.0/ucd/unihan")   # Unihan split files
            sync_unicode("17.0.0/charts")       # charts
            sync_unicode("1.1-Update")          # a legacy "-Update" dir
            sync_unicode("reconstructed/1.0.0") # reconstructed 1.0.0 data
        """
        folder = folder.strip("/")
        remote = f"{cls.UNICODE_BASE}/{folder}"
        dest = Dirs.UNICODE / folder
        cls.console.print(f"[bold yellow]=== Download unicode.org/Public/{folder} ===")
        for name in cls._dir_listing(remote):
            if not cls._KEEP_RE.search(name):
                continue
            cls._download_one(f"{remote}/{name}", dest / name, debug=debug, force=force)

    # ── ISO 15924 script codes ────────────────────────────────────────────────
    ISO15924_URL = "https://www.unicode.org/iso15924/iso15924-codes.html"
    ISO15924_FILE = Dirs.DATA / "scripts" / "iso15924.tsv"
    # Matches the per-cell content of a data row: <td>…</td> / <td nowrap>…</td>
    _TD_RE = re.compile(r"<td[^>]*>(.*?)</td>")
    _TAG_RE = re.compile(r"<[^>]+>")

    @classmethod
    def sync_charts(cls, debug: bool = True, force: bool = False, version: str | None = None) -> None:
        """Download the code-chart index files (``RSIndex.txt``, ``Readme.txt``).

        ``unicode.org/Public/<version>/charts/`` serves an HTML page, not a folder
        listing, so ``sync_unicode`` cannot mirror it — the two text files the
        library reads are fetched directly.
        """
        version = version or Dirs.CURRENT
        cls._ensure_folder(Dirs.CHARTS)
        base = f"{cls.UNICODE_BASE}/{version}/charts"
        cls.console.print(f"[bold yellow]=== Download {base} (index files) ===")
        for name in ("RSIndex.txt", "Readme.txt"):
            cls._download_one(f"{base}/{name}", Dirs.CHARTS / name, debug=debug, force=force)

    @classmethod
    def sync_unihan(cls, debug: bool = True, force: bool = False, version: str | None = None) -> None:
        """Unihan is published as a single ``Unihan.zip``; extract it into ``ucd/unihan/``.

        ``sync_unicode`` cannot do this: it mirrors the *files* of a folder and
        explicitly skips archives.
        """
        import io
        import zipfile

        version = version or Dirs.CURRENT
        cls._ensure_folder(Dirs.UNIHAN)
        url = f"{cls.UNICODE_BASE}/{version}/ucd/Unihan.zip"
        marker = Dirs.UNIHAN / "Unihan_IRGSources.txt"
        if not force and marker.is_file():
            if debug:
                print(f"    (skip, already extracted) {url}")
            return
        cls.console.print(f"[bold yellow]=== Download {url} ===")
        response = cls._get(url)
        target = Dirs.UNIHAN.resolve()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            for member in archive.namelist():
                # Guard against entries that would land outside the target
                # (zip-slip); zipfile's own "data" filter needs Python 3.12.
                if not (target / member).resolve().is_relative_to(target):
                    raise ValueError(f"refusing to extract {member!r} outside {target}")
                archive.extract(member, target)
        if debug:
            cls.console.print(f"[green]Extracted[/green] {url} -> {Dirs.UNIHAN}")

    @classmethod
    def sync_iso15924(cls, debug: bool = True) -> None:
        """Download & parse the ISO 15924 Alphabetical Code List → iso15924.tsv.

        Source: https://www.unicode.org/iso15924/iso15924-codes.html
        The page is a single HTML table with columns:
            Code  N°  English Name  Nom français  Alias  Age  Date
        Written (tab-separated) to data/scripts/iso15924.tsv.
        """
        cls._ensure_folder(cls.ISO15924_FILE.parent)
        cls.console.print("[bold yellow]=== Download ISO 15924 code list ===")
        html = cls._get(cls.ISO15924_URL, timeout=120).text

        rows: list[list[str]] = []
        for raw in re.findall(r"<tr>(.*?)</tr>", html, flags=re.DOTALL):
            cells = [cls._clean_td(m) for m in cls._TD_RE.findall(raw)]
            if len(cells) != 7 or not cells[0] or cells[0] == "Code":
                continue
            rows.append(cells)

        # Keep a stable alphabetical order by code.
        rows.sort(key=lambda r: r[0])
        lines = [
            "# BabelSoft Data: ISO 15924 script codes (Alphabetical Code List)",
            "# Source: https://www.unicode.org/iso15924/iso15924-codes.html",
            "# Fields: code\\tnumber\\tenglish_name\\tfrench_name\\talias\\tage\\tdate",
        ]
        lines += ["\t".join(cells) for cells in rows]
        text = "\n".join(lines) + "\n"
        cls.ISO15924_FILE.write_text(text, encoding="utf-8")
        if debug:
            cls.console.print(f"[green]Parsed {len(rows)} scripts[/green] -> {cls.ISO15924_FILE}")

    @classmethod
    def _clean_td(cls, cell: str) -> str:
        """Strip tags, decode &nbsp;, collapse whitespace inside one <td> cell."""
        return re.sub(r"\s+", " ", cls._TAG_RE.sub("", cell)).replace("&nbsp;", " ").strip()


if __name__ == "__main__":
    import sys

    folder = sys.argv[1] if len(sys.argv) > 1 else f"{Dirs.CURRENT}/ucd"
    UnicodeDataDownloader.sync_unicode(folder)
    UnicodeDataDownloader.sync_ids()
    UnicodeDataDownloader.sync_ivd()
    UnicodeDataDownloader.sync_iso15924()
