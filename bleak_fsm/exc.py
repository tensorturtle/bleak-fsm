class BleakFSMError(Exception):
    '''
    Base class for this library's exceptions.
    When developers use Bleak FSM, they should only see subclasses of this exception.
    No other types of exceptions should pass through and be raised.
    '''
    pass

class StaleScanError(BleakFSMError):
    '''
    Raised when the scan is stale.
    '''
    def __init__(self):
        super().__init__("Scan is stale. Please rescan. Consider setting 'auto_rescan=True' to avoid this error.")

class NoDevicesFoundError(BleakFSMError):
    '''
    Raised when no devices are found during a scan.
    '''
    def __init__(self):
        super().__init__("No devices found during scan.")

