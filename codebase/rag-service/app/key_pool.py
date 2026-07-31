from dataclasses import dataclass, field
from time import monotonic
from typing import Callable


RECOVERABLE_STATUS_CODES = {401, 402, 408, 429, 502, 503, 524, 529}


@dataclass
class ApiKeySlot:
    name: str
    value: str = field(repr=False)
    cooldown_until: float = 0.0
    consecutive_failures: int = 0


class OpenRouterKeyPool:
    """Flow-aware key selection without ever logging credential values."""

    def __init__(
        self,
        keys: dict[str, str],
        flow_orders: dict[str, list[str]],
        *,
        clock: Callable[[], float] = monotonic,
    ):
        self._clock = clock
        self._slots: dict[str, ApiKeySlot] = {}
        seen_values: set[str] = set()
        for name, value in keys.items():
            clean_value = value.strip()
            if not clean_value or clean_value in seen_values:
                continue
            seen_values.add(clean_value)
            self._slots[name] = ApiKeySlot(name=name, value=clean_value)
        self._flow_orders = {
            flow: [name for name in order if name in self._slots]
            for flow, order in flow_orders.items()
        }

    @property
    def configured(self) -> bool:
        return bool(self._slots)

    def candidates(self, flow: str) -> list[ApiKeySlot]:
        preferred = self._flow_orders.get(flow, [])
        order = preferred + [name for name in self._slots if name not in preferred]
        slots = [self._slots[name] for name in order]
        now = self._clock()
        return [slot for slot in slots if slot.cooldown_until <= now]

    def mark_success(self, name: str) -> None:
        slot = self._slots[name]
        slot.consecutive_failures = 0
        slot.cooldown_until = 0.0

    def mark_failure(
        self,
        name: str,
        status_code: int | None,
        retry_after: float | None = None,
    ) -> None:
        slot = self._slots[name]
        slot.consecutive_failures += 1
        if status_code in {401, 402}:
            cooldown = 6 * 60 * 60
        elif status_code == 429:
            cooldown = retry_after or min(
                120.0,
                5.0 * (2 ** (slot.consecutive_failures - 1)),
            )
        else:
            cooldown = min(
                60.0,
                3.0 * (2 ** (slot.consecutive_failures - 1)),
            )
        slot.cooldown_until = self._clock() + max(1.0, cooldown)
