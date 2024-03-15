import pytest
import asyncio
import transitions
from bleak_fsm import machine, BleakModel # Replace 'your_module' with the actual name of your Python file

@pytest.mark.asyncio
async def test_scan():
    '''
    This test only works on a machine with a Bluetooth adapter and 1 or more nearby bluetooth devices responding to the scan.
    '''
    await BleakModel.start_scan()
    await asyncio.sleep(2.0)
    await BleakModel.stop_scan()  # Stop scan to ensure it's not running
    assert BleakModel.bt_devices

@pytest.mark.asyncio
async def test_unset_target_from_targetset_state():
    model = BleakModel()
    machine.add_model(model)
    # Manually put a mock device into the scanned devices list
    BleakModel.bt_devices = {'some_address': ('device', 'advertisement_data')}
    await model.set_target('some_address')
    await model.unset_target()
    assert model.state == "Init"

@pytest.mark.asyncio
async def test_unset_target_from_init_state():
    model = BleakModel()
    machine.add_model(model)
    with pytest.raises(transitions.core.MachineError):
        # Since no target was set, state is "Init". We can't unset a target from "Init" state, we must be in "TargetSet" state.
        await model.unset_target()

@pytest.mark.asyncio
async def test_clean_up_from_targetset_state():
    model = BleakModel(connection_timeout=0.5) # by default, 5.0 seconds. Setting to 0.5 seconds for faster testing
    machine.add_model(model)
    BleakModel.bt_devices = {'some_address': ('device', 'advertisement_data')}
    await model.set_target('some_address')
    assert model.state == "TargetSet"
    await model.clean_up()
    assert model.state == "Init"


@pytest.mark.asyncio
async def test_set_target_successful():
    model = BleakModel()
    machine.add_model(model)
    BleakModel.bt_devices = {'some_address': ('device', 'advertisement_data')}
    await model.set_target('some_address')
    assert model.target == 'some_address'
    assert model.state == "TargetSet"

@pytest.mark.asyncio
async def test_clean_up_from_streaming_state():
    model = BleakModel()
    machine.add_model(model)
    BleakModel.bt_devices = {'some_address': ('device', 'advertisement_data')}
    await model.set_target('some_address')
    assert model.state == "TargetSet"
    await model.connect()
    # Since we're mocking the address, connection should fail after timeout, which should be handled internally
    # and disconnect() called internally. Therefore we should be in "TargetSet" state.
    assert model.state == "TargetSet"
    await model.clean_up()
    assert model.state == "Init"

# TODO: Add tests for NoDevicesFoundError