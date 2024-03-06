# Bleak FSM (Finite State Machine)

[Bleak](https://github.com/hbldh/bleak) provides an excellent cross-platform API for connecting to Bluetooth devices using Python. 

However, it provides no guidance about incorporating it into a production application with proper state transitions (scanning, reading data, disconnecting, re-scanning, etc.).

This library is an opinionated abstraction over Bleak that uses the concept of [Finite State Machines](https://en.wikipedia.org/wiki/Finite-state_machine) to facilitate its use across a full user application lifecycle. Use this library to correctly interface with Bluetooth devices instead of trying to keep it in your head and doing ad-hoc fixes to invalid states.

Developed by [tensorturtle](https://github.com/tensorturtle), creator of [react-pycycling-demo](https://github.com/tensorturtle/react-pycycling-demo) and major contributor to [pycycling](https://github.com/zacharyedwardbull/pycycling)

## Dependencies
+ [pytransitions](https://github.com/pytransitions/transitions/tree/master): Python implementation of FSM.
+ [pycycyling](https://github.com/zacharyedwardbull/pycycling): Bleak-based library for reading & controlling cycling-related devices. Used for demonstration.

## Helpful Reading

[pytrainsitions README](https://github.com/pytransitions/transitions/blob/master/README.md) has an excellent follow-along tutorial.
