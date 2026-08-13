"""Infra-only regression guard for ADR 0003's first slice: fast-mlsirm
must actually be importable, and its compiled Rust core (not the NumPy
parity fallback) must be the module that loads -- silently falling back
would mean the `backend/Dockerfile` Rust toolchain step regressed
without anyone noticing, since the NumPy fallback still runs.
"""

from __future__ import annotations


def test_fast_mlsirm_rust_core_is_loaded_not_the_numpy_fallback() -> None:
    import fast_mlsirm._core  # noqa: F401 -- import itself is the assertion


def test_fast_mlsirm_can_simulate_a_dataset() -> None:
    from fast_mlsirm import MLS2PLMConfig, simulate

    data = simulate(MLS2PLMConfig(seed=20260101))
    assert data.Y.shape[0] > 0
    assert data.Y.shape[1] > 0
