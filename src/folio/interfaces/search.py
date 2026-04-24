"""Search provider protocol — the search subsystem contract.

Any class that can search for stock images or SVG assets satisfies this
protocol via structural subtyping.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SearchProvider(Protocol):
    """Searches for stock images or SVG assets.

    Providers fetch results from external APIs or local indices.
    """

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[object]:
        """Search for assets matching the query.

        Args:
            query: Search terms.
            limit: Maximum number of results.

        Returns:
            List of search result objects (provider-specific shape).
        """
        ...
