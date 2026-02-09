"""
Direkter Download mit httpx.
Lädt Dateien parallel oder sequentiell herunter.
"""

import asyncio
from pathlib import Path
from dataclasses import dataclass
import httpx

from .browser import SongDownloadLinks


DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"


@dataclass
class DownloadResult:
    """Ergebnis eines Downloads."""
    song_name: str
    format_type: str
    success: bool
    file_path: Path | None = None
    error: str | None = None
    file_size_mb: float = 0.0


class TuneeDownloader:
    """Direkter Download der extrahierten URLs."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or DOWNLOADS_DIR
        self.output_dir.mkdir(exist_ok=True)

    def _get_extension(self, format_type: str) -> str:
        """Gibt die Dateiendung für ein Format zurück."""
        extensions = {
            'mp3': '.mp3',
            'raw': '.flac',
            'video': '.mp4',
            'lrc': '.lrc'
        }
        return extensions.get(format_type, '')

    def _sanitize_filename(self, name: str) -> str:
        """Bereinigt Dateinamen von ungültigen Zeichen."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()

    async def download_file(
        self,
        url: str,
        song_name: str,
        format_type: str,
        cookies: list[dict] | None = None
    ) -> DownloadResult:
        """
        Lädt eine einzelne Datei herunter.
        """
        if not url:
            return DownloadResult(
                song_name=song_name,
                format_type=format_type,
                success=False,
                error="Keine URL vorhanden"
            )

        # Erstelle Song-Ordner
        safe_name = self._sanitize_filename(song_name)
        song_dir = self.output_dir / safe_name
        song_dir.mkdir(exist_ok=True)

        # Dateiname
        extension = self._get_extension(format_type)
        filename = f"{safe_name}{extension}"
        filepath = song_dir / filename

        try:
            # Cookies für httpx vorbereiten
            httpx_cookies = {}
            if cookies:
                for cookie in cookies:
                    httpx_cookies[cookie['name']] = cookie['value']

            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=120.0,
                cookies=httpx_cookies
            ) as client:
                print(f"    Downloading {format_type.upper()}...")

                response = await client.get(url)
                response.raise_for_status()

                # Speichere Datei
                with open(filepath, 'wb') as f:
                    f.write(response.content)

                file_size = filepath.stat().st_size / (1024 * 1024)
                print(f"    {format_type.upper()}: {file_size:.2f} MB")

                return DownloadResult(
                    song_name=song_name,
                    format_type=format_type,
                    success=True,
                    file_path=filepath,
                    file_size_mb=file_size
                )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            print(f"    {format_type.upper()} fehlgeschlagen: {error_msg}")
            return DownloadResult(
                song_name=song_name,
                format_type=format_type,
                success=False,
                error=error_msg
            )
        except Exception as e:
            print(f"    {format_type.upper()} fehlgeschlagen: {e}")
            return DownloadResult(
                song_name=song_name,
                format_type=format_type,
                success=False,
                error=str(e)
            )

    async def download_song(
        self,
        links: SongDownloadLinks,
        cookies: list[dict] | None = None,
        formats: list[str] | None = None
    ) -> list[DownloadResult]:
        """
        Lädt alle Formate für einen Song herunter.
        Reihenfolge: MP3, RAW, LRC, VIDEO
        """
        if formats is None:
            formats = ['mp3', 'raw', 'lrc', 'video']

        results = []

        url_map = {
            'mp3': links.mp3_url,
            'raw': links.raw_url,
            'video': links.video_url,
            'lrc': links.lrc_url
        }

        for format_type in formats:
            url = url_map.get(format_type)
            result = await self.download_file(
                url=url,
                song_name=links.name,
                format_type=format_type,
                cookies=cookies
            )
            results.append(result)

            # Kleine Pause zwischen Downloads
            await asyncio.sleep(0.5)

        return results

    async def download_all_songs(
        self,
        all_links: list[SongDownloadLinks],
        cookies: list[dict] | None = None,
        formats: list[str] | None = None
    ) -> dict:
        """
        Lädt alle Songs herunter.
        Gibt Zusammenfassung zurück.
        """
        total_results = {
            'success': 0,
            'failed': 0,
            'total_size_mb': 0.0,
            'songs': []
        }

        for idx, links in enumerate(all_links, 1):
            print(f"\n[{idx}/{len(all_links)}] {links.name}")

            results = await self.download_song(links, cookies, formats)

            song_summary = {
                'name': links.name,
                'downloads': []
            }

            for result in results:
                song_summary['downloads'].append({
                    'format': result.format_type,
                    'success': result.success,
                    'file': str(result.file_path) if result.file_path else None,
                    'size_mb': result.file_size_mb,
                    'error': result.error
                })

                if result.success:
                    total_results['success'] += 1
                    total_results['total_size_mb'] += result.file_size_mb
                else:
                    total_results['failed'] += 1

            total_results['songs'].append(song_summary)

        return total_results
