from PyQt6.QtNetwork import QLocalServer, QLocalSocket


SERVER_NAME = "IAinvicibleApp_SingleInstance_v1"


class SingleInstanceGuard:
    """Garantiza una sola instancia de la app.

    - acquire() devuelve True si esta instancia es la unica (y crea el servidor).
    - Si ya hay otra corriendo, le envia un mensaje "show" y devuelve False.
    - La primera instancia establece on_show para mostrarse/focalizarse.
    """

    def __init__(self, server_name: str = SERVER_NAME):
        self.server_name = server_name
        self._server = None
        self.on_show = None

    def acquire(self) -> bool:
        client = QLocalSocket()
        client.connectToServer(self.server_name)
        if client.waitForConnected(300):
            client.write(b"show")
            client.waitForBytesWritten(300)
            client.disconnectFromServer()
            return False

        client.abort()
        QLocalServer.removeServer(self.server_name)

        self._server = QLocalServer()
        self._server.newConnection.connect(self._on_new_connection)
        return self._server.listen(self.server_name)

    def _on_new_connection(self):
        conn = self._server.nextPendingConnection()
        if conn is None:
            return
        conn.readyRead.connect(lambda: self._handle_show(conn))

    def _handle_show(self, conn):
        try:
            data = bytes(conn.readAll().data())
            if data and b"show" in data and self.on_show:
                self.on_show()
        except Exception:
            pass
        try:
            conn.disconnectFromServer()
        except Exception:
            pass

    def close(self):
        if self._server is not None:
            try:
                self._server.close()
            except Exception:
                pass
            self._server = None