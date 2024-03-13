import asyncio
import time

from transitions.extensions.asyncio import AsyncMachine
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

### Exceptions
    
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

class BleakModel:
    '''
    This class is a transitions.AsyncModel wrapper around the BleakScanner class.
    It is used to scan and receive data for Bluetooth Low Energy devices,
    while providing a simple state machine interface to the programmer.

    Many of this class's methods are meant to be state machine callbacks, 
    so they are prefixed with an underscore to prevent accidentally calling them directly.
    '''
    bt_devices = {} # class variable to store the discovered devices, since we can only have one BleakScanner
    _stop_scan_event = asyncio.Event() # class variable to stop the scan
    def __init__(self, scan_stale_time=120, auto_rescan=True, auto_rescan_timeout=3):
        '''
        Args
            (int) scan_stale_time: number of seconds while scan results are considered valid for establishing connection. Must re-scan if connection attempted after this time.
            (bool) auto_rescan: If connect() attempted when scan is stale, run scan for `auto_rescan_timeout` seconds
            (int) auto_rescan_timeout: Number of seconds to scan, if auto_rescan is True. If scan isn't stale, then this value is not used and scan continues indefinitely until you call stop_scan().
        '''
        self.bleak_client: BleakClient = None
        self.ble_device: BLEDevice = None
        self.target = None
        self._stop_streaming_event = asyncio.Event()

        self.scan_stale_time = scan_stale_time
        self.auto_rescan = auto_rescan
        self.auto_rescan_timeout = auto_rescan_timeout

        self.wrap = lambda client: client  # Callable that sets self.wrapped_client. A callable may return identity for no wrap, or a Pycycling object which wraps a standard client. By default, an identity function.
        self.wrapped_client = None # Either identical to `self.bleak_client` (not wrapped) or custom object that represents the BLE device that presumably takes in a BleakClient, such as pycycling classes
        self.enable_notifications = None # an Async Callable must be set later that takes in a BleakClient or similar (Pycycling) object
        self.set_measurement_handler = None  # a Callable must be set later that takes in a BleakClient or similar (Pycycling) object and a value
        self.disable_notifications = None # an Async Callable must be set later that takes in a BleakClient or similar (Pycycling) object

        self.last_scan_time = None
        
    async def _bt_scan(self):        
        def detection_callback(device, _advertisement_data):
            BleakModel.bt_devices[device.address] = device
        async with BleakScanner(detection_callback) as scanner:
            await self._stop_scan_event.wait() # continues to scan until stop_scan_event is set

    async def _stop_bt_scan(self):
        self.last_scan_time = time.time()
        self._stop_scan_event.set()

    def _set_target(self, address):
        if address in BleakModel.bt_devices:
            self.target = address
            return True
        else:
            return BleakFSMError(f"Address {address} not found in discovered devices")
            # recommend resetting wifi if you suspect that the device was improperly connected from this device

    def _unset_target(self):
        self.target = None

    async def _connect_to_device(self):
        # stale scan data
        if self.last_scan_time is not None:
            if time.time() - self.last_scan_time > self.scan_stale_time:
                if self.auto_rescan:
                    print("Stale scan. Automatically re-scanning before attempting connect")
                    await self._bt_scan()
                    await asyncio.sleep(self.auto_rescan_timeout)
                    await self._stop_bt_scan()
                    await self._connect_to_device() # while this looks recursive, it isn't because after one iteration, the stale time will not have been reached
                    return True
                else:
                    raise StaleScanError()
                
        if len(BleakModel.bt_devices) == 0:
            raise NoDevicesFoundError()
        try:
            self.ble_device = (BleakModel.bt_devices.pop(self.target))# remove the device from the list to avoid connecting to it multiple times
        except:
            raise BleakFSMError(f"Bluetooth device {self.target} not found in scanned list. It could be powered off, connected to another device, or to another BleakModel.")
        self.bleak_client = BleakClient(self.ble_device) # we don't use the async context manager because we want to access the client object from the disconnect function
        try:
            connected = await self.bleak_client.connect()
            if connected:
                print(f"Connected to {self.target}")

                self.wrapped_client = self.wrap(self.bleak_client)
                    
                return True
            else:
                print(f"Failed to connect to {self.target}")
        except Exception as e:
            print(f"An error occurred: {e}")
            return False
        return True
    
    async def _disconnect_from_device(self):
        BleakModel.bt_devices[self.target] = self.ble_device # put it back in the list
        await self.bleak_client.disconnect()
        print(f"Disconnected from {self.bleak_client.address}")

    async def _stream_from_device(self):
        self._stop_streaming_event.clear()

        self.set_measurement_handler(self.wrapped_client)
        await self.enable_notifications(self.wrapped_client)
        
        print("Started streaming")

        await self._stop_streaming_event.wait()
        return True
    
    async def send_command(self, command):
        if self.state != "Streaming":
            raise BleakFSMError("Cannot send command while not streaming")
        raise NotImplementedError("Todo: Implement this method")

    async def _stop_stream_from_device(self):
        self._stop_streaming_event.set()
        try:
            await self.disable_notifications(self.wrapped_client)

            print("Stopped streaming")
            return True
        except Exception as e:
            print(f"An error occurred while stopping streaming: {e}")
            return False

    async def _stop_stream_and_disconnect_from_device(self):
        '''
        Since we can't re-use the connection after stopping notify,
        we bundle the stop streaming and disconnect logic
        so that the state jumps from Streaming to Init.
        '''
        await self._stop_stream_from_device()
        await self._disconnect_from_device()
        return True
    
### pytransitions FSM
    
transitions = []

model = BleakModel() # import this from user script

machine = AsyncMachine(model, states=["Init", "Scanning", "TargetSet", "Connected", "Streaming"], transitions=transitions, initial='Init')

machine.add_transition(
    trigger="start_scan",
    source="Init",
    dest="Scanning",
    after="_bt_scan"
)

machine.add_transition(
    trigger="stop_scan",
    source="Scanning",
    dest="Init",
    after="_stop_bt_scan"
)

machine.add_transition(
    trigger="set_target",
    source="Init",
    dest="TargetSet",
    before="_set_target"
)

machine.add_transition(
    trigger="unset_target",
    source="TargetSet",
    dest="Init",
    before="_unset_target"
)

machine.add_transition(
    trigger="connect",
    source="TargetSet",
    dest="Connected",
    conditions="_connect_to_device"
)

machine.add_transition(
    trigger="stream",
    source="Connected",
    dest="Streaming",
    after="_stream_from_device"
)

machine.add_transition(
    trigger="disconnect",
    source="Connected",
    dest="TargetSet",
    before="_disconnect_from_device"
)

# After a stream is stopped, we can't go back to Connected
# because we can't re-use the BleakClient object.
# Therefore we need to go one more back to TargetSet,
machine.add_transition(
    trigger="disconnect",
    source="Streaming",
    dest="TargetSet",
    before="_stop_stream_and_disconnect_from_device"
)

