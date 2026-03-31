from typing import Optional

from pathlib import Path

from qgis.PyQt.QtCore import QObject, Qt, QThread, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from qgis.PyQt.uic import loadUi

from .downloader import Downloader
from .layer_loader import LayerLoader


class DownloadWorker(QObject):
    # O worker executa o download fora da thread da interface para nao travar o QGIS.
    finished = pyqtSignal()
    success = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, product_name: str, destination_folder: str, netrc_path: str) -> None:
        super().__init__()
        self.product_name = product_name
        self.destination_folder = destination_folder
        self.netrc_path = netrc_path

    def run(self) -> None:
        try:
            downloader = Downloader(
                server_url_format="copernicus",
                destination_folder=self.destination_folder,
                netrc_path=self.netrc_path,
            )
            path = downloader.download_file(self.product_name)
            self.success.emit(str(path))
        except Exception as exc:  # pragma: no cover - ambiente QGIS
            self.error.emit(str(exc))
        finally:
            self.finished.emit()


class RasterSelectionDialog(QDialog):
    """Dialogo simples para o usuario escolher qual raster carregara no QGIS."""

    def __init__(self, raster_paths: list[Path], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Escolher raster")
        self.resize(720, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Selecione o raster que deseja carregar no QGIS."))

        self.raster_list = QListWidget(self)
        for raster_path in raster_paths:
            item = QListWidgetItem(self._build_item_label(raster_path))
            item.setData(Qt.UserRole, str(raster_path))
            item.setToolTip(str(raster_path))
            self.raster_list.addItem(item)

        if self.raster_list.count() > 0:
            self.raster_list.setCurrentRow(0)

        layout.addWidget(self.raster_list)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def selected_raster_path(self) -> Optional[Path]:
        current_item = self.raster_list.currentItem()
        if current_item is None:
            return None
        return Path(current_item.data(Qt.UserRole))

    def _build_item_label(self, raster_path: Path) -> str:
        tail_parts = raster_path.parts[-4:]
        return "/".join(tail_parts)


class CopernicusDownloaderWindow(QMainWindow):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.plugin_dir = Path(__file__).resolve().parent
        self.ui_path = self.plugin_dir / "janela1.ui"
        loadUi(str(self.ui_path), self)

        self.thread_download = None
        self.worker = None
        self.destination_folder = str(Path.home() / "Downloads")
        self.netrc_path = str(Path.home() / ".netrc")

        self._inject_extra_controls()
        self._configure_defaults()
        self._connect_signals()

    def _inject_extra_controls(self) -> None:
        self.pushButtonEscolherPasta = QPushButton("Escolher pasta...")
        self.gridLayoutDownload.addWidget(self.pushButtonEscolherPasta, 1, 2)

    def _configure_defaults(self) -> None:
        self.setWindowTitle("Downloader Copernicus")
        self.lineEditNomeImagem.setPlaceholderText(
            "Ex.: S2A_MSIL2A_20220503T130251_N0510_R095_T23KPS_20241129T025850"
        )
        self.labelTitulo.setText("Downloader Copernicus para QGIS")
        self.labelDescricao.setText(
            "Informe o nome do produto Copernicus. O plugin baixa o ZIP, extrai o produto "
            "e permite escolher qual raster carregar no projeto."
        )
        self.labelPastaTitulo.setText("Pasta de destino")
        self.labelPastaDestino.setText(self.destination_folder)
        self.labelNetrcTitulo.setText("Arquivo .netrc")
        self.labelNetrc.setText(self.netrc_path)
        self.labelStatus.setText("Pronto para iniciar.")
        self.plainTextEditLog.clear()

    def _connect_signals(self) -> None:
        self.pushButtonDownload.clicked.connect(self.iniciar_download)
        self.lineEditNomeImagem.returnPressed.connect(self.iniciar_download)
        self.pushButtonEscolherPasta.clicked.connect(self.escolher_pasta)

    def reset_defaults(self) -> None:
        self.lineEditNomeImagem.clear()
        self._configure_defaults()

    def escolher_pasta(self) -> None:
        pasta = QFileDialog.getExistingDirectory(
            self,
            "Escolha a pasta de destino",
            self.destination_folder,
        )
        if pasta:
            self.destination_folder = pasta
            self.labelPastaDestino.setText(pasta)
            self._add_log(f"Nova pasta de destino: {pasta}")

    def iniciar_download(self) -> None:
        nome_imagem = self.lineEditNomeImagem.text().strip()
        if not nome_imagem:
            self._mostrar_erro("Informe o nome do produto Copernicus antes de iniciar o download.")
            return

        self.pushButtonDownload.setEnabled(False)
        self.labelStatus.setText("Baixando produto...")
        self.plainTextEditLog.clear()
        self._add_log(f"Produto informado: {nome_imagem}")
        self._add_log(f"Pasta de destino: {self.destination_folder}")
        self._add_log(f"Arquivo .netrc: {self.netrc_path}")

        self.thread_download = QThread()
        self.worker = DownloadWorker(nome_imagem, self.destination_folder, self.netrc_path)
        self.worker.moveToThread(self.thread_download)

        # O worker faz o download na thread secundaria; os sinais voltam para a janela.
        self.thread_download.started.connect(self.worker.run)
        self.worker.success.connect(self._download_concluido)
        self.worker.error.connect(self._mostrar_erro)
        self.worker.finished.connect(self.thread_download.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread_download.finished.connect(self._finalizar_download)
        self.thread_download.finished.connect(self.thread_download.deleteLater)

        self.thread_download.start()

    def _download_concluido(self, downloaded_path: str) -> None:
        self._add_log(f"Arquivo baixado: {downloaded_path}")
        self.labelStatus.setText("Download concluido. Preparando selecao da camada...")

        try:
            loader = LayerLoader(
                self.iface,
                destination_folder=self.destination_folder,
                netrc_path=self.netrc_path,
            )

            raster_candidates = loader.list_raster_candidates(downloaded_path)
            if raster_candidates:
                selected_raster = self._select_raster(raster_candidates)
                if selected_raster is None:
                    self.labelStatus.setText("Carregamento cancelado pelo usuario.")
                    self._add_log("Nenhum raster foi carregado.")
                    return

                # O carregamento da camada acontece na interface principal, onde o QGIS pode
                # manipular o projeto com seguranca.
                loaded_source = loader.load_raster_source(selected_raster)
            else:
                loaded_source = loader.load_downloaded_product(downloaded_path)

            self.labelStatus.setText("Camada adicionada ao projeto com sucesso.")
            self._add_log(f"Camada carregada a partir de: {loaded_source}")
        except Exception as exc:
            self._mostrar_erro(str(exc))

    def _mostrar_erro(self, mensagem: str) -> None:
        self.labelStatus.setText("Ocorreu um erro durante o processo.")
        self._add_log(f"Erro: {mensagem}")
        QMessageBox.critical(self, "Erro", mensagem)

    def _finalizar_download(self) -> None:
        self.pushButtonDownload.setEnabled(True)
        self.worker = None
        self.thread_download = None

    def _add_log(self, mensagem: str) -> None:
        self.plainTextEditLog.appendPlainText(mensagem)

    def _select_raster(self, raster_candidates: list[Path]) -> Optional[Path]:
        self._add_log(f"Rasters encontrados: {len(raster_candidates)}")
        dialog = RasterSelectionDialog(raster_candidates, self)
        if dialog.exec_() != QDialog.Accepted:
            return None

        selected_raster = dialog.selected_raster_path()
        if selected_raster is not None:
            self._add_log(f"Raster escolhido: {selected_raster}")
        return selected_raster
