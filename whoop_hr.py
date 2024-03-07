import asyncio
from bleak import BleakClient

HEART_RATE_MEASUREMENT_CHARACTERISTIC_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

def handle_heart_rate_measurement(sender, data):
    print(f"Data received from {sender}: {data}")
    flag = data[0]
    heart_rate = data[1]
    print(f"Heart Rate: {heart_rate} beats per minute")

async def run_ble_client(address):
    print(f"Trying to connect to {address}")
    async with BleakClient(address) as client:
        connected = await client.is_connected()
        print(f"Connected: {connected}")
        if connected:
            print(f"Connected to {address}")
            await client.start_notify(HEART_RATE_MEASUREMENT_CHARACTERISTIC_UUID, handle_heart_rate_measurement)
            print("Started notifications.")
            await asyncio.sleep(30)  # Waits for 30 seconds to receive data
            await client.stop_notify(HEART_RATE_MEASUREMENT_CHARACTERISTIC_UUID)
            print("Stopped notifications.")
        else:
            print(f"Failed to connect to {address}")

if __name__ == "__main__":
    device_address = "14863C4D-BF71-4EA3-C6B4-98001056AAF8"
    asyncio.run(run_ble_client(device_address))

