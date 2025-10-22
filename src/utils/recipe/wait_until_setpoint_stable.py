import logging

# Local imports
from .wait_until_setpoint import WaitUntilSetpointAction
from devices.source import Source

logger = logging.getLogger(__name__)

# WAIT_UNTIL_SETPOINT_STABLE action
# Extends WaitUntilSetpointAction because it is almost identical, just a slightly different check
class WaitUntilSetpointStableAction(WaitUntilSetpointAction):
    def __init__(self, source_dict: dict[str, Source]):
        super().__init__(source_dict)
        
        # Reconnect timer to subclass version of _check
        self.check_timer.timeout.disconnect()
        self.check_timer.timeout.connect(self._check)
        
    def _check(self):
        if self.sources_checking == self.sources_finished:
            self.can_continue.emit()
            self.check_timer.stop()
            return
        
        for source_name in self.sources_checking:
            source = self.sources[source_name]
            if source.get_is_stable() and source.is_pv_close_to_sp():
                self.sources_finished.add(source_name)
            else:
                self.sources_finished.discard(source_name)