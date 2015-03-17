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

    # TODO.
    # Delegate the following attributes.
    DELEGATE_TO_PROTOCOL = [
        'stop',
        'get_data',
        'new_version',
    ]
    def __getattr__(self, name):
        if hasattr(self.protocol, name) and name in self.DELEGATE_TO_PROTOCOL:
            return getattr(self.protocol, name)
        raise AttributeError("%r object has no attribute %r" % (self.__class__, name))
