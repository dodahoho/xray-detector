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

application/app_config.py: load_config_with_yaml() overrider AppConfig-defaults (klasser, default_model, confidence_threshold, data_dir, models_dir, logs_dir) från en valfri YAML-fil (datakatalogen först, sedan arbetskatalogen) utan extra beroende; relativa models_dir/logs_dir tolkas mot projektroten. setup_logging() startar RotatingFileHandler för logs/app.log (1 MB, 5 backups) som app.py anropar vid start, och log_path()/rotating_handler()/file_logger() ger samma rotation och format åt fler loggtyper under logs/ – träningsvyn skriver logs/training.log via file_logger(). Statusmeddelanden i GUI loggas via xray-loggern.
