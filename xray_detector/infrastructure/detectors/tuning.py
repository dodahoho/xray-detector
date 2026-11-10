"""Trådinställningar för GPU-inferens (TASK-32).

Inferensen körs på GPU, men både ultralytics och rfdetr gör letterbox,
normalisering och NMS på CPU. PyTorch sprider de små tensorerna över alla
kärnor som standard. Mätt med två strömmar i 30 fps kostar det:

    RF-DETR small   torch=12: 2176 % CPU   torch=1: 102 % CPU   (samma fps)
    YOLO26m         torch=12:   78 % CPU   torch=1:  56 % CPU   (samma fps)

Genomströmningen är oförändrad eftersom taket är videons 60 fps. Med CUDA
tillgängligt begränsas därför torch och OpenCV till en tråd. På en
CPU-only-maskin lämnas de orörda, där vinner flera trådar.
"""

_configured = False


def configure_inference_threads() -> None:
    """Begränsar torch och OpenCV till en CPU-tråd när CUDA används."""
    global _configured
    if _configured:
        return
    _configured = True
    import torch

    if not torch.cuda.is_available():
        return
    torch.set_num_threads(1)
    import cv2

    cv2.setNumThreads(1)
