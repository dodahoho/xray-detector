"""Trådinställningar för GPU-inferens (TASK-32)."""

import cv2
import pytest
import torch

from xray_detector.infrastructure.detectors import tuning


@pytest.fixture(autouse=True)
def reset_configured(monkeypatch):
    monkeypatch.setattr(tuning, "_configured", False)


def test_limits_threads_when_cuda_is_available(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    original_torch = torch.get_num_threads()
    original_cv = cv2.getNumThreads()
    try:
        tuning.configure_inference_threads()

        assert torch.get_num_threads() == 1
        assert cv2.getNumThreads() == 1
    finally:
        torch.set_num_threads(original_torch)
        cv2.setNumThreads(original_cv)


def test_keeps_threads_without_cuda(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    original_torch = torch.get_num_threads()
    original_cv = cv2.getNumThreads()

    tuning.configure_inference_threads()

    assert torch.get_num_threads() == original_torch
    assert cv2.getNumThreads() == original_cv


def test_runs_only_once(monkeypatch):
    calls = []
    monkeypatch.setattr(torch.cuda, "is_available", lambda: calls.append(1) or False)

    tuning.configure_inference_threads()
    tuning.configure_inference_threads()

    assert len(calls) == 1
