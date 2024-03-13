# Bleak-FSM

**A Finite State Machine abstraction over the Bleak Bluetooth library for simplified state management in production Python applications.**

## Introduction

[Bleak](https://github.com/hbldh/bleak) provides an excellent cross-platform API for connecting to Bluetooth devices using Python. 

However, it lacks any guidance for incorporating it into a production application. Developers using the Bleak library are expected to keep track of the bluetooth connection status for each bluetooth adapter and for each device. This can result in applications storing bluetooth state shared between various components of the frontend and backend. We believe this to be an anti-pattern.

`bleak-fsm` makes it easy to keep track of all state in the same program that actually interfaces with bluetooth. This library is an opinionated abstraction over Bleak that uses the concept of [Finite State Machines](https://en.wikipedia.org/wiki/Finite-state_machine) to make explicit the status of scanned / connected devices across a full user application lifecycle. Basically, `bleak-fsm` defines several possible "states" (such as `Init`, `TargetSet`, `Connected`, `Streaming`) and possible methods to transition between those states (such as `set_target()`, `connect()`, `start_stream()`, `disconnect()`). A `MachineError` is thrown when illegal transition is attempted.

## Migrating from Vanilla Bleak

The following is a non-functioning code snippet that shows how to migrate from vanilla `bleak` to `bleak-fsm`:

<table>
<tr>
<th>Vanilla `bleak`</th>
<th>`bleak-fsm`</th>
</tr>
<tr>
<td>
<div style="width:100px">
    
```python
# Setup

from bleak import BleakClient

HEART_RATE_CHARACTERISTIC="00002a37-0000-1000-8000-00805f9b34fb"

def handle_hr_measurement(sender, data):
    heart_rate = data[1]
    print(f"HR: {heart_rate}")

# Somewhere in your application logic (scanning part not shown)

async with BleakClient(device) as client:
    logger.info("Connected")

    await client.start_notify(HEART_RATE_CHARACTERISTIC, handle_hr_measurement)
    await asyncio.sleep(5.0)
    await client.stop_notify(HEART_RATE_CHARACTERISTIC)
```
</div>

</td>
<td>
<pre style="white-space: pre-wrap;">
    
```python
# Setup

from bleak_fsm import machine, BleakModel

model = BleakModel()
machine.add_model(model)

def handle_hr_measurement(value):
    print(f"HR: {value}")

model.enable_notifications = lambda client: client.start_notify(HEART_RATE_CHARACTERISTIC, handle_hr_measurement)

model.disable_notifications = lambda client: client.stop_notify(HEART_RATE_CHARACTERISTIC)

# Somewhere in your application logic (scanning part not shown)

await model.connect()
print(model.state) # "Connected"

await model.stream()
print(model.state) # "Streaming"

await asyncio.sleep(5)
print(model.state) # "Streaming"

await model.disonnect()
print(model.state) # "TargetSet"

```

</pre>
</td> 
</tr> 
</table>

Code snippets of 'vanilla' `bleak` vs. `bleak-fsm` code:

Vanilla `bleak`:


`bleak-fsm`:

## Pycycling Compatibility

`bleak-fsm` is designed to accomodate [`pycycling`](https://github.com/zacharyedwardbull/pycycling).

## Further Resources & Recommendations

This library uses `async` Python. Familiarize yourself with the basics of async Python before using this library.

Read the [`pytransitions` README](https://github.com/pytransitions/transitions/blob/master/README.md) for an excellent follow-along tutorial on Finite State Machines.

## `bleak-fsm` in the Wild

A list of projects that use this library

+ [react-pycycling-demo](https://github.com/tensorturtle/react-pycycling-demo)
+ (your project here) - let me know via Github issues or tensorturtle@gmail.com
