"""
This module contains the BleakModel class, which is a wrapper around the BleakScanner class.

The state machine (pytransitions) adds public methods to this class 
(methods that don't start with an underscore).
Underscore-prefixed methods are meant to be called by the state machine, 
and should not raise exceptions.
Instead, they should return True if the method was successful, and False if it was not.
You are responsible for dealing with transitions that weren't successful.
"""

import asyncio
import logging

from bleak import BleakClient, BleakScanner

# typing
from transitions.extensions.asyncio import AsyncMachine
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData


class BleakModel:
    """
    This class is a transitions.AsyncModel wrapper around the BleakScanner class.
    It is used to scan and receive data for Bluetooth Low Energy devices,
    while providing a simple state machine interface to the programmer.

    Many of this class's methods are meant to be state machine callbacks,
    so they are prefixed with an underscore to prevent accidentally calling them directly.

    Methods that are called by the state machine must not raise exceptions.
    Instead, return True if the method was successful, and False if it was not.
    The user of the state machine is responsible for
    dealing with transitions that weren't successful.
    """

    # class variable to store all instances of BleakModel, for easy cleanup
    instances = []

    # class variable to store the discovered devices, since we can only have one BleakScanner
    bt_devices = {}

    _stop_scan_event = asyncio.Event()  # class variable to stop the scan

    async def __aenter__(self):
        """
        Entering the `async with` context manager. Does nothing.
        """

    async def __aexit__(self, *args):
        """
        Exiting the `async with` context manager. Cleans up.
        """
        await self.clean_up()

    @classmethod
    async def clean_up_all(cls):
        """
        Go to Init state from all states for all instances of BleakModel.
        Call when handling exceptions or when program is exiting.
        """
        for instance in cls.instances:
            await instance.clean_up()
        return True

    @classmethod
    async def _start_scan(cls):
        """
        Worker that runs the BLE scan.
        """
        cls.bt_devices = {}  # clear the list
        cls._stop_scan_event.clear()  # clear the stop_scan_event

        def detection_callback(device, advertisement_data):
            cls.bt_devices.update({device.address: (device, advertisement_data)})

        async with BleakScanner(detection_callback) as scanner:
            await cls._stop_scan_event.wait()  # continues to scan until stop_scan_event is set
        return True

    @classmethod
    async def start_scan(cls):
        """
        Non-blocking start of the BLE scan.
        """
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(
            lambda loop, context: logging.error(
                f"Exception: {context.get('exception')}"
            )
        )
        asyncio.create_task(cls._start_scan())
        return True

    @classmethod
    async def stop_scan(cls):
        """
        Stop the BLE scan.
        """
        cls._stop_scan_event.set()
        return True

    def _setup_state_machine(self):
        """
        Initialize the state machine.
        """
        states = ["Init", "TargetSet", "Connected", "Streaming"]

        self.machine = AsyncMachine(model=self, states=states, initial="Init")
        self.machine.add_transition(
            trigger="set_target",
            source="Init",
            dest="TargetSet",
            conditions="_set_target",
        )

        self.machine.add_transition(
            trigger="unset_target",
            source="TargetSet",
            dest="Init",
            before="_unset_target",
        )

        self.machine.add_transition(
            trigger="connect",
            source="TargetSet",
            dest="Connected",
            conditions="_connect_to_device_with_timeout",
        )

        self.machine.add_transition(
            trigger="stream",
            source="Connected",
            dest="Streaming",
            # potentially check if the measurement handler is set in a 'condition'.
            conditions="_setup_stream",
            after="_nonblocking_stream",
        )

        self.machine.add_transition(
            trigger="disconnect",
            source="Connected",
            dest="TargetSet",
            before="_disconnect_from_device",
        )

        # After a stream is stopped, we can't go back to Connected
        # because we can't re-use the BleakClient object.
        # Therefore we need to go one more back to TargetSet,
        self.machine.add_transition(
            trigger="disconnect",
            source="Streaming",
            dest="TargetSet",
            before="_stop_stream_and_disconnect_from_device",
        )

    def __init__(self, connection_timeout=5.0, logging_level=logging.WARNING):
        logging.basicConfig(level=logging_level)

        self._setup_state_machine()

        self.connection_timeout = connection_timeout  # seconds

        self.bleak_client: BleakClient = None
        self.ble_device: BLEDevice = None
        self.advertisement_data: AdvertisementData = None
        self.target = None
        self._stop_streaming_event = asyncio.Event()

        self.wrapped_client = None

        # --- The following must be defined by user after instantiation ---
        # Callable that sets self.wrapped_client.
        # If you use anything besides BleakClient, you must define this.
        self.wrap = lambda client: client
        # Callable that takes in the wrapped client and starts notifications.
        self.enable_notifications = None
        # Callable that takes in the wrapped client and stops notifications.
        self.disable_notifications = None
        # Callable that takes in the wrapped client and returns the measurement handler.
        # It 'sets' the 'setter'.
        self.set_measurement_handler = None

        BleakModel.instances.append(self)

    async def clean_up(self):
        logging.info("Cleaning up.")
        self._stop_streaming_event.set()

        try:
            if self.state == "Streaming":
                await self.disconnect()
            if self.state == "Connected":
                await self.disconnect()
            if self.state == "TargetSet":
                await self.unset_target()
        except Exception as e:
            logging.error(f"An error occurred during cleanup: {str(e)}")
            return False

        return True

    def _set_target(self, address):
        try:
            if address in BleakModel.bt_devices:
                self.target = address
                return True
            else:
                logging.error(f"Address {address} not found in discovered devices")
                return False
        except Exception as e:
            logging.error(f"An error occurred while setting the target. Error: {e}")
            return False

    def _unset_target(self):
        self.target = None

    async def _connect_to_device_with_timeout(self):
        """
        Connect to the device with a timeout (seconds)
        """
        try:
            return await asyncio.wait_for(
                self._connect_to_device(), timeout=self.connection_timeout
            )

        except asyncio.TimeoutError:
            logging.warning(f"Timed out while connecting to {self.target}")
            # We must disconnect so that the device is returned to the list of discovered devices
            await self._disconnect_from_device()
            return False

    async def _connect_to_device(self):
        if len(BleakModel.bt_devices) == 0:
            logging.error("No devices found")
            return False
        try:
            self.ble_device, self.advertisement_data = BleakModel.bt_devices.pop(
                self.target
            )  # remove the device from the list to avoid connecting to it multiple times
        except Exception as e:
            logging.error(
                f"""
                Bluetooth device {self.target} not found in scanned list.
                It could be powered off, connected to another device, or to another BleakModel.
                Error: {e}
                """
            )
            return False
        try:
            self.bleak_client = BleakClient(self.ble_device)
            # we don't use the async context manager because
            # we want to access the client object from the disconnect function

            connected = await self.bleak_client.connect()
            if connected:
                logging.info(f"Connected to {self.target}")

                self.wrapped_client = self.wrap(self.bleak_client)

                return True
            else:
                logging.warning(f"Failed to connect to {self.target}")
        except Exception as e:
            logging.error(
                f"An error occurred while connecting to {self.target}. Error: {e}"
            )
            return False
        return True

    async def _disconnect_from_device(self):
        try:
            BleakModel.bt_devices.update(
                {self.target: (self.ble_device, self.advertisement_data)}
            )  # put it back in the list
            await self.bleak_client.disconnect()
            logging.info(f"Disconnected from {self.target}")
            return True
        except Exception as e:
            logging.error(f"An error occurred while disconnecting. Error: {e}")
            return False

    async def _setup_stream(self):
        try:
            self._stop_streaming_event.clear()
            if not isinstance(self.wrapped_client, BleakClient):
                logging.info(
                    f"""Wrapped client is not a BleakClient object. 
                    Assuming it's a Pycycling object and calling `set_measurement_handler`.
                    """
                )
                self.set_measurement_handler(self.wrapped_client)
            await self.enable_notifications(self.wrapped_client)
            return True
        except Exception as e:
            logging.error(
                f"""
                An error occurred while setting up the stream.\n
                Double-check that the enable_notifications and set_measurement_handler methods are set, 
                and that they take in a BleakClient or similar (Pycycling) object."
                Error: {e}
                """
            )
            return False

    async def _nonblocking_stream(self):
        """
        Run _stream_from_device in a detached coroutine.
        Allowing users to `await model.stream()` without blocking.
        """
        asyncio.create_task(self._stop_streaming_event.wait())
        # We checked as best we could that the stream is correctly set up in _setup_stream()
        # And since we can't know at this point if the stream is actually working,
        # We have to assume it is and return True.
        return True

    async def send_command(self, command):
        raise NotImplementedError("Todo: Implement this method")

    async def _stop_stream_from_device(self):
        try:
            self._stop_streaming_event.set()
            await self.disable_notifications(self.wrapped_client)
            logging.info("Stopped streaming")
            return True
        except Exception as e:
            logging.error(f"An error occurred while stopping streaming: {e}")
            return False

    async def _stop_stream_and_disconnect_from_device(self):
        """
        Since we can't re-use the connection after stopping notify,
        we bundle the stop streaming and disconnect logic
        so that the state jumps from Streaming to Init.
        """
        try:
            await self._stop_stream_from_device()
            await self._disconnect_from_device()
            return True
        except Exception as e:
            logging.warning(
                f"An error occurred while stopping streaming. Continuing to disconnect from device. Error: {e}"
            )
            return False
