import asyncio
import logging

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .exc import BleakFSMError, NoDevicesFoundError

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

    @classmethod
    async def _start_scan(cls):
        '''
        Worker that runs the BLE scan.
        '''
        cls.bt_devices = {} # clear the list
        cls._stop_scan_event.clear()  # clear the stop_scan_event
        def detection_callback(device, advertisement_data):
            cls.bt_devices.update({device.address: (device, advertisement_data)})
        async with BleakScanner(detection_callback) as scanner:
            await cls._stop_scan_event.wait() # continues to scan until stop_scan_event is set
        return True

    @classmethod
    async def start_scan(cls):
        '''
        Non-blocking start of the BLE scan.
        '''
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(lambda loop, context: logging.error(f"Exception: {context.get('exception')}"))
        asyncio.create_task(cls._start_scan())
        return True

    @classmethod
    async def stop_scan(cls):
        '''
        Stop the BLE scan.
        '''
        cls._stop_scan_event.set()
        return True

    def __init__(self, connection_timeout=5.0, logging_level=logging.WARNING):
        '''
        Args
            (int) scan_stale_time: number of seconds while scan results are considered valid for establishing connection. Must re-scan if connection attempted after this time.
            (bool) auto_rescan: If connect() attempted when scan is stale, run scan for `auto_rescan_timeout` seconds
            (int) auto_rescan_timeout: Number of seconds to scan, if auto_rescan is True. If scan isn't stale, then this value is not used and scan continues indefinitely until you call stop_scan().
        '''
        logging.basicConfig(level=logging_level)

        self.connection_timeout = connection_timeout  # seconds
        
        self.bleak_client: BleakClient = None
        self.ble_device: BLEDevice = None
        self.advertisement_data: AdvertisementData = None
        self.target = None
        self._stop_streaming_event = asyncio.Event()

        self.wrap = lambda client: client  # Callable that sets self.wrapped_client. A callable may return identity for no wrap, or a Pycycling object which wraps a standard client. By default, an identity function.
        self.wrapped_client = None # Either identical to `self.bleak_client` (not wrapped) or custom object that represents the BLE device that presumably takes in a BleakClient, such as pycycling classes
        self.enable_notifications = None # an Async Callable must be set later that takes in a BleakClient or similar (Pycycling) object
        self.set_measurement_handler = None  # a Callable must be set later that takes in a BleakClient or similar (Pycycling) object and a value
        self.disable_notifications = None # an Async Callable must be set later that takes in a BleakClient or similar (Pycycling) object

        self.last_scan_time = None

    async def clean_up(self):
        '''
        Go to Init state from all states. Call when handling exceptions or when program is exiting.
        '''
        self._stop_scan_event.set()
        self._stop_streaming_event.set()

        if self.state == "Streaming":
            await self.disconnect()
        if self.state == "Connected":
            await self.disconnect()
        if self.state == "Scanning":
            await self.stop_scan()
        if self.state == "TargetSet":
            await self.unset_target()
        return True
    async def _nonblocking_start_scan(self):
        '''
        Run _start_scan in a detached coroutine.
        Allowing users to `await model.start_scan()` without blocking.
        '''
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(lambda loop, context: logging.error(f"Exception: {context.get('exception')}"))
        asyncio.create_task(self._start_scan())
        return True

    def _set_target(self, address):
        if address in BleakModel.bt_devices.keys():
            self.target = address
            return True
        else:
            raise BleakFSMError(f"Address {address} not found in discovered devices")
            # recommend resetting wifi if you suspect that the device was improperly connected from this device

    def _unset_target(self):
        self.target = None

    async def _connect_to_device_with_timeout(self):
        '''
        Connect to the device with a timeout (seconds)
        '''
        try:
            await asyncio.wait_for(self._connect_to_device(), timeout=self.connection_timeout)
        except asyncio.TimeoutError:
            logging.warning(f"Timed out while connecting to {self.target}")
            # We must disconnect so that the device is returned to the list of discovered devices
            await self._disconnect_from_device()
            return False
        return True

    async def _connect_to_device(self):
        if len(BleakModel.bt_devices) == 0:
            raise NoDevicesFoundError()
        try:
            self.ble_device, self.advertisement_data = (BleakModel.bt_devices.pop(self.target))# remove the device from the list to avoid connecting to it multiple times
        except:
            raise BleakFSMError(f"Bluetooth device {self.target} not found in scanned list. It could be powered off, connected to another device, or to another BleakModel.")
        self.bleak_client = BleakClient(self.ble_device) # we don't use the async context manager because we want to access the client object from the disconnect function
        try:
            connected = await self.bleak_client.connect()
            if connected:
                logging.info(f"Connected to {self.target}")

                self.wrapped_client = self.wrap(self.bleak_client)
                    
                return True
            else:
                logging.warning(f"Failed to connect to {self.target}")
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return False
        return True
    
    async def _disconnect_from_device(self):
        BleakModel.bt_devices.update({self.target: (self.ble_device, self.advertisement_data)}) # put it back in the list
        await self.bleak_client.disconnect()
        logging.info(f"Disconnected from {self.bleak_client.address}")

    async def _nonblocking_stream_from_device(self):
        '''
        Run _stream_from_device in a detached coroutine.
        Allowing users to `await model.stream()` without blocking.
        '''
        asyncio.create_task(self._stream_from_device())
        return True

    async def _stream_from_device(self):
        self._stop_streaming_event.clear()

        self.set_measurement_handler(self.wrapped_client)
        await self.enable_notifications(self.wrapped_client)
        
        logging.info("Started streaming")

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

            logging.info("Stopped streaming")
            return True
        except Exception as e:
            logging.error(f"An error occurred while stopping streaming: {e}")
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