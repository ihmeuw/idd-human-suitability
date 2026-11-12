"""Shared test setup: figures are drawn off screen."""

from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")
