import zipfile
from io import BytesIO
from pathlib import Path
from shutil import rmtree

import requests
from rich.console import Console
from rich.progress import (BarColumn, DownloadColumn, Progress, TextColumn,
                           TimeRemainingColumn, TransferSpeedColumn)

from utils_.paths import DATA_UCD_DIR, DATA_UNIHAN_DIR


class UnicodeDataDownloader:
    DATA_UCD_URL: str = "https://www.unicode.org/Public/latest/ucd/UCD.zip"
    DATA_UNIHAN_URL: str = "https://www.unicode.org/Public/latest/ucd/Unihan.zip"

    console = Console()

    @classmethod
    def _initialize_directories(cls, folder: Path) -> None:
        rmtree(folder)
        folder.mkdir(exist_ok=True)

    @classmethod
    def _download_and_extract_txt_only(
        cls, url: str, output_dir: Path, show_progress: bool = True
    ) -> None:
        output_dir.mkdir(exist_ok=True)

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
            resp = requests.get(url, stream=True, timeout=600)
            resp.raise_for_status()
            total_size = int(resp.headers.get("content-length", 0))

            task = progress.add_task(url.split("/")[-1], total=total_size)

            zip_data = BytesIO()
            for chunk in resp.iter_content(chunk_size=1024 * 64):
                zip_data.write(chunk)
                progress.update(task, advance=len(chunk))

            with zipfile.ZipFile(zip_data) as zf:
                txt_files = [
                    f
                    for f in zf.infolist()
                    if not f.is_dir() and f.filename.endswith(".txt")
                ]

                extract_task = progress.add_task(
                    "Extracting .txt files", total=len(txt_files)
                )

                for file_info in txt_files:
                    dest_path = output_dir / file_info.filename
                    dest_path.parent.mkdir(exist_ok=True)

                    with zf.open(file_info) as source, dest_path.open("wb") as f:
                        f.write(source.read())

                    progress.advance(extract_task)

        if show_progress:
            cls.console.print(f"✅ [green]Finished[/green] → {output_dir}")

    @classmethod
    def download_all_ucd_data(cls, show_progress: bool = True) -> None:
        cls._initialize_directories(DATA_UCD_DIR)
        cls._initialize_directories(DATA_UNIHAN_DIR)

        cls.console.print("[bold yellow]=== Download UCD data ===")
        cls._download_and_extract_txt_only(
            url=cls.DATA_UCD_URL,
            output_dir=DATA_UCD_DIR,
            show_progress=show_progress,
        )

        cls.console.print("[bold yellow]=== Download Unihan data ===")
        cls._download_and_extract_txt_only(
            url=cls.DATA_UNIHAN_URL,
            output_dir=DATA_UNIHAN_DIR,
            show_progress=show_progress,
        )


if __name__ == "__main__":
    UnicodeDataDownloader.download_all_ucd_data()
