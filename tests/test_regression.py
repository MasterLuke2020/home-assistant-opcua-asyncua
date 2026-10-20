"""Offline regression tests for the existing YAML OPC-UA implementation.

These tests use lightweight stubs because no full Home Assistant or WAGO PLC is
available in the local audit environment. They test the real class source, not
simulated copies of method implementations. Full HA/PLC tests remain necessary.
"""
from __future__ import annotations

import ast
import asyncio
import logging
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

CODE = Path(__file__).resolve().parents[1] / "custom_components" / "asyncua"


class FakeCoordinatorBase:
    def __init__(self, *, hass, logger, name, update_interval):
        self.hass = hass
        self.name = name
        self.data = None

    def async_set_updated_data(self, new):
        self.data = new


class FakeHA:
    def __init__(self):
        self.tasks = []

    def async_create_task(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        return task


def load_classes(filename, names, env):
    """Compile class AST nodes as-is, with controlled external dependencies."""
    filepath = CODE / filename
    parsed = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    body = [n for n in parsed.body if isinstance(n, ast.ClassDef) and n.name in names]
    assert len(body) == len(names), (filename, names)
    preamble = ast.parse("from __future__ import annotations\n")
    module = ast.Module(body=preamble.body + body, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(filepath), "exec"), env)
    return [env[name] for name in names]


BaseEnv = {
    "asyncio": asyncio,
    "time": time,
    "Any": Any,
    "_LOGGER": logging.getLogger("test-opcua"),
    "DataUpdateCoordinator": FakeCoordinatorBase,
}
AsyncuaCoordinator, OpcuaSubscriptionHandler = load_classes(
    "__init__.py", ["AsyncuaCoordinator", "OpcuaSubscriptionHandler"], dict(BaseEnv)
)
AsyncuaButton, = load_classes("button.py", ["AsyncuaButton"], {
    "asyncio": asyncio,
    "_LOGGER": logging.getLogger("test-opcua-button"),
    "ButtonEntity": object,
})


def test_concurrent_pulses_on_same_node_are_serialized():
    async def scenario():
        ha = FakeHA()
        c = AsyncuaCoordinator(ha, "PLC", "opc.tcp://example.invalid:4840", 5)
        c.register_write_node("key", "ns=2;s=test")
        writes = []

        async def write(nodeid, value, **kwargs):
            writes.append((nodeid, value))
            await asyncio.sleep(0)

        c.async_write_bool = write
        b = AsyncuaButton(c, "key", "Test")
        b._pulse_time = 0.001
        await asyncio.gather(b._pulse(), b._pulse())
        assert [value for _node, value in writes] == [True, False, True, False]
        assert all(node == "ns=2;s=test" for node, _value in writes)
    asyncio.run(scenario())


def test_cancelled_pulse_attempts_to_reset_false():
    async def scenario():
        c = AsyncuaCoordinator(FakeHA(), "PLC", "opc.tcp://example.invalid:4840", 5)
        c.register_write_node("key", "ns=2;s=test")
        writes = []
        true_seen = asyncio.Event()

        async def write(_nodeid, value, **kwargs):
            writes.append(value)
            if value:
                true_seen.set()

        c.async_write_bool = write
        b = AsyncuaButton(c, "key", "Test")
        b._pulse_time = 60
        task = asyncio.create_task(b._pulse())
        await true_seen.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert writes == [True, False]
    asyncio.run(scenario())


def test_subscription_initial_notification_not_discarded_or_overwritten():
    async def scenario():
        c = AsyncuaCoordinator(FakeHA(), "PLC", "opc.tcp://example.invalid:4840", 5)
        c.register_data_node("key", "ns=2;s=key")
        c.async_set_updated_data({})
        node = SimpleNamespace(nodeid=SimpleNamespace(to_string=lambda: "ns=2;s=key"))

        async def read_value():
            return 0  # a value read before the subscribe notification

        node.read_value = read_value

        class Subscription:
            async def subscribe_data_change(self, subscribed_node):
                # emulate an asyncua callback while await is still active
                c._handler.datachange_notification(subscribed_node, 1, None)

        class Client:
            def get_node(self, nodeid):
                assert nodeid == "ns=2;s=key"
                return node

            async def create_subscription(self, *, period, handler):
                c._handler = handler
                return Subscription()

        c.client = Client()
        c._connected = True
        async def noop():
            return None
        c.async_connect = noop
        await c.start_subscription()
        assert c.data["key"] == 1
        assert "key" in c.subscribed_keys
    asyncio.run(scenario())


def test_read_reconnect_restores_subscription_without_blocking_read():
    async def scenario():
        ha = FakeHA()
        c = AsyncuaCoordinator(ha, "PLC", "opc.tcp://example.invalid:4840", 5)
        reads = 0
        reconnect_calls = []
        restored = asyncio.Event()

        async def read_once(nodeid):
            nonlocal reads
            reads += 1
            if reads == 1:
                raise ConnectionError("lost")
            return 21

        async def reconnect(*, rebuild_subscriptions):
            reconnect_calls.append(rebuild_subscriptions)

        async def restore():
            restored.set()

        c._read_once = read_once
        c.async_reconnect = reconnect
        c.start_subscription = restore
        assert await c.async_read_value("ns=2;s=temp") == 21
        await asyncio.wait_for(restored.wait(), timeout=2)
        assert reconnect_calls == [False]
        assert reads == 2
        await asyncio.gather(*ha.tasks)
    asyncio.run(scenario())


def test_manifest_schema_basics():
    import json
    manifest = json.loads((CODE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["domain"] == "asyncua"
    assert manifest["version"]
    assert any(item.startswith("asyncua==") for item in manifest["requirements"])


def test_all_python_sources_compile():
    for file in CODE.glob("*.py"):
        compile(file.read_text(encoding="utf-8"), str(file), "exec")
