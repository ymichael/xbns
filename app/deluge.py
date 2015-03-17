import app.protocol.deluge
import app.data_dissemination


class Deluge(app.data_dissemination.DataDissemination):
    """Shell application to run the Deluge protocol."""
    ADDRESS = ("", 11002)

    @classmethod
    def create_protocol(cls):
        return app.protocol.deluge.Deluge()

    def _handle_incoming_dissemination(self, data):
        pass
