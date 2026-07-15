#!/usr/bin/env python3
"""Validate the Agent Project Orchestrator package and scenario providers.

This remains a package-level doctor. It validates the three-scenario MVP but
neither implements nor certifies the future projectctl transactional runtime.
"""

from __future__ import annotations

import argparse
import json
import re