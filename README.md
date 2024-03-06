# Bleak FSM (Finite State Machine)

[Bleak](https://github.com/hbldh/bleak) provides an excellent cross-platform API for connecting to Bluetooth devices using Python. 

However, when incorporating it into a production application with proper state transitions (scanning, reading data, disconnecting, re-scanning.) it provides no guidance.

This library is an opinionated abstraction over Bleak that uses the concept of [Finite State Machines](https://en.wikipedia.org/wiki/Finite-state_machine). Use this library to correctly interface with Bluetooth devices instead of trying to reason about it in your head.

We use [pytransitions](https://github.com/pytransitions/transitions/tree/master) implementation of FSM.
