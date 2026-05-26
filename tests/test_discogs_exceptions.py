from __future__ import annotations

import pytest

from app.connectors.discogs_client import (
    DiscogsAuthError,
    DiscogsError,
    DiscogsForbiddenError,
    DiscogsNotFoundError,
    DiscogsRateLimitError,
    exception_for_status,
)


@pytest.mark.parametrize(
    "status, expected_type, expected_code",
    [
        (401, DiscogsAuthError, 401),
        (403, DiscogsForbiddenError, 403),
        (404, DiscogsNotFoundError, 404),
        (429, DiscogsRateLimitError, 429),
    ],
)
def test_known_statuses_map_to_typed_exceptions(status, expected_type, expected_code) -> None:
    exc = exception_for_status(status, payload={"message": "x"})
    assert isinstance(exc, expected_type)
    assert isinstance(exc, DiscogsError)
    assert exc.status_code == expected_code
    assert exc.upstream_status == status
    assert exc.payload == {"message": "x"}


def test_other_client_errors_propagate_their_status() -> None:
    exc = exception_for_status(400)
    assert type(exc) is DiscogsError
    assert exc.status_code == 400


def test_upstream_server_errors_collapse_to_502() -> None:
    exc = exception_for_status(503)
    assert type(exc) is DiscogsError
    assert exc.status_code == 502
    assert exc.upstream_status == 503
