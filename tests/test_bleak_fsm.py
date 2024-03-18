import pytest
import asyncio
import transitions
from bleak_fsm import BleakModel # Replace 'your_module' with the actual name of your Python file

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
async def test_skip_targetset_and_connect_fails():
    model = BleakModel()
    with pytest.raises(transitions.core.MachineError):
        await model.connect()

@pytest.mark.asyncio
async def test_unset_target_from_targetset_state():
    model = BleakModel()
    # Manually put a mock device into the scanned devices list
    BleakModel.bt_devices = {'some_address': ('device', 'advertisement_data')}
    await model.set_target('some_address')
    await model.unset_target()
    assert model.state == "Init"

@pytest.mark.asyncio
async def test_unset_target_from_init_state():
    model = BleakModel()
    #machine.add_model(model)
    with pytest.raises(transitions.core.MachineError):
        # Since no target was set, state is "Init". We can't unset a target from "Init" state, we must be in "TargetSet" state.
        await model.unset_target()

@pytest.mark.asyncio
async def test_clean_up_from_targetset_state():
    model = BleakModel(connection_timeout=0.2)
    BleakModel.bt_devices = {'some_address': ('device', 'advertisement_data')}
    await model.set_target('some_address')
    assert model.state == "TargetSet"
    await model.clean_up()
    assert model.state == "Init"


@pytest.mark.asyncio
async def test_set_target_successful():
    model = BleakModel()
    BleakModel.bt_devices = {'some_address': ('device', 'advertisement_data')}
    await model.set_target('some_address')
    assert model.target == 'some_address'
    assert model.state == "TargetSet"

@pytest.mark.asyncio
async def test_set_target_failure():
    model = BleakModel()
    await model.set_target('non_existent_address')
    assert model.state == "Init"

@pytest.mark.asyncio
async def test_clean_up_from_streaming_state():
    model = BleakModel()
    BleakModel.bt_devices = {'some_address': ('device', 'advertisement_data')}
    await model.set_target('some_address')
    assert model.state == "TargetSet"
    await model.connect()
    # Since we're mocking the address, connection should fail after timeout, which should be handled internally
    # and disconnect() called internally. Therefore we should be in "TargetSet" state.
    assert model.state == "TargetSet"
    await model.clean_up()
    assert model.state == "Init"

### Context Manager ###
    
@pytest.mark.asyncio
async def test_context_manager_from_targetset():
    model = BleakModel()
    BleakModel.bt_devices = {'some_address': ('device', 'advertisement_data')}
    async with model:
        await model.set_target('some_address')
        assert model.state == "TargetSet"
    assert model.state == "Init"
    
@pytest.mark.asyncio
async def test_context_manager_from_failed_connected():
    model = BleakModel()
    BleakModel.bt_devices = {'some_address': ('device', 'advertisement_data')}
    async with model:
        await model.set_target('some_address') 
        should_fail = await model.connect() # since 'some_address' isn't real, should fail.
        assert not should_fail
        assert model.state == "TargetSet" 
    assert model.state == "Init"

# Since we can't go further than "TargetSet" state, we can't test the context manager from "Connected" or "Streaming" state.
    
# Test idea:
# If user doesn't set the proper callbacks (model.enable_notifications, model.disable_notifications, model.set_measurement_handler)
# Then `await model.stream()` should fail, returning False
# and the state shouldn't have changed (should be Connected)
# This is a regression test that is currently untestable because
# we never actually connect to a real device.