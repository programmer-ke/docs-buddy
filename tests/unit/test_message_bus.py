import pytest
from dataclasses import dataclass

from docs_buddy.adapters import InMemoryMessageBus, MemoryBusError
from docs_buddy.services.commands import Command
from docs_buddy.services.events import Event


@dataclass(frozen=True)
class DummyCommand(Command):
    pass


@dataclass(frozen=True)
class DummyEvent(Event):
    pass


def test_register_and_send_command() -> None:
    bus = InMemoryMessageBus()
    received = []

    def handler(*, command):
        received.append(command)

    bus.register_command_handler(DummyCommand, handler)
    cmd = DummyCommand()
    bus.send(cmd)
    assert len(received) == 1
    assert received[0] is cmd


def test_send_unregistered_command_raises() -> None:
    bus = InMemoryMessageBus()
    cmd = DummyCommand()
    with pytest.raises(MemoryBusError):
        bus.send(cmd)


def test_register_and_publish_event() -> None:
    bus = InMemoryMessageBus()
    received = []

    def handler(*, event):
        received.append(event)

    bus.register_event_handler(DummyEvent, handler)
    evt = DummyEvent()
    bus.publish(evt)
    assert len(received) == 1
    assert received[0] is evt


def test_multiple_handlers_for_same_event() -> None:
    bus = InMemoryMessageBus()
    received_1 = []
    received_2 = []

    def handler_1(*, event):
        received_1.append(event)

    def handler_2(*, event):
        received_2.append(event)

    bus.register_event_handler(DummyEvent, handler_1)
    bus.register_event_handler(DummyEvent, handler_2)

    evt = DummyEvent()
    bus.publish(evt)

    assert len(received_1) == 1
    assert received_1[0] is evt
    assert len(received_2) == 1
    assert received_2[0] is evt


def test_publish_unregistered_event_does_nothing() -> None:
    bus = InMemoryMessageBus()
    # Should not raise
    evt = DummyEvent()
    bus.publish(evt)


def test_handler_receives_correct_command_instance() -> None:
    bus = InMemoryMessageBus()
    captured = None

    def handler(*, command):
        nonlocal captured
        captured = command

    bus.register_command_handler(DummyCommand, handler)
    cmd = DummyCommand()
    bus.send(cmd)
    assert captured is cmd


def test_handler_receives_correct_event_instance() -> None:
    bus = InMemoryMessageBus()
    captured = None

    def handler(*, event):
        nonlocal captured
        captured = event

    bus.register_event_handler(DummyEvent, handler)
    evt = DummyEvent()
    bus.publish(evt)
    assert captured is evt


def test_different_command_types_isolated() -> None:
    @dataclass(frozen=True)
    class OtherCommand(Command):
        pass

    bus = InMemoryMessageBus()
    called = False

    def handler(*, command):
        nonlocal called
        called = True

    bus.register_command_handler(DummyCommand, handler)
    # Sending an unregistered other command should raise
    other_cmd = OtherCommand()
    with pytest.raises(MemoryBusError):
        bus.send(other_cmd)

    # The handler for TestCommand should not have been called
    assert not called

    # Sending a registered command still works (prove isolation)
    bus.send(DummyCommand())
    assert called


def test_different_event_types_isolated() -> None:
    @dataclass(frozen=True)
    class OtherEvent(Event):
        pass

    bus = InMemoryMessageBus()
    called = False

    def handler(*, event):
        nonlocal called
        called = True

    bus.register_event_handler(DummyEvent, handler)
    # Publishing an unregistered event should not trigger the handler
    other_evt = OtherEvent()
    bus.publish(other_evt)
    assert not called

    # Publishing a registered event does trigger it
    bus.publish(DummyEvent())
    assert called


def test_dynamic_registration() -> None:
    bus = InMemoryMessageBus()
    received = []

    def handler(*, command):
        received.append(command)

    # Send a command before registration (should raise)
    with pytest.raises(MemoryBusError):
        bus.send(DummyCommand())
    assert len(received) == 0

    # Register and send again - should now work
    bus.register_command_handler(DummyCommand, handler)
    cmd = DummyCommand()
    bus.send(cmd)
    assert len(received) == 1
    assert received[0] is cmd
