from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

C = TypeVar("C")

Result = dict[str, Any]


@dataclass(frozen=True)
class CommandEntry(Generic[C]):
    parse: Callable[[Mapping[str, Any]], C]
    handle: Callable[[C], Awaitable[Result]]


class CommandRegistry:
    """Associe un nom de commande à son parseur et à son handler."""

    def __init__(self) -> None:
        self._entries: dict[str, CommandEntry[Any]] = {}

    def register(
        self,
        name: str,
        parse: Callable[[Mapping[str, Any]], C],
        handle: Callable[[C], Awaitable[Result]],
    ) -> None:
        if name in self._entries:
            raise ValueError(f"commande déjà enregistrée : {name}")
        self._entries[name] = CommandEntry(parse, handle)

    def get(self, name: str) -> CommandEntry[Any] | None:
        return self._entries.get(name)

    def names(self) -> list[str]:
        return sorted(self._entries)
