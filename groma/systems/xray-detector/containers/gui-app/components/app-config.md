---
type: C4 Component
title: Konfig- och logginitiering
status: stable
groma:
  id: app-config
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/application/app_config.py
description: Läser valfri config.yaml och startar rotationsloggningen.
---

application/app_config.py: load_config_with_yaml() overrider AppConfig-defaults (klasser, default_model, confidence_threshold, data_dir) från en valfri YAML-fil (datakatalogen först, sedan arbetskatalogen) utan extra beroende; setup_logging() startar RotatingFileHandler under datakatalogens logs/ som app.py anropar vid start; statusmeddelanden i GUI loggas via xray-loggern.
