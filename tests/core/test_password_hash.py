"""Unit tests for password_hash — crypto utility, mocks PBKDF2 for speed."""
from __future__ import annotations

import hashlib
import unittest.mock as mock

import pytest

from app.core.password_hash import (
    get_hash_info,
    hash_password,
    needs_rehash,
    verify_password,
)


class TestHashPassword:
    """hash_password produces valid PBKDF2 hashes."""

    def test_returns_string_prefixed_with_q_marker(self):
        h = hash_password("test_password")
        assert h.startswith("$q$1$")

    def test_produces_different_salts_each_call(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2  # different random salt

    def test_hash_length_reasonable(self):
        h = hash_password("x" * 100)
        # $q$1$ + base64(16 salt + 32 key) = 5 + 64 = 69 chars
        assert 60 < len(h) < 100


class TestVerifyPassword:
    """verify_password correctly validates against different hash formats."""

    def test_verify_correct_password_v1(self):
        h = hash_password("my_secret")
        assert verify_password("my_secret", h) is True

    def test_verify_wrong_password_v1(self):
        h = hash_password("my_secret")
        assert verify_password("wrong_password", h) is False

    def test_verify_legacy_sha256_hex_rejected(self):
        legacy_hash = hashlib.sha256("test".encode()).hexdigest()
        assert verify_password("test", legacy_hash) is False
        assert verify_password("wrong", legacy_hash) is False

    def test_verify_invalid_format_returns_false(self):
        assert verify_password("anything", "not_a_valid_hash!!!") is False

    def test_verify_empty_hash(self):
        assert verify_password("anything", "") is False

    def test_verify_empty_password(self):
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("not_empty", h) is False


class TestNeedsRehash:
    """needs_rehash identifies hashes that need upgrading."""

    def test_v1_hash_no_rehash_needed(self):
        h = hash_password("x")
        assert needs_rehash(h) is False

    def test_v0_hash_needs_rehash(self):
        assert needs_rehash("$q$0$something") is True

    def test_raw_hex_needs_rehash(self):
        assert needs_rehash(hashlib.sha256("x".encode()).hexdigest()) is True

    def test_unknown_format_needs_rehash(self):
        assert needs_rehash("random_string") is True


class TestGetHashInfo:
    """get_hash_info returns correct algorithm and rehash flag."""

    def test_pbkdf2_v1(self):
        h = hash_password("x")
        algo, needs = get_hash_info(h)
        assert algo == "pbkdf2_sha256"
        assert needs is False

    def test_v0_marker(self):
        algo, needs = get_hash_info("$q$0$salt+key")
        assert algo == "pbkdf2_sha256_legacy"
        assert needs is True

    def test_raw_hex(self):
        hex_hash = hashlib.sha256("x".encode()).hexdigest()
        algo, needs = get_hash_info(hex_hash)
        assert algo == "sha256_raw"
        assert needs is True

    def test_unknown_format(self):
        algo, needs = get_hash_info("totally_unknown")
        assert algo == "unknown"
        assert needs is True
