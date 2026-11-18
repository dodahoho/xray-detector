"""Syntetiska bildpar i datasetvyn: märke, filter, utökning och återställning (TASK-88)."""

import numpy as np
import pytest
from PySide6.QtCore import QDate, QSize
from PySide6.QtWidgets import QDialog, QLabel, QMessageBox

from tests.conftest import synthetic_frame
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.dataset import (
    MODE_ALL,
    MODE_PER_TYPE,
    AnnotatedImage,
    VariationSettings,
)
from xray_detector.infrastructure.dataset_store.pending import save_pending
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.ui.dataset_view import (
    BUTTON_GROUP_GAP,
    HEADER_MARGINS,
    ORIGINALS_ONLY,
    SYNTHETIC_ICON_PATH,
    SYNTHETIC_ONLY,
    DatasetView,
)
from xray_detector.ui.variation_dialog import VariationDialog

ORIGINAL_GROUP = 1
ROTATION_GROUP = 2
FLIP_GROUP = 3


def _sample(fill: int = 60) -> AnnotatedImage:
    frame = np.full((40, 50, 3), fill, np.uint8)
    return AnnotatedImage(frame, [{"class_name": "kniv", "bbox": [2, 3, 10, 12]}])


@pytest.fixture
def service(tmp_path) -> DatasetStore:
    """Ett originalpar och två syntetiska par: en rotation och en vändning."""
    svc = DatasetStore(tmp_path / "datasets")
    svc.add_samples([_sample(60), _sample(120)], captured="2026-11-01T09:00:00")
    svc.add_variations(
        VariationSettings(
            mode=MODE_PER_TYPE,
            rotation=True,
            rotation_degrees=30,
            flip_horizontal=True,
        ),
        seed=5,
    )
    return svc




def _built(config, service, settings) -> DatasetView:
    view = DatasetView(config, service, settings)
    view.refresh()
    view.wait_for_refresh()
    return view


def _header_icons(view, group_id) -> list[QLabel]:
    """Ikonerna i rubrikraden; klassmärkena bär text i stället för en pixmap."""
    header, _frame = view._group_headers[group_id]
    return [
        label
        for label in header.parentWidget().findChildren(QLabel)
        if not label.pixmap().isNull()
    ]


def _select_type(view, key) -> None:
    view.type_combo.setCurrentIndex(view.type_combo.findData(key))


def test_synthetic_pair_shows_the_icon(qapp, config, service, settings):
    view = _built(config, service, settings)

    assert len(_header_icons(view, ROTATION_GROUP)) == 1
    assert len(_header_icons(view, FLIP_GROUP)) == 1
    assert _header_icons(view, ORIGINAL_GROUP) == []


def test_synthetic_icon_is_used_in_a_prepared_size(qapp, config, service, settings):
    """Ikonen ligger färdig i rätt storlek, så korten inte skalar den (TASK-120)."""
    view = _built(config, service, settings)

    icon = _header_icons(view, ROTATION_GROUP)[0]

    assert SYNTHETIC_ICON_PATH.is_file()
    assert icon.pixmap().size() == QSize(20, 20)


def test_synthetic_icon_sits_in_the_cards_top_right_corner(
    qapp, config, service, settings
):
    """Ikonen ligger sist i rubrikraden, alltså i kortets övre högra hörn (TASK-120)."""
    view = _built(config, service, settings)
    header, card = view._group_headers[ROTATION_GROUP]
    row = header.parentWidget()
    row.resize(400, row.sizeHint().height())
    row.layout().activate()

    icon = _header_icons(view, ROTATION_GROUP)[0]

    assert row is card.layout().itemAt(0).widget()
    assert icon.x() + icon.width() == row.width() - HEADER_MARGINS[2]
    assert icon.y() == HEADER_MARGINS[1]


def test_synthetic_icon_explains_the_variation(qapp, config, service, settings):
    view = _built(config, service, settings)

    icon = _header_icons(view, ROTATION_GROUP)[0]

    assert "rotation" in icon.toolTip()


def test_type_filter_shows_only_the_originals(qapp, config, service, settings):
    view = _built(config, service, settings)

    _select_type(view, "original")

    assert list(view._group_headers) == [ORIGINAL_GROUP]
    assert len(view._thumbs) == 2


def test_type_filter_shows_only_the_synthetic_pairs(qapp, config, service, settings):
    view = _built(config, service, settings)

    _select_type(view, "synthetic")

    assert list(view._group_headers) == [FLIP_GROUP, ROTATION_GROUP]
    assert len(view._thumbs) == 4


def test_type_filter_can_be_cleared(qapp, config, service, settings):
    view = _built(config, service, settings)
    _select_type(view, "synthetic")

    _select_type(view, None)

    assert list(view._group_headers) == [FLIP_GROUP, ROTATION_GROUP, ORIGINAL_GROUP]


def test_synthetic_filter_hides_the_pending_captures(qapp, config, tmp_path, settings):
    """Osparade fångster är alltid original, så de göms med de syntetiska."""
    service = DatasetStore(tmp_path / "datasets")
    service.add_samples([_sample()], captured="2026-11-01T09:00:00")
    service.add_variations(VariationSettings(count=1, flip_horizontal=True), seed=1)
    save_pending(
        tmp_path, [StreamFrame("left", synthetic_frame(), [], "kamera-vanster")]
    )
    view = _built(config, service, settings)
    assert "Osparade fångster" in view._section_headings

    _select_type(view, "synthetic")

    assert "Osparade fångster" not in view._section_headings
    assert all(not thumb.pending for thumb in view._thumbs)


