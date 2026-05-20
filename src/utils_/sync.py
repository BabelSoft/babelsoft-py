import zipfile
from pathlib import Path
from shutil import rmtree

import requests
from dirs import Dirs
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn, TransferSpeedColumn


class UnicodeDataDownloader:
    console = Console()

    @classmethod
    def _initialize_folder(cls, folder: Path) -> None:
        if folder.exists():
            rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _download(cls, url: str, output: Path, debug: bool = True) -> None:
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
            response = requests.get(url, stream=True, timeout=600)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            task = progress.add_task(f"Downloading {output.name}", total=total_size)

            with output.open("wb") as output_file:
                for chunk in response.iter_content(chunk_size=1024 * 64):
                    if not chunk:
                        continue
                    output_file.write(chunk)
                    progress.update(task, advance=len(chunk))

        if debug:
            cls.console.print(f"✅ [green]Downloaded[/green] → {output}")

    @classmethod
    def _extract_zip(cls, zip_path: Path, output_dir: Path, show_progress: bool = True, txt_only: bool = False) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)

        progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=cls.console,
            disable=not show_progress,
        )

        with progress:
            with zipfile.ZipFile(zip_path) as zf:
                members = [
                    member
                    for member in zf.infolist()
                    if not member.is_dir() and (not txt_only or member.filename.endswith(".txt"))
                ]

                task = progress.add_task("Extracting files", total=len(members))

                for member in members:
                    dest_path = output_dir / member.filename
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    with zf.open(member) as source, dest_path.open("wb") as target:
                        target.write(source.read())

                    progress.advance(task)

        if show_progress:
            cls.console.print(f"✅ [green]Extracted[/green] → {output_dir}")

    @classmethod
    def _download_and_extract_zip(
        cls, url: str, output: Path, debug: bool = True, txt_only: bool = False, delete_zip: bool = True
    ) -> None:
        output.mkdir(parents=True, exist_ok=True)
        zip_path = output / Path(url).name

        cls._download(url=url, output=zip_path, debug=debug)
        cls._extract_zip(zip_path=zip_path, output_dir=output, show_progress=debug, txt_only=txt_only)

        if delete_zip and zip_path.exists():
            zip_path.unlink()
            if debug:
                cls.console.print(f"🗑️  [yellow]Deleted zip[/yellow] → {zip_path}")

    @classmethod
    def _download_and_extract_txt_only(cls, url: str, output: Path, debug: bool = True) -> None:
        cls._download_and_extract_zip(url=url, output=output, debug=debug, txt_only=True, delete_zip=True)

    @classmethod
    def sync_ucd(cls, debug: bool = True) -> None:
        cls._initialize_folder(Dirs.UCD)
        ucd_url: str = "https://www.unicode.org/Public/latest/ucd/UCD.zip"
        cls.console.print("[bold yellow]=== Download UCD data ===")
        cls._download_and_extract_txt_only(url=ucd_url, output=Dirs.UCD, debug=debug)

    @classmethod
    def sync_unihan(cls, debug: bool = True) -> None:
        cls._initialize_folder(Dirs.UNIHAN)
        unihan_url: str = "https://www.unicode.org/Public/latest/ucd/Unihan.zip"
        cls.console.print("[bold yellow]=== Download Unihan data ===")
        cls._download_and_extract_txt_only(url=unihan_url, output=Dirs.UNIHAN, debug=debug)

    @classmethod
    def sync_ids(cls, debug: bool = True) -> None:
        cls._initialize_folder(Dirs.BABELSTONE)
        ids_url: str = "https://www.babelstone.co.uk/CJK/IDS.TXT"
        cls.console.print("[bold yellow]=== Download IDS data ===")
        cls._download(url=ids_url, output=Dirs.BABELSTONE / "IDS.TXT", debug=debug)

    @classmethod
    def sync_charts(cls, debug: bool = True) -> None:
        cls._initialize_folder(Dirs.CHARTS)
        charts_url: str = "https://www.unicode.org/Public/latest/charts/RSIndex.txt"
        cls.console.print("[bold yellow]=== Download charts data ===")
        cls._download(url=charts_url, output=Dirs.CHARTS / "RSIndex.txt", debug=debug)


if __name__ == "__main__":
    UnicodeDataDownloader.sync_ucd()
    UnicodeDataDownloader.sync_unihan()
    UnicodeDataDownloader.sync_ids()
    UnicodeDataDownloader.sync_charts()
