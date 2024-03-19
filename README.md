# Bleak-FSM

**A Finite State Machine abstraction over the Bleak Bluetooth library for simplified state management in production Python applications.**

## Introduction

[Bleak](https://github.com/hbldh/bleak) provides an excellent cross-platform API for connecting to Bluetooth devices using Python. 

However, it lacks any guidance for incorporating it into a production application. Developers using the Bleak library are expected to keep track of the bluetooth connection status for the bluetooth adapter and for each device. This can result in applications storing bluetooth state shared between various components of the frontend and backend. We believe this to be an anti-pattern.

**Bleak-FSM** makes it easy to keep track of all state in the same program that actually interfaces with bluetooth. This library is an opinionated abstraction over Bleak that uses the concept of [Finite State Machines](https://en.wikipedia.org/wiki/Finite-state_machine) to make explicit the status of scanned / connected devices across a full user application lifecycle. Basically, `bleak-fsm` defines several possible "states" and specific methods to transition between those states.

This library inherits all of the cross-platform compatibility of Bleak, supporting Mac, Linux, Windows, and Android. It's tested on the first three.

## Concepts

`BleakModel`(found in [bleak_model.py](bleak_fsm/bleak_model.py)) represents the bluetooth adapter on your system. This library supports one adapter per program. It follows that scanning is a class method of the `BleakModel`, like so: `await BleakModel.start_scan()`. You must scan before setting the connection targets for instances of the `BleakModel` class.

As a rule, transitions may fail but no runtime exceptions are raised. In other words, the worst that can happen is that the state didn't change, even when you told it to. 

You are responsible for detecting failed transitions by:
1. Checking the return value (boolean) of the transition function. E.g. `successful = await model.connect(); assert successful`
2. Or, by checking the state of the model after the attempted transition: `await model.connect(); assert model.state=="Connected"`

If you fail to do the above, a `MachineError` may be thrown to prevent illegal transition attempts.

Instances of `BleakModel` represents individual BLE devices that you wish to connect to. You may transition between the following states: `Init`, `TargetSet`, `Connected`, and `Streaming` using methods: `set_target()`, `connect()`, `stream()`, `disconnect()`, and `unset_target`. The `clean_up()` method can be used as a shortcut to transition instances of BleakModel in any state back to `Init` for whenever exceptions are raised or the program quits.

## Installation

```
pip3 install bleak-fsm
```

Bleak-FSM is compatible with Python versions 3.8 to 3.12. See [pyproject.toml](pyproject.toml)

## Quickstart

Bleak-FSM is designed for use within Python scripts. Nevertheless, the following demonstration uses the Python REPL:

From your command line, start the interactive Python interpeter:
```bash
python3 # or python, depending on OS and installation.
```

All following commands are to be copy-pasted into the Python REPL, after `>>>`.

```python
from bleak_fsm import BleakModel
import asyncio
```

Create asyncio event loop:
```python
loop = asyncio.new_event_loop()
```

Start scan
```python
loop.run_until_complete(BleakModel.start_scan())
```

Here, we use `loop.run_until_complete()`, but typically you would `await BleakModel.start_scan()` inside a pre-existing async function.

Wait for a few seconds for the scan to find some devices.

End scan
```python
loop.run_until_complete(BleakModel.stop_scan())
```

List discovered devices:
```python
BleakModel.bt_devices
```

It might fill up your screen in a messy way. Here's a prettier way to print it:

```python
for k, v in BleakModel.bt_devices.items(): print(f"Address: {k}. Name: {v[0].name}")
```

Use one of the addresses. For this example, we'll pick a device that implement bluetooth heart rate monitoring.

```python
target_address = "14863C4D-BF71-4EA3-C6B4-98001056AAF8" # ENTER YOUR OWN HERE
```

Create a BleakModel object representing that device.
```python
model = BleakModel(connection_timeout=10)
loop.run_until_complete(model.set_target(target_address))
model.state # prints: "TargetSet"
```

Connect to it:
```python
loop.run_until_complete(model.connect())
model.state # should print: "Connected".
```
If the state isn't "Connected", try increasing the `connection_timeout`.

At this point, we need to tell our `model` the details on how to connect and process the data from it.

Define the GATT characteristic UUID that you want to query:
```python
HEART_RATE_MEASUREMENT_CHARACTERISTIC_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
```

For this example, we'll save the output to a text file.
```python
def handle_hr_measurement(sender, data): open("hr_output.txt", "a").write(f"Data received from {sender}: {data}\nHeart Rate: {data[1]} beats per minute\n")
```

Define three important methods on our `model`. You need to pass in a Callable (a function) that takes a single `client` argument. 
Compare this code to [`bleak` examples](https://github.com/hbldh/bleak/blob/develop/examples/enable_notifications.py).

In this example, our `client` is a straightforward `BleakClient`. See [examples](/examples/) directory for using Pycycling objects and other abstractions.

```python
model.enable_notifications = lambda client: client.start_notify(HEART_RATE_MEASUREMENT_CHARACTERISTIC_UUID, handle_hr_measurement)

model.disable_notifications = lambda client: client.stop_notify(HEART_RATE_MEASUREMENT_CHARACTERISTIC_UUID)

model.set_measurement_handler = lambda client: handle_hr_measurement
```

Stream the heart rate measurements from it:
```python
loop.run_until_complete(model.stream())
```

You won't immediately see any output. The Python REPL doesn't really support that. But after you disconnect, you should see a new text file `hr_output.txt` that has the recorded heart rate (as defined by our `handle_hr_measurement` callback).

```python
loop.run_until_complete(model.clean_up())
```

## Examples

Clone this repository and check out the guides in the [examples](examples/) directory to get more familiar with Bleak-FSM.

Start with the [basic Jupyter notebook tutorial](examples/single_hr_notebook_example.ipynb). It uses Heart Rate monitor as an example. For all of these demos, you need to modify the target bluetooth device address/name.

If you don't have a device with heart rate service, refer to the [Migration Guide notebook](examples/migration_guide.ipynb) to use your Bluetooth device with Bleak-FSM.

[dual_notebook_example.ipynb](examples/dual_notebook_example.ipynb) builds on the basic tutorial and demonstrates simultaneous connection to two different Bluetooth devices.

For a regular python script version, see [single_hr_script_example.py](examples/single_hr_script_example.py).

For developer convenience, this library implements Python context managers (`with` blocks). See [context manager notebook example](examples/context_manager.ipynb) for a quick demonstration.


## Migrating from Vanilla Bleak

The following is a non-functioning code snippet that shows what your `bleak` code would look like after migrating to `bleak-fsm`:

<table>
<tr>
<th>Vanilla Bleak</th>
<th>Bleak-FSM</th>
</tr>
<tr>
<td>
    
```python
# Setup

from bleak import BleakClient

def handle_hr_measurement(sender, data):
    heart_rate = data[1]
    print(f"HR: {heart_rate}")

# Scanning process not shown
# Somewhere in your application logic

async with BleakClient(device) as client:
    logger.info("Connected")

    await client.start_notify(
        HEART_RATE_CHARACTERISTIC,
        handle_hr_measurement)
    await asyncio.sleep(5.0)
    await client.stop_notify(
        HEART_RATE_CHARACTERISTIC)
```

</td>
<td>
    
```python
# Setup

from bleak_fsm import BleakModel

model = BleakModel()

def handle_hr_measurement(value):
    print(f"HR: {value}")

# pass in the same Callable as used in
# Vanilla Bleak
model.enable_notifications =
    lambda client: client.start_notify(
        HEART_RATE_CHARACTERISTIC,
        handle_hr_measurement)

model.disable_notifications =
    lambda client: client.stop_notify(
        HEART_RATE_CHARACTERISTIC)

# Scanning process not shown
# Somewhere in your application logic

await model.connect()
print(model.state) # "Connected"

await model.stream()
print(model.state) # "Streaming"

await asyncio.sleep(5)
print(model.state) # "Streaming"

await model.disonnect()
print(model.state) # "TargetSet"

```


</td> 
</tr> 
</table>

## Error Handling

The methods of `BleakModel` do not raise Exceptions, and only return True or False.
The Finite State Machine `machine` uses that Boolean to determine if transition is successful or not.

Therefore, for you, the worst case scenario is that the transition fails.
Runtime exceptions are never thrown.

## Pycycling Compatibility

`bleak-fsm` is designed to accomodate [`pycycling`](https://github.com/zacharyedwardbull/pycycling). The [basic tutorial notebook](examples/single_hr_notebook_example.ipynb) has parallel examples of using either raw BleakClient or a Pycycling object. 

## Limitations & Future Features

+ Only unidirectional (peripheral to computer) communication is supported. Bidirectional support coming in a future version.
+ While this framework enforces correct order of states and transitions, there is no mechanism for constantly checking for the validity of the current state. For example, a supposedly 'Connected' device may power down, move outside of Bluetooth range, etc. A supposedly 'Streaming' device may also power down, stop its stream, etc. This library has no-built in machinery to detect this. However, if you do want to build such a thing, this library provides good building blocks for it.

## Further Resources & Recommendations

This library uses `async` Python. Familiarize yourself with the basics of async Python before using this library. 

If you end up nesting asyncio (for example, if your web server is already async and you want to call this code), you may want to install and use `nest-asyncio`.
```
import nest_asyncio
nest_asyncio.apply()
```

Read the [`pytransitions` README](https://github.com/pytransitions/transitions/blob/master/README.md) for an excellent follow-along tutorial on Finite State Machines.

## Bleak-FSM in the Wild

A list of projects that use this library

+ [react-pycycling-demo](https://github.com/tensorturtle/react-pycycling-demo)
+ (Your Project Here) - let me know via Github issues or tensorturtle@gmail.com