def test_type_filter_combines_with_the_date_filter(qapp, config, service, settings):
    view = _built(config, service, settings)

    _select_type(view, "synthetic")
    view.date_filter.setChecked(True)
    view.date_from.setDate(QDate.fromString("2026-12-01", "yyyy-MM-dd"))
    view.date_to.setDate(QDate.fromString("2026-12-31", "yyyy-MM-dd"))

    assert view._group_headers == {}


def test_reset_button_is_disabled_without_synthetic_images(
    qapp, config, tmp_path, settings
):
    service = DatasetStore(tmp_path / "datasets")
    service.add_samples([_sample()])

    view = _built(config, service, settings)

    assert not view.reset_button.isEnabled()
    assert view.variation_button.isEnabled()


def test_reset_removes_the_synthetic_images(qapp, config, service, settings, monkeypatch):
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes),
    )
    view = _built(config, service, settings)
    messages = []
    view.status_changed.connect(messages.append)

    view._on_reset_synthetic()
    view.wait_for_refresh()

    assert [image["id"] for image in service.load_dataset()["images"]] == [1, 2]
    assert messages == ["Tog bort 2 syntetiska bildpar från datasetet"]
    assert list(view._group_headers) == [ORIGINAL_GROUP]
    assert not view.reset_button.isEnabled()


def test_reset_can_be_cancelled(qapp, config, service, settings, monkeypatch):
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.No),
    )
    view = _built(config, service, settings)

    view._on_reset_synthetic()

    assert len(service.load_dataset()["images"]) == 6


def test_reset_without_synthetic_images_reports_it(
    qapp, config, tmp_path, settings
):
    service = DatasetStore(tmp_path / "datasets")
    service.add_samples([_sample()])
    view = _built(config, service, settings)
    messages = []
    view.status_changed.connect(messages.append)

    view._on_reset_synthetic()

    assert messages == ["Det finns inga syntetiska bilder att ta bort"]


def test_extend_adds_the_variations_from_the_dialog(
    qapp, config, service, settings, monkeypatch
):
    def accept(self) -> QDialog.DialogCode:
        self.rotation.setChecked(True)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(VariationDialog, "exec", accept)
    view = _built(config, service, settings)
    messages = []
    view.status_changed.connect(messages.append)

    view._on_add_variations()
    view.wait_for_variations()
    view.wait_for_refresh()

    assert len(service.load_dataset()["images"]) == 8
    assert messages == ["Lade till 1 syntetiskt bildpar i datasetet"]
    assert len(view._group_headers) == 4


def test_extend_can_be_cancelled(qapp, config, service, settings, monkeypatch):
    monkeypatch.setattr(
        VariationDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )
    view = _built(config, service, settings)

    view._on_add_variations()
    view.wait_for_variations()

    assert len(service.load_dataset()["images"]) == 6


def test_extend_without_originals_reports_it(qapp, config, service, settings):
    service.delete_images([1, 2])
    view = _built(config, service, settings)
    messages = []
    view.status_changed.connect(messages.append)

    view._on_add_variations()

    assert messages == ["Det finns inga originalbilder att variera"]


def test_extend_button_opens_the_dialog_with_the_original_pairs(
    qapp, config, service, settings, monkeypatch
):
    opened = []

    def accept(self) -> QDialog.DialogCode:
        opened.append(self.pairs)
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(VariationDialog, "exec", accept)
    view = _built(config, service, settings)

    view.variation_button.click()

    assert opened == [1]


def test_type_filter_labels(qapp, config, service, settings):
    view = _built(config, service, settings)

    labels = [view.type_combo.itemText(index) for index in range(view.type_combo.count())]

    assert labels == ["Alla bilder", ORIGINALS_ONLY, SYNTHETIC_ONLY]


def test_variation_buttons_form_their_own_group_on_the_right(
    qapp, config, service, settings
):
    """Utöka/återställ ligger till höger med luft till exportknapparna (TASK-102)."""
    view = _built(config, service, settings)
    bar = view.layout().itemAt(0).layout()

    # raden börjar med en stretch, så knapparna ligger till höger
    assert bar.itemAt(0).spacerItem() is not None
    assert bar.itemAt(1).widget() is view.variation_button
    assert bar.itemAt(2).widget() is view.reset_button
    # mellanrummet gör utöka/återställ till en egen knappgrupp
    gap = bar.itemAt(3).spacerItem()
    assert gap is not None
    assert gap.sizeHint().width() == BUTTON_GROUP_GAP
    assert bar.itemAt(4).widget() is view.export_coco_button
    assert bar.itemAt(5).widget() is view.export_yolo_button
    # importen hör till samma grupp som exporterna (TASK-159)
    assert bar.itemAt(6).widget() is view.import_button


def test_synthetic_icon_lists_every_variation(qapp, config, tmp_path, settings):
    """En bild med flera variationer visar alla i tooltipen (TASK-106)."""
    service = DatasetStore(tmp_path / "datasets")
    service.add_samples([_sample(60), _sample(120)], captured="2026-11-01T09:00:00")
    service.add_variations(
        VariationSettings(
            count=1,
            mode=MODE_ALL,
            rotation=True,
            rotation_degrees=30,
            scale=True,
            scale_up_percent=20,
            scale_down_percent=20,
        ),
        seed=1,
    )
    view = _built(config, service, settings)

    icon = _header_icons(view, ROTATION_GROUP)[0]

    assert "rotation" in icon.toolTip() and "storlek" in icon.toolTip()
