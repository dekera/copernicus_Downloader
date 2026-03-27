from pathlib import Path
from typing import Optional
from zipfile import ZipFile

from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer

from .downloader import Downloader


class LayerLoader:
    """Baixa produtos e adiciona ao QGIS a melhor camada encontrada."""

    RASTER_EXTENSIONS = {".jp2", ".tif", ".tiff"}
    VECTOR_EXTENSIONS = {".gpkg", ".geojson", ".shp"}

    def __init__(self, iface, destination_folder: str, netrc_path: Optional[str] = None):
        # Mantemos a assinatura com iface para ficar alinhado ao plugin/QGIS e ao UML.
        self.iface = iface
        self.downloader = Downloader("copernicus", destination_folder, netrc_path)

    def download_product(self, product_name: str) -> str:
        return self.downloader.download_file(product_name)

    def load_downloaded_product(self, downloaded_path: str) -> str:
        path = Path(downloaded_path)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo baixado nao encontrado: {path}")

        # Resolve o caminho final a ser aberto, seja vindo de ZIP, pasta ou arquivo direto.
        source_path, layer_kind = self._resolve_source(path)

        if layer_kind == "raster":
            layer = QgsRasterLayer(str(source_path), source_path.stem)
            if not layer.isValid():
                raise RuntimeError(f"Falha ao carregar raster no QGIS: {source_path}")
            QgsProject.instance().addMapLayer(layer)
            return str(source_path)

        layer = QgsVectorLayer(str(source_path), source_path.stem, "ogr")
        if not layer.isValid():
            raise RuntimeError(f"Falha ao carregar vetor no QGIS: {source_path}")
        QgsProject.instance().addMapLayer(layer)
        return str(source_path)

    def _resolve_source(self, path: Path) -> tuple[Path, str]:
        if path.is_dir():
            search_root = path
        elif path.suffix.lower() == ".zip":
            search_root = self._extract_zip(path)
        else:
            return self._classify_direct_path(path)

        raster = self._find_best_raster(search_root)
        if raster is not None:
            return raster, "raster"

        vector = self._find_first_by_extension(search_root, self.VECTOR_EXTENSIONS)
        if vector is not None:
            return vector, "vector"

        raise FileNotFoundError(
            "Nao encontrei nenhum raster ou vetor compativel dentro do produto extraido."
        )

    def _classify_direct_path(self, path: Path) -> tuple[Path, str]:
        suffix = path.suffix.lower()
        if suffix in self.RASTER_EXTENSIONS:
            return path, "raster"
        if suffix in self.VECTOR_EXTENSIONS:
            return path, "vector"
        raise RuntimeError(f"Formato nao suportado para carregamento direto: {path.suffix}")

    def _extract_zip(self, zip_path: Path) -> Path:
        extract_dir = zip_path.parent / zip_path.stem
        extract_dir.mkdir(parents=True, exist_ok=True)
        with ZipFile(zip_path, "r") as zip_file:
            zip_file.extractall(extract_dir)
        return extract_dir

    def _find_best_raster(self, root: Path) -> Optional[Path]:
        # Entre todos os rasters do produto, escolhemos o mais adequado para abrir no QGIS.
        candidates = self._list_files_by_extension(root, self.RASTER_EXTENSIONS)
        if not candidates:
            return None
        return min(candidates, key=self._raster_sort_key)

    def _find_first_by_extension(self, root: Path, extensions: set[str]) -> Optional[Path]:
        candidates = self._list_files_by_extension(root, extensions)
        if not candidates:
            return None
        return candidates[0]

    def _list_files_by_extension(self, root: Path, extensions: set[str]) -> list[Path]:
        return sorted(
            (
                candidate
                for candidate in root.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() in extensions
            ),
            key=lambda current_path: str(current_path).lower(),
        )

    def _raster_sort_key(self, path: Path) -> tuple[int, int, str]:
        return (
            self._raster_priority(path),
            len(path.parts),
            str(path).lower(),
        )

    def _raster_priority(self, path: Path) -> int:
        normalized_path = str(path).replace("\\", "/").lower()
        normalized_name = path.name.lower()

        in_r10m_folder = "/img_data/r10m/" in normalized_path
        in_r20m_folder = "/img_data/r20m/" in normalized_path

        # A prioridade reflete a regra do trabalho: tentar abrir primeiro o TCI em 10 m.
        if normalized_name.endswith("_tci_10m.jp2"):
            return 0 if in_r10m_folder else 1
        if normalized_name.endswith("_tci_20m.jp2"):
            return 2 if in_r20m_folder else 3
        if normalized_name.endswith("_b04_10m.jp2"):
            return 4
        if normalized_name.endswith("_b03_10m.jp2"):
            return 5
        if normalized_name.endswith("_b02_10m.jp2"):
            return 6
        if normalized_name.endswith(".jp2"):
            return 7 if in_r10m_folder else 8
        if normalized_name.endswith(".tif") or normalized_name.endswith(".tiff"):
            return 9
        return 99
