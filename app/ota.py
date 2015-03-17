import app.protocol.deluge
import app.data_dissemination
import argparse
import net.layers.base
import time
import utils.git
import utils.pdu



class OTAPDU(utils.pdu.PDU):
    TYPES = [
        "ADV",
        "ACK",
        "FLOOD",
        "PATCH",
        "STOP",
    ]

    def _init_adv(self):
        self.rev = self.message

    def _init_patch(self):
        self.from_rev = self.message[:7]
        self.to_rev = self.message[7:14]
        self.patch = self.message[14:]

    def _repr_adv(self):
        return "%s, %s" % (self.type, self.rev)

    def _repr_patch(self):
        return "%s, from = %s, to = %s, size = %s" % \
            (self.type, self.from_rev, self.to_rev, len(self.patch))

    @classmethod
    def create_patch(cls, from_rev, to_rev, patch):
        return cls(cls.PATCH, "".join([from_rev, to_rev, patch]))


class Mode(object):
    NORMAL = "normal"
    UPGRADE = "upgrade"
    STOP = "stop"


class OTA(app.data_dissemination.DataDissemination):
    """Shell application to run the Deluge protocol."""
    ADDRESS = ("", 11007)

    def __init__(self, addr, protocol=None):
        super(OTA, self).__init__(addr, protocol)
        self.mode = Mode.NORMAL
        self.earliest_revision = None
        # Address of node that sent the last flood.
        self.seed_addr = None

    def set_mode(self, mode):
        self.mode = mode

    @classmethod
    def create_protocol(cls):
        # Configure
        app.protocol.deluge.Deluge.PAGE_SIZE = 6000
        app.protocol.deluge.Deluge.PACKET_SIZE = 60
        app.protocol.deluge.Deluge.PACKETS_PER_PAGE = 6000 / 60
        app.protocol.deluge.Deluge.T_MIN = 2
        return app.protocol.deluge.Deluge()

    def _handle_incoming_message(self, data, sender_addr):
        ota_pdu = OTAPDU.from_string(data)
        self._log_receive_pdu(ota_pdu, sender_addr)
        if ota_pdu.is_adv() and self.mode == Mode.UPGRADE:
            # Based on the ADV, figure out the earliest revision.
            assert utils.git.has_revision(ota_pdu.rev)
            if self.earliest_revision is None:
                self.earliest_revision = ota_pdu.rev
            elif ota_pdu.rev != self.earliest_revision:
                adv_date = utils.git.get_revision_date(ota_pdu.rev)
                curr_date = utils.git.get_revision_date(self.earliest_revision)
                if adv_date < curr_date:
                    self.earliest_revision = ota_pdu.rev
            self.log("Current earliest revision: %s" % self.earliest_revision)

        if ota_pdu.is_flood() and self.mode == Mode.NORMAL:
            self.start_protocol()
            self.seed_addr = sender_addr
            self._send_adv(sender_addr)

        if ota_pdu.is_stop() and self.mode == Mode.NORMAL:
            self.stop_protocol()
            self._send_ack(sender_addr)

    def _send_adv(self, dest_addr):
        ota_pdu = OTAPDU.create_adv(utils.git.get_current_revision())
        self._send_pdu_to_app(ota_pdu, dest_addr)

    def _send_ack(self, dest_addr):
        self._send_pdu_to_app(OTAPDU.create_ack(), dest_addr)

    def _send_flood(self):
        self._send_pdu_to_app(
            OTAPDU.create_flood(), dest_addr=net.layers.base.FLOOD_ADDRESS)

    def _send_stop(self):
        self._send_pdu_to_app(
            OTAPDU.create_stop(), dest_addr=net.layers.base.FLOOD_ADDRESS)

    def _send_pdu_to_app(self, ota_pdu, dest_addr):
        self._log_send_pdu(ota_pdu)
        self._send_to_app(ota_pdu.to_string(), dest_addr=dest_addr)

    def _send_patch(self, version=None):
        if self.earliest_revision is None:
            self.log("No earliest revision. Unable to send patch.")
            return
        to_rev = utils.git.get_current_revision()
        if self.earliest_revision == to_rev:
            self.log("Earliest revision is up-to-date. No patch required.")
            return
        from_rev = self.earliest_revision
        patch = utils.git.get_patch_for_revision(from_rev, to_rev)
        ota_pdu = OTAPDU.create_patch(from_rev, to_rev, patch)
        self.log("Disseminating patch... %s, %s" % (from_rev, to_rev))
        self.disseminate(ota_pdu.to_string(), version)

    def _handle_incoming_dissemination(self, data):
        ota_pdu = OTAPDU.from_string(data)
        self._log_receive_pdu(ota_pdu, 'protocol')
        assert ota_pdu.is_patch()
        if utils.git.get_current_revision() == ota_pdu.from_rev:
            utils.git.apply_patch(ota_pdu.patch)
            # Send an ADV back to upgrader.
            self._send_adv(self.seed_addr)

    def _log(self, message):
        prefix = "(%s)" % self.addr
        self.logger.info("%s - %s" % (prefix, message))

    def _log_send_pdu(self, data_unit):
        self._log("Sending message (%s): %s" % (len(data_unit.to_string()), repr(data_unit)))

    def _log_receive_pdu(self, data_unit, sender_addr):
        self._log("Received message from %3s: %s" % (sender_addr, repr(data_unit)))


def main(args):
    ota = OTA.create_and_run_application()
    ota.set_mode(args.mode)

    if args.mode == Mode.UPGRADE:
        ota._send_flood()
        time.sleep(5)
        ota._send_patch(args.version)
    elif args.mode == Mode.STOP:
        ota._send_stop()

    while True:
        time.sleep(5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manager Application')
    parser.add_argument('--mode', '-m', type=str, default=Mode.NORMAL,
                        choices=[Mode.NORMAL, Mode.UPGRADE, Mode.STOP])
    parser.add_argument('--version', '-v', type=int, default=2)
    args = parser.parse_args()
    main(args)