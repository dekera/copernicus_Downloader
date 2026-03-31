import netrc
from pathlib import Path
from typing import Optional

import requests


class CopernicusDownloader:
    """Motor de download do Copernicus Data Space Ecosystem."""

    TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    CATALOGUE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    DOWNLOAD_URL = "https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
    CLIENT_ID = "cdse-public"
    TIMEOUT = 120
    CHUNK_SIZE = 20 * 1024 * 1024

    def __init__(
        self,
        pasta_destino: str,
        netrc_path: Optional[str] = None,
        machine_name: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.pasta_destino = Path(pasta_destino)
        self.pasta_destino.mkdir(parents=True, exist_ok=True)
        self.netrc_path = Path(netrc_path or Path.home() / ".netrc")
        self.machine_name = machine_name or self.TOKEN_URL
        self.session = session or requests.Session()

    def download(self, nome_imagem: str) -> Path:
        nome_consulta = nome_imagem.strip()
        if not nome_consulta:
            raise ValueError("O nome da imagem nao pode ser vazio.")

        # O fluxo da API e: localizar o produto, autenticar e so entao baixar o ZIP.
        produto = self._buscar_produto(nome_consulta)
        token = self._obter_token()

        nome_arquivo = f"{produto['Name']}.zip"
        caminho_saida = self.pasta_destino / nome_arquivo
        url_download = self.DOWNLOAD_URL.format(product_id=produto["Id"])

        with self.session.get(
            url_download,
            headers={"Authorization": f"Bearer {token}"},
            stream=True,
            timeout=self.TIMEOUT,
        ) as response:
            response.raise_for_status()
            with caminho_saida.open("wb") as arquivo:
                for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                    if chunk:
                        arquivo.write(chunk)

        return caminho_saida

    def _obter_token(self) -> str:
        usuario, senha = self._ler_credenciais()
        response = self.session.post(
            self.TOKEN_URL,
            data={
                "client_id": self.CLIENT_ID,
                "grant_type": "password",
                "username": usuario,
                "password": senha,
            },
            timeout=self.TIMEOUT,
        )
        response.raise_for_status()

        access_token = response.json().get("access_token")
        if not access_token:
            raise RuntimeError("A resposta de autenticacao nao trouxe access_token.")
        return access_token

    def _ler_credenciais(self) -> tuple[str, str]:
        if not self.netrc_path.exists():
            raise FileNotFoundError(f"Arquivo .netrc nao encontrado em: {self.netrc_path}")

        parser_netrc = netrc.netrc(str(self.netrc_path))
        credenciais = parser_netrc.authenticators(self.machine_name)
        if credenciais is None:
            credenciais = parser_netrc.authenticators("identity.dataspace.copernicus.eu")

        if credenciais is None:
            raise RuntimeError(
                "Nao encontrei credenciais no .netrc para o endpoint da Copernicus."
            )

        login, _, password = credenciais
        if not login or not password:
            raise RuntimeError("As credenciais no .netrc estao incompletas.")
        return login, password

    def _buscar_produto(self, nome_imagem: str) -> dict:
        nomes_consulta = [nome_imagem]
        if not nome_imagem.endswith(".SAFE"):
            nomes_consulta.append(f"{nome_imagem}.SAFE")

        for nome_consulta in nomes_consulta:
            filtro = f"Name eq '{self._escapar_valor_odata(nome_consulta)}'"
            response = self.session.get(
                self.CATALOGUE_URL,
                params={
                    "$filter": filtro,
                    "$select": "Id,Name,Online,ContentLength",
                    "$top": 2,
                },
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()

            produtos = response.json().get("value", [])
            if not produtos:
                continue

            if len(produtos) > 1:
                raise RuntimeError(
                    f"A busca por '{nome_consulta}' retornou mais de um produto, revise o filtro."
                )

            produto = produtos[0]
            if produto.get("Online") is False:
                raise RuntimeError(
                    f"O produto '{nome_consulta}' existe, mas nao esta online para download."
                )
            return produto

        raise FileNotFoundError(
            "Produto nao encontrado no catalogo Copernicus: "
            f"{', '.join(nomes_consulta)}"
        )

    @staticmethod
    def _escapar_valor_odata(valor: str) -> str:
        return valor.replace("'", "''")
