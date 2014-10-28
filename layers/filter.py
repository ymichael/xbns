class Filter(base.BaseLayer):
    """Filter layer.

    Used to enforce fake network topology.
    """
    def process_incoming(self, data, metadata=None):
        # TODO: Change this to reflect topology
        self.put_incoming(data, metadata)