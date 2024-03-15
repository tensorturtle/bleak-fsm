# single_hr_script_example.py
#
# This is a Python script equivalent of `single_hr_example.ipynb` Jupyter notebook.
# It streams the heart rate measurement from a Bluetooth Low Energy (BLE) heart rate device.
# The major difference is that this script demonstrates how to handle CTRL+C signal
# So that Bluetooth connection is properly closed before the script exits.

import asyncio
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("bleak_fsm_demo")

# filter out asyncio log messages
logging.getLogger('transitions.extensions.asyncio').setLevel(logging.WARN)

from bleak_fsm import machine, BleakModel
from pycycling.heart_rate_service import HeartRateService

def handle_hr_measurement(value):
    logger.debug("Using Pycycling wrapper around BleakClient")
    print(f"Heart Rate: {value}")

async def main(model, target_name: str):
    try:
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
        await model.disconnect()
        await model.unset_target()
        logger.info("Program finished. Exiting")
    except Exception as e:
        logger.error(f"Error: {e}")
        await model.clean_up()
        logger.debug(model.state)
        logger.error("Exiting due to error")

if __name__ == "__main__":
    model = BleakModel(logging_level=logging.DEBUG)
    machine.add_model(model)

    model.wrap = lambda client: HeartRateService(client)
    model.enable_notifications = lambda client: client.enable_hr_measurement_notifications()
    model.disable_notifications = lambda client: client.disable_hr_measurement_notifications()
    model.set_measurement_handler = lambda client: client.set_hr_measurement_handler(handle_hr_measurement)

    try:
        asyncio.get_event_loop().run_until_complete(main(
            model=model,
            target_name="WHOOPDEDOO" # Replace with the name of your heart rate device
        ))
    except KeyboardInterrupt: # must be caught at this top level
        asyncio.get_event_loop().run_until_complete(model.clean_up())
        assert model.state == "Init", "State should be 'Init' after clean_up()"
        logger.error("\nExiting due to keyboard interrupt (CTRL+C)")