# single_hr_script_context_manager_example.py
#
# This is very similar to `single_hr_script_example.py`,
# But instead of calling clean up methods manually in a `try...except`,
# We use the built-in context manager to ensure that the model is properly cleaned up before the script exits.

import asyncio
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("bleak_fsm_demo")

# filter out asyncio log messages
logging.getLogger('transitions.extensions.asyncio').setLevel(logging.WARN)

from bleak_fsm import BleakModel
from pycycling.heart_rate_service import HeartRateService

def handle_hr_measurement(value):
    logger.debug("Using Pycycling wrapper around BleakClient")
    print(f"Heart Rate: {value}")

async def main(model, target_name: str):
    async with model:
        logger.info("Starting BLE scan")
        await BleakModel.start_scan()
        await asyncio.sleep(5.0)
        await BleakModel.stop_scan()
        if len(BleakModel.bt_devices) == 0:
            logger.error("No devices found. Exiting")
            return
        logger.info("Scan stopped")
        logger.debug("Discovered devices:")
        logger.debug(BleakModel.bt_devices)
        logger.info(f"Connecting to device named {target_name}")
        target_address = ""
        for address, (ble_device, advertisement_data) in BleakModel.bt_devices.items():
            if ble_device.name == target_name:
                target_address = address
                logger.info(f"Found {target_name} at {target_address}")
                break

        await model.set_target(target_address)
        await model.connect()
        await model.stream()
        await asyncio.sleep(5)

        # At this point, the model is in the "Streaming" state
        # If we weren't using the context manager, we would have to call model.disconnect() and model.unset_target() here. But:
        print("The state of the model before the context manager exits is", model.state)

    print("The state of the model after context manager exists is:", model.state)

if __name__ == "__main__":
    model = BleakModel(logging_level=logging.DEBUG)

    model.wrap = lambda client: HeartRateService(client)
    model.enable_notifications = lambda client: client.enable_hr_measurement_notifications()
    model.disable_notifications = lambda client: client.disable_hr_measurement_notifications()
    model.set_measurement_handler = lambda client: client.set_hr_measurement_handler(handle_hr_measurement)

    try:
        asyncio.new_event_loop().run_until_complete(main(
            model=model,
            target_name="WHOOPDEDOO" # Replace with the name of your heart rate device
        ))
    except KeyboardInterrupt: # must be caught at this top level
        asyncio.get_event_loop().run_until_complete(model.clean_up())
        assert model.state == "Init", "State should be 'Init' after clean_up()"
        logger.error("\nExiting due to keyboard interrupt (CTRL+C)")