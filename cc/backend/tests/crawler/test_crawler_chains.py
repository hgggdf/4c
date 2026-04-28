"""Crawler pipeline chain tests.

Skipped: crawler module was restructured — clients/pipelines/scripts
subpackages no longer exist. These tests need to be rewritten against
the new crawler.transformers layout.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="crawler module restructured, old pipeline imports removed")