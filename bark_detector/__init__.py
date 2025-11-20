# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Bark Detection System for Home Assistant

A simple bark detection system that monitors audio from a USB microphone,
detects barking events using decibel threshold analysis, and reports them
to Home Assistant via MQTT.
"""

__version__ = "1.0.0"
__author__ = "Bark Detector"
