# Bleak-FSM (Work in Progress)

**A Finite State Machine abstraction over the Bleak Bluetooth library for simplified state management in production Python applications.**

## Introduction

[Bleak](https://github.com/hbldh/bleak) provides an excellent cross-platform API for connecting to Bluetooth devices using Python. 

However, it lacks any guidance for incorporating it into a production application. Developers using the Bleak library are expected to keep track of the bluetooth connection status for the bluetooth adapter and for each device. This can result in applications storing bluetooth state shared between various components of the frontend and backend. We believe this to be an anti-pattern.

**Bleak-FSM** makes it easy to keep track of all state in the same program that actually interfaces with bluetooth. This library is an opinionated abstraction over Bleak that uses the concept of [Finite State Machines](https://en.wikipedia.org/wiki/Finite-state_machine) to make explicit the status of scanned / connected devices across a full user application lifecycle. Basically, `bleak-fsm` defines several possible "states" and specific methods to transition between those states. A `MachineError` is thrown when illegal transition is attempted.

## Concepts

[BleakModel](https://github.com/tensorturtle/bleak-fsm/blob/38c725c7eb501139149cd8cbae22a4eb35e57c33/bleak_fsm.py#L35) represents the bluetooth adapter on your system. This library supports one adapter per program. Scanning operations are executed as class methods on this class.

Instances of BleakModel represents individual BLE devices that you wish to connect to. You may transition between the following states: `Init`, `TargetSet`, `Connected`, `Streaming` using methods: `set_target()`, `connect()`, `stream()`, `disconnect()`. `clean_up()` is a somewhat special method that gracefully transitions instances of BleakModel back to `Init` for whenever exceptions are raised or the program quits.

## Installation

```
pip3 install bleak-fsm
```

## Quickstart

After installation, you should clone this repository and check out the guides in the [examples](examples/) directory to get familiar with Bleak-FSM.

Start with the [basic Jupyter notebook tutorial](examples/single_hr_notebook_example.ipynb). It uses Heart Rate monitor as an example. For all of these demos, you need to modify the target bluetooth device address/name.

If you don't have one, refer to the [Migration Guide notebook](examples/migration_guide.ipynb) to use your Bluetooth device with Bleak-FSM.

[dual_notebook_example.ipynb](examples/dual_notebook_example.ipynb) builds on the basic tutorial and demonstrates simultaneous connection to two different Bluetooth devices.

For a regular python script version, see [single_hr_script_example.py](examples/single_hr_script_example.py).

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

from bleak_fsm import machine, BleakModel

model = BleakModel()
machine.add_model(model)

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

## Further Resources & Recommendations

This library uses `async` Python. Familiarize yourself with the basics of async Python before using this library. 

Read the [`pytransitions` README](https://github.com/pytransitions/transitions/blob/master/README.md) for an excellent follow-along tutorial on Finite State Machines.

## Bleak-FSM in the Wild

A list of projects that use this library

+ [react-pycycling-demo](https://github.com/tensorturtle/react-pycycling-demo)
+ (your project here) - let me know via Github issues or tensorturtle@gmail.com
