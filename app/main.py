import os
import sys
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.controller import PipelineController
from ui.control_window import ControlWindow
from ui.context_window import ContextWindow
from ui.overlay_window import OverlayWindow
from ui.selection_window import SelectionWindow
from utils.config import load_config, save_user_config
from utils.dpi import set_process_dpi_awareness


def main() -> int:
    if os.environ.get("FORCE_DPI_AWARENESS") == "1":
        set_process_dpi_awareness()

    app = QtWidgets.QApplication(sys.argv)
    config = load_config()

    controller = PipelineController(config)
    overlay = OverlayWindow(config)
    selection = SelectionWindow()
    control = ControlWindow()
    context_cfg = config.get("ui", {}).get("context", {})
    context = ContextWindow(config) if context_cfg.get("enabled", True) else None
    input_mode = config.get("input", {}).get("mode", "ocr")
    control.set_mode(input_mode)

    def on_roi_selected(roi_logical):
        config["capture"]["roi"] = list(roi_logical)
        left, top, _right, _bottom = roi_logical
        screen = QtGui.QGuiApplication.screenAt(QtCore.QPoint(left, top))
        if screen:
            screens = QtGui.QGuiApplication.screens()
            monitor_index = screens.index(screen) if screen in screens else 0
            config["capture"]["monitor_index"] = monitor_index
            save_user_config(
                {"capture": {"roi": list(roi_logical), "monitor_index": monitor_index}}
            )
        else:
            save_user_config({"capture": {"roi": list(roi_logical)}})
        overlay.position_for_roi(roi_logical)
        if input_mode == "caption_http":
            wait_text = "Waiting for captions..."
        elif input_mode == "text_hook_clipboard":
            wait_text = "Waiting for text hook..."
        else:
            wait_text = "Waiting for OCR..."
        overlay.update_text(wait_text)
        overlay.show()
        control.position_for_roi(roi_logical)
        control.show()
        if context:
            context.position_for_roi(roi_logical)
            context.show()
        controller.start(roi_logical)

    def on_reselect():
        controller.stop()
        overlay.hide()
        control.hide()
        if context:
            if context_cfg.get("clear_on_reselect", True):
                context.clear_entries()
            context.hide()
        selection.activate()

    def on_toggle_context():
        if not context:
            return
        if context.isVisible():
            context.hide()
        else:
            context.show()

    def on_mode_changed(mode: str):
        nonlocal input_mode
        if mode == input_mode:
            return
        input_mode = mode
        config.setdefault("input", {})["mode"] = mode
        save_user_config({"input": {"mode": mode}})
        controller.stop()
        if config.get("capture", {}).get("roi"):
            on_roi_selected(tuple(config["capture"]["roi"]))
        else:
            selection.activate()

    selection.roi_selected.connect(on_roi_selected)
    control.reselect_requested.connect(on_reselect)
    control.context_toggle_requested.connect(on_toggle_context)
    control.mode_changed.connect(on_mode_changed)
    controller.translation_ready.connect(overlay.update_text)
    controller.ocr_ready.connect(overlay.update_raw_text)
    if context:
        controller.translation_pair.connect(context.append_entry)
    controller.status.connect(print)
    controller.status.connect(overlay.update_status)
    app.aboutToQuit.connect(controller.stop)

    use_last = "--use-last" in sys.argv
    if use_last and config.get("capture", {}).get("roi"):
        on_roi_selected(tuple(config["capture"]["roi"]))
    else:
        selection.activate()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
