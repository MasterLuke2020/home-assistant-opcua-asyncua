from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from asyncua import Client, ua
from asyncua.ua.uatypes import DataValue
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import homeassistant.helpers.config_validation as cv

from .const import *

_LOGGER = logging.getLogger(__name__)

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------

BASE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_URL): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=5.0): vol.Coerce(float),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [BASE_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)


# ------------------------------------------------------------------
# SETUP
# ------------------------------------------------------------------


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})

    for hub_cfg in config.get(DOMAIN, []):
        name = hub_cfg[CONF_NAME]

        coordinator = AsyncuaCoordinator(
            hass=hass,
            name=name,
            url=hub_cfg[CONF_URL],
            scan_interval=float(hub_cfg.get(CONF_SCAN_INTERVAL, 5.0)),
        )

        # HA startup darf nie auf die PLC warten.
        coordinator.async_set_updated_data({})
        hass.data[DOMAIN][name] = coordinator

        async def _start_asyncua_after_ha_started(event, coord=coordinator):
            coord.start_background_tasks()

        hass.bus.async_listen_once("homeassistant_started", _start_asyncua_after_ha_started)

    async def shutdown_handler(event):
        for coord in hass.data[DOMAIN].values():
            await coord.async_shutdown()

    hass.bus.async_listen_once("homeassistant_stop", shutdown_handler)

    return True


# ------------------------------------------------------------------
# COORDINATOR
# ------------------------------------------------------------------


