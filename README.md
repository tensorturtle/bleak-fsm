# Bleak FSM (Finite State Machine)

## Introduction

[Bleak](https://github.com/hbldh/bleak) provides an excellent cross-platform API for connecting to Bluetooth devices using Python. 

However, it lacks any guidance for incorporating it into a production application. More specifically, users of the Bleak library are expected to keep track of the bluetooth connection status for each bluetooth adapter and for each device. This can result in applications storing bluetooth state shared between various components of the frontend and backend. We believe this to be an anti-pattern.

`bleak-fsm` keeps all state in the same program that actually interfaces with bluetooth. This library is an opinionated abstraction over Bleak that uses the concept of [Finite State Machines](https://en.wikipedia.org/wiki/Finite-state_machine) to make explicit the status of scanned / connected devices across a full user application lifecycle. Basically, `bleak-fsm` defines several possible "states" (such as `Init`, `TargetSet`, `Connected`, `Streaming`) and possible methods to transition between those states (such as `set_target()`, `connect()`, `start_stream()`, `disconnect()`). A `MachineError` is thrown when illegal transition is attempted.

## Examples (incorrect)

Code snippets of 'vanilla' `bleak` vs. `bleak-fsm` code:

Vanilla `bleak`:
```python
from bleak import BleakClient

with BleakClient(address) as client:
    client.start_notify(CHARACTERISTIC_UUID)
    asyncio.sleep(10)
    client.stop_notify(CHARACTERISTIC_UUID)
```

`bleak-fsm`
```python
from bleak_fsm import machine, BleakModel

# Setup

model = BleakModel()
machine.add_model(model)

model.enable_notifications = lambda client: client.start_notify(CHARACTERISTIC_UUID, handle_hr_measurement)

model.disable_notifications = lambda client: client.stop_notify(CHARACTERISTIC_UUID)

# In Application

await model.connect()

await model.stream()

await model.disonnect()

```

## Pycycling Compatibility

`bleak-fsm` is designed to accomodate [`pycycling`](https://github.com/zacharyedwardbull/pycycling).

## Further Resources & Recommendations

This library uses `async` Python. Familiarize yourself with the basics of async Python before using this library.

Read the [`pytransitions` README](https://github.com/pytransitions/transitions/blob/master/README.md) for an excellent follow-along tutorial on Finite State Machines.

## `bleak-fsm` in the Wild

A list of projects that use this library

+ [react-pycycling-demo](https://github.com/tensorturtle/react-pycycling-demo)
+ (your project here) - let me know via Github issues or tensorturtle@gmail.com