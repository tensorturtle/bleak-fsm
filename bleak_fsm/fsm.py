from .bleak_model import BleakModel
from transitions.extensions.asyncio import AsyncMachine

transitions = []

model = BleakModel() # import this from user script

machine = AsyncMachine(model, states=["Init", "TargetSet", "Connected", "Streaming"], transitions=transitions, initial='Init')

machine.add_transition(
    trigger="set_target",
    source="Init",
    dest="TargetSet",
    before="_set_target"
)

machine.add_transition(
    trigger="unset_target",
    source="TargetSet",
    dest="Init",
    before="_unset_target"
)

machine.add_transition(
    trigger="connect",
    source="TargetSet",
    dest="Connected",
    conditions="_connect_to_device_with_timeout"
)

machine.add_transition(
    trigger="stream",
    source="Connected",
    dest="Streaming",
    after="_nonblocking_stream_from_device"
)

machine.add_transition(
    trigger="disconnect",
    source="Connected",
    dest="TargetSet",
    before="_disconnect_from_device"
)

# After a stream is stopped, we can't go back to Connected
# because we can't re-use the BleakClient object.
# Therefore we need to go one more back to TargetSet,
machine.add_transition(
    trigger="disconnect",
    source="Streaming",
    dest="TargetSet",
    before="_stop_stream_and_disconnect_from_device"
)