class AsyncuaCoordinator(DataUpdateCoordinator):
    """Shared OPC-UA connection, subscriptions and safe read/write helpers."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        url: str,
        scan_interval: float,
    ):
        self._hass = hass
        self.url = url
        self.client: Client | None = None

        self.nodes: dict[str, str] = {}
        self.data_node_keys: set[str] = set()

        self.subscription = None
        self.nodeid_to_key: dict[str, str] = {}
        self.subscribed_keys: set[str] = set()

        self._connect_lock = asyncio.Lock()
        self._op_lock = asyncio.Lock()
        self._reconnect_lock = asyncio.Lock()
        self._subscription_lock = asyncio.Lock()
        self._pulse_locks: dict[str, asyncio.Lock] = {}

        self._connected = False
        self._stopping = False

        self._keepalive_task: asyncio.Task | None = None
        self._subscription_bootstrap_task: asyncio.Task | None = None
        self._polling_task: asyncio.Task | None = None
        self._subscription_watchdog_task: asyncio.Task | None = None

        # bewusst kurz: lieber schnell reconnecten als Home Assistant minutenlang blockieren
        self._request_timeout = 5.0
        self._connect_timeout = 5.0
        self._disconnect_timeout = 2.0
        self._keepalive_interval = 60.0

        # v7: Polling als Sicherheitsnetz, wenn die Subscription still stirbt.
        # Die Subscription bleibt für schnelle Updates zuständig; Polling verhindert stehende Werte.
        # Polling is only a safety net. With many nodes a 5 s full poll creates
        # unnecessary load and can race against subscription updates.
        self._poll_interval = max(float(scan_interval or 5.0), 30.0)
        self._subscription_watchdog_interval = 60.0
        self._subscription_rebuild_after = 300.0
        self._last_datachange = time.monotonic()
        # Per-key timestamp prevents a slow fallback poll from overwriting a newer
        # subscription value with a stale value read earlier in the poll cycle.
        self._last_datachange_by_key: dict[str, float] = {}
        self._last_successful_poll = 0.0

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=name,
            update_interval=None,  # Subscription + eigener Fallback-Poll
        )

    @property
    def connected(self) -> bool:
        return self._connected and self.client is not None

    def register_data_node(self, key: str, nodeid: str) -> None:
        self.nodes[key] = nodeid
        self.data_node_keys.add(key)

    def register_write_node(self, key: str, nodeid: str) -> None:
        self.nodes[key] = nodeid

    def pulse_lock_for(self, nodeid: str) -> asyncio.Lock:
        """Serialize momentary button pulses targeting the same OPC-UA node."""
        return self._pulse_locks.setdefault(nodeid, asyncio.Lock())

    def start_background_tasks(self) -> None:
        """Start all async background workers after HA has finished startup."""
        if self._keepalive_task is None or self._keepalive_task.done():
            self._keepalive_task = self._hass.async_create_task(self._keepalive_loop())

        if self._polling_task is None or self._polling_task.done():
            self._polling_task = self._hass.async_create_task(self._polling_fallback_loop())

        if self._subscription_watchdog_task is None or self._subscription_watchdog_task.done():
            self._subscription_watchdog_task = self._hass.async_create_task(
                self._subscription_watchdog_loop()
            )

        if (
            self._subscription_bootstrap_task is None
            or self._subscription_bootstrap_task.done()
        ):
            self._subscription_bootstrap_task = self._hass.async_create_task(
                self._delayed_subscription_start()
            )

    async def _delayed_subscription_start(self) -> None:
        await asyncio.sleep(1)
        try:
            await self.start_subscription()
        except asyncio.CancelledError:
            raise
        except Exception as err:
            _LOGGER.warning(
                "Background OPC-UA subscription start failed for %s: %s",
                self.name,
                err,
            )

    async def async_shutdown(self) -> None:
        self._stopping = True

        for task_name in (
            "_keepalive_task",
            "_subscription_bootstrap_task",
            "_polling_task",
            "_subscription_watchdog_task",
        ):
            task = getattr(self, task_name)
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                setattr(self, task_name, None)

        await self.async_disconnect()

    async def async_connect(self) -> None:
        async with self._connect_lock:
            if self.connected:
                return

            _LOGGER.info("Connecting OPC-UA hub %s to %s", self.name, self.url)

            client = Client(self.url, timeout=self._request_timeout)
            await asyncio.wait_for(client.connect(), timeout=self._connect_timeout)

            self.client = client
            self._connected = True

    async def async_disconnect(self) -> None:
        async with self._connect_lock:
            self._connected = False

            subscription = self.subscription
            client = self.client

            self.subscription = None
            self.nodeid_to_key.clear()
            self.subscribed_keys.clear()
            self.client = None

            if subscription is not None:
                try:
                    await asyncio.wait_for(subscription.delete(), timeout=self._disconnect_timeout)
                except Exception as err:
                    _LOGGER.debug("Ignoring subscription delete error for %s: %s", self.name, err)

            if client is not None:
                try:
                    await asyncio.wait_for(client.disconnect(), timeout=self._disconnect_timeout)
                except Exception as err:
                    _LOGGER.debug("Ignoring disconnect error for %s: %s", self.name, err)

    async def async_reconnect(self, *, rebuild_subscriptions: bool = True) -> None:
        if self._stopping:
            return

        async with self._reconnect_lock:
            _LOGGER.warning("Reconnecting OPC-UA hub %s", self.name)

            await self.async_disconnect()
            await self.async_connect()

            if rebuild_subscriptions:
                await self.start_subscription()

    def _schedule_reconnect(self) -> None:
        if self._stopping:
            return
        self._hass.async_create_task(self.async_reconnect(rebuild_subscriptions=True))

    def _get_node(self, nodeid: str):
        if self.client is None:
            raise ConnectionError(f"OPC-UA client for {self.name} is not connected")
        return self.client.get_node(nodeid)

    async def _read_once(self, nodeid: str) -> Any:
        await self.async_connect()
        node = self._get_node(nodeid)
        return await asyncio.wait_for(node.read_value(), timeout=self._request_timeout)

    async def _write_bool_once(self, nodeid: str, value: bool) -> None:
        await self.async_connect()
        node = self._get_node(nodeid)
        await asyncio.wait_for(
            node.write_value(DataValue(ua.Variant(value, ua.VariantType.Boolean))),
            timeout=self._request_timeout,
        )

    async def async_read_value(self, nodeid: str, *, retry: bool = True) -> Any:
        async with self._op_lock:
            try:
                return await self._read_once(nodeid)
            except Exception as err:
                if not retry:
                    raise
                _LOGGER.warning(
                    "OPC-UA read failed on hub %s for %s: %s. Reconnecting and retrying once.",
                    self.name,
                    nodeid,
                    err,
                )
                await self.async_reconnect(rebuild_subscriptions=False)
                value = await self._read_once(nodeid)
                # A reconnect removed the old subscription; restore it promptly.
                self._hass.async_create_task(self.start_subscription())
                return value

    async def async_write_bool(self, nodeid: str, value: bool, *, retry: bool = True) -> None:
        async with self._op_lock:
            try:
                await self._write_bool_once(nodeid, value)
                return
            except Exception as err:
                if not retry:
                    raise
                _LOGGER.warning(
                    "OPC-UA write failed on hub %s for %s=%s: %s. Reconnecting and retrying once.",
                    self.name,
                    nodeid,
                    value,
                    err,
                )
                await self.async_reconnect(rebuild_subscriptions=False)
                await self._write_bool_once(nodeid, value)
                self._hass.async_create_task(self.start_subscription())

    async def _async_update_data(self) -> dict[str, Any]:
        return await self._read_all_data_nodes()

    async def _read_all_data_nodes(self) -> dict[str, Any]:
        """Read data nodes without overwriting newer subscription updates.

        A complete fallback poll can take a while with many PLC nodes.  The old
        implementation built one snapshot and published it only at the end.  If
        a subscription update arrived in between, that fresh value could be
        overwritten by an older polled value.  We now merge each value only when
        no newer subscription notification for that key arrived since the read
        started.
        """
        any_success = False

        for key in list(self.data_node_keys):
            if self._stopping:
                break

            nodeid = self.nodes.get(key)
            if nodeid is None:
                continue

            read_started = time.monotonic()
            try:
                value = await self.async_read_value(nodeid)
            except Exception as err:
                _LOGGER.debug("Polling read failed for %s (%s): %s", key, nodeid, err)
                continue

            # No await between this check and publishing, so a subscription
            # callback cannot interleave on the HA event loop here.
            last_subscription_update = self._last_datachange_by_key.get(key, 0.0)
            if last_subscription_update <= read_started:
                new_data = dict(self.data or {})
                new_data[key] = value
                self.async_set_updated_data(new_data)

            any_success = True

        if any_success:
            self._last_successful_poll = time.monotonic()

        return dict(self.data or {})

    async def start_subscription(self) -> None:
        """Create subscription and add data nodes. Safe to call repeatedly."""
        async with self._subscription_lock:
            if not self.data_node_keys or self._stopping:
                return

            try:
                await self.async_connect()
            except Exception as err:
                _LOGGER.warning("Cannot start OPC-UA subscription for %s: %s", self.name, err)
                return

            if self.client is None:
                return

            if self.subscription is None:
                _LOGGER.info("Starting OPC-UA subscription for %s", self.name)
                handler = OpcuaSubscriptionHandler(self)

                try:
                    self.subscription = await asyncio.wait_for(
                        self.client.create_subscription(period=100, handler=handler),
                        timeout=self._request_timeout,
                    )
                except Exception as err:
                    _LOGGER.warning("Creating subscription failed for %s: %s", self.name, err)
                    await self.async_disconnect()
                    return

            # Initial values must not overwrite newer notifications received
            # while other nodes are being subscribed.
            initial_values: dict[str, tuple[Any, float]] = {}

            for key in list(self.data_node_keys):
                if self._stopping:
                    return
                if key in self.subscribed_keys:
                    continue

                nodeid = self.nodes.get(key)
                if nodeid is None:
                    continue

                try:
                    node = self._get_node(nodeid)
                    read_started = time.monotonic()
                    value = await asyncio.wait_for(node.read_value(), timeout=self._request_timeout)
                    initial_values[key] = (value, read_started)
                except Exception as err:
                    _LOGGER.debug("Initial read skipped/failed for %s (%s): %s", key, nodeid, err)
                    continue

                nodeid_str = node.nodeid.to_string()
                # asyncua may deliver the initial notification before await returns.
                self.nodeid_to_key[nodeid_str] = key
                try:
                    await asyncio.wait_for(
                        self.subscription.subscribe_data_change(node),
                        timeout=self._request_timeout,
                    )
                    self.subscribed_keys.add(key)
                    _LOGGER.debug("Subscribed node %s -> %s", key, nodeid)
                except Exception as err:
                    self.nodeid_to_key.pop(nodeid_str, None)
                    _LOGGER.warning("Subscribe failed for %s (%s): %s", key, nodeid, err)

            new_data = dict(self.data or {})
            for key, (value, read_started) in initial_values.items():
                if self._last_datachange_by_key.get(key, 0.0) <= read_started:
                    new_data[key] = value

            self._last_datachange = time.monotonic()
            self.async_set_updated_data(new_data)

    async def rebuild_subscription(self) -> None:
        """Drop only subscription state and recreate it without disconnecting the whole client."""
        async with self._subscription_lock:
            subscription = self.subscription
            self.subscription = None
            self.nodeid_to_key.clear()
            self.subscribed_keys.clear()

            if subscription is not None:
                try:
                    await asyncio.wait_for(subscription.delete(), timeout=self._disconnect_timeout)
                except Exception as err:
                    _LOGGER.debug("Ignoring subscription rebuild delete error for %s: %s", self.name, err)

        await self.start_subscription()

    async def _polling_fallback_loop(self) -> None:
        """Safety net: keep sensor values alive even if OPC-UA subscriptions silently stop."""
        while not self._stopping:
            await asyncio.sleep(self._poll_interval)
            if self._stopping or not self.data_node_keys:
                continue

            try:
                new_data = await self._read_all_data_nodes()
                if new_data:
                    self.async_set_updated_data(new_data)
            except asyncio.CancelledError:
                raise
            except Exception as err:
                _LOGGER.warning("OPC-UA fallback polling failed for hub %s: %s", self.name, err)

    async def _subscription_watchdog_loop(self) -> None:
        """Rebuild subscription periodically if it appears stale."""
        while not self._stopping:
            await asyncio.sleep(self._subscription_watchdog_interval)
            if self._stopping or not self.data_node_keys:
                continue

            age = time.monotonic() - self._last_datachange
            if self.subscription is None:
                _LOGGER.warning("OPC-UA subscription missing for hub %s. Rebuilding.", self.name)
                try:
                    await self.start_subscription()
                except Exception as err:
                    _LOGGER.warning("OPC-UA subscription rebuild failed for %s: %s", self.name, err)
                continue

            if age >= self._subscription_rebuild_after:
                _LOGGER.warning(
                    "OPC-UA subscription for hub %s had no datachange for %.0fs. Rebuilding subscription.",
                    self.name,
                    age,
                )
                try:
                    await self.rebuild_subscription()
                except Exception as err:
                    _LOGGER.warning("OPC-UA stale subscription rebuild failed for %s: %s", self.name, err)

    async def _keepalive_loop(self) -> None:
        """Detect broken asyncua internals before the next button press."""
        while not self._stopping:
            await asyncio.sleep(self._keepalive_interval)
            if self._stopping:
                return

            try:
                if not self.connected:
                    await self.async_reconnect(rebuild_subscriptions=True)
                    continue

                if self.client is None:
                    raise ConnectionError("OPC-UA client missing")

                await asyncio.wait_for(
                    self.client.nodes.server_state.read_value(),
                    timeout=self._request_timeout,
                )
            except asyncio.CancelledError:
                raise
            except Exception as err:
                _LOGGER.warning(
                    "OPC-UA keepalive failed for hub %s: %s. Reconnecting.",
                    self.name,
                    err,
                )
                try:
                    await self.async_reconnect(rebuild_subscriptions=True)
                except Exception as reconnect_err:
                    _LOGGER.warning(
                        "OPC-UA keepalive reconnect failed for hub %s: %s",
                        self.name,
                        reconnect_err,
                    )


# ------------------------------------------------------------------
# SUBSCRIPTION HANDLER
# ------------------------------------------------------------------


class OpcuaSubscriptionHandler:
    def __init__(self, coordinator: AsyncuaCoordinator):
        self.coordinator = coordinator

    def datachange_notification(self, node, val, data):
        nodeid_str = node.nodeid.to_string()
        key = self.coordinator.nodeid_to_key.get(nodeid_str)
        if key is None:
            return

        now = time.monotonic()
        self.coordinator._last_datachange = now
        self.coordinator._last_datachange_by_key[key] = now

        new_data = dict(self.coordinator.data or {})
        new_data[key] = val
        self.coordinator.async_set_updated_data(new_data)

    def status_change_notification(self, status):
        _LOGGER.warning(
            "OPC-UA subscription status changed for hub %s: %s",
            self.coordinator.name,
            status,
        )
        self.coordinator._schedule_reconnect()
