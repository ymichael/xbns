import app.protocol.rateless_deluge
import app.deluge


class RatelessDeluge(app.deluge.Deluge):
    """Shell application to run the Deluge protocol."""
    ADDRESS = ("", 11003)

    @classmethod
    def create_protocol(cls):
        return app.protocol.rateless_deluge.RatelessDeluge()
