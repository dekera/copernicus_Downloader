from typing import Optional

from .copernicus_api import CopernicusDownloader


class Downloader:
    """Adaptador para manter a classe Downloader do UML usando o motor real do Copernicus."""

    def __init__(
        self,
        server_url_format: str,
        destination_folder: str,
        netrc_path: Optional[str] = None,
    ):
        self.server_url_format = server_url_format
        self.destination_folder = destination_folder
        self.netrc_path = netrc_path
        self._copernicus = CopernicusDownloader(
            pasta_destino=destination_folder,
            netrc_path=netrc_path,
        )

    def download_file(self, name: str) -> str:
        # O adaptador so repassa a operacao para a implementacao concreta da API.
        return str(self._copernicus.download(name))
