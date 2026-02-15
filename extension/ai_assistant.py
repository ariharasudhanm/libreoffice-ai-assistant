# LibreOffice AI Assistant Extension
# Copyright (c) 2026 Local MVP — MIT License
# See LICENSE file for details.

"""LibreOffice AI Assistant - Extension with Dialog UI

Provides AI-powered text manipulation via a modeless dialog.
The dialog stays open so users can select text, generate previews,
and apply results in a two-step workflow.
"""

import sys
import os
import uno
import unohelper
from com.sun.star.task import XJobExecutor
from com.sun.star.awt import XActionListener, XTopWindowListener, XItemListener
from com.sun.star.awt import MessageBoxButtons as MSG_BUTTONS
from com.sun.star.awt.PosSize import POS, SIZE, POSSIZE
from com.sun.star.awt.PushButtonType import OK, CANCEL

# Add pythonpath to sys.path
def _ensure_pythonpath():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        py_path = os.path.join(current_dir, "pythonpath")
        if os.path.isdir(py_path) and py_path not in sys.path:
            sys.path.insert(0, py_path)
    except Exception:
        pass

_ensure_pythonpath()

from ollama_client import generate as ollama_generate
from prompts import build_prompt


# ---------- Global references to keep modeless dialog alive ----------
_g_dialog = None
_g_handler = None
_g_close_listener = None
_g_action_listener = None


def _close_dialog():
    """Close and dispose the global dialog."""
    global _g_dialog, _g_handler, _g_close_listener, _g_action_listener
    if _g_dialog is not None:
        try:
            _g_dialog.setVisible(False)
            _g_dialog.dispose()
        except Exception:
            pass
    _g_dialog = None
    _g_handler = None
    _g_close_listener = None
    _g_action_listener = None


class _CloseListener(unohelper.Base, XTopWindowListener):
    """Handles the window X button on the modeless dialog."""
    def windowClosing(self, event):
        _close_dialog()
    def windowOpened(self, event): pass
    def windowClosed(self, event): pass
    def windowMinimized(self, event): pass
    def windowNormalized(self, event): pass
    def windowActivated(self, event): pass
    def windowDeactivated(self, event): pass
    def disposing(self, event): pass


class _ActionRadioListener(unohelper.Base, XItemListener):
    """Updates Tone and instructions label based on selected action."""

    def __init__(self, dialog):
        self._dialog = dialog

    def _get_selected_action(self):
        for name, action in (("action_rewrite", "rewrite"),
                             ("action_summarize", "summarize"),
                             ("action_grammar", "grammar"),
                             ("action_translate", "translate"),
                             ("action_continue", "continue"),
                             ("action_simplify", "simplify"),
                             ("action_custom", "custom")):
            if self._dialog.getControl(name).getState():
                return action
        return "rewrite"

    def itemStateChanged(self, event):
        action = self._get_selected_action()
        is_rewrite = (action == "rewrite")

        # Tone only for Rewrite
        for name in ("tone_formal", "tone_concise", "tone_academic"):
            self._dialog.getControl(name).getModel().Enabled = is_rewrite
        grp = self._dialog.getControl("tone_group")
        grp.getModel().Label = "Tone" if is_rewrite else "Tone (only for Rewrite)"

        # Update instructions label based on action
        lbl = self._dialog.getControl("custom_label")
        hints = {
            "translate": "Target language (e.g. Spanish, German, Japanese):",
            "continue": "Direction for continuation (optional):",
            "custom": "Your prompt / instructions:",
        }
        lbl.setText(hints.get(action,
                              "Additional instructions (optional):"))

    def disposing(self, event):
        pass


# ---------- Dialog handler ----------

class _DialogHandler(unohelper.Base, XActionListener):
    """Handles button clicks in the AI Assistant dialog."""

    def __init__(self, dialog, ctx):
        self._dialog = dialog
        self._ctx = ctx
        self._last_output = ""
        self._selection_text = ""
        self._saved_cursor = None  # persistent ref to selected range
        self._last_action = ""     # action used during last Generate

    # -- XActionListener --
    def actionPerformed(self, event):
        name = event.Source.getModel().Name
        if name == "generate_btn":
            self._on_generate()
        elif name == "apply_btn":
            self._on_apply()
        elif name == "close_btn":
            _close_dialog()
        elif name == "refresh_btn":
            self._on_refresh_selection()

    def disposing(self, event):
        pass

    # -- helpers --
    def _set_status(self, text):
        self._dialog.getControl("status_label").setText(text)

    def _set_preview(self, text):
        self._dialog.getControl("preview_box").setText(text)

    def _get_action(self):
        for name, action in (("action_summarize", "summarize"),
                             ("action_grammar", "grammar"),
                             ("action_translate", "translate"),
                             ("action_continue", "continue"),
                             ("action_simplify", "simplify"),
                             ("action_custom", "custom")):
            if self._dialog.getControl(name).getState():
                return action
        return "rewrite"

    def _get_custom_instructions(self):
        return self._dialog.getControl("custom_box").getText().strip()

    def _get_tone(self):
        if self._dialog.getControl("tone_concise").getState():
            return "Concise"
        if self._dialog.getControl("tone_academic").getState():
            return "Academic"
        return "Formal"

    def _get_output_mode(self):
        ctrl = self._dialog.getControl("output_comment")
        return "comment" if ctrl.getState() else "replace"

    def _get_selection_text(self, save_cursor=False):
        """Read selected text from the Writer document.
        If save_cursor=True, store a persistent TextCursor so Apply works
        even after the selection is lost (when dialog gets focus)."""
        try:
            desktop = self._ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", self._ctx)
            doc = desktop.getCurrentComponent()
            if not doc or not hasattr(doc, "Text"):
                return ""
            selection = doc.CurrentController.getSelection()
            if selection and hasattr(selection, "getCount") and selection.getCount() > 0:
                parts = []
                for i in range(selection.getCount()):
                    try:
                        parts.append(selection.getByIndex(i).getString())
                    except Exception:
                        pass
                text = "\n".join(p for p in parts if p)
                if save_cursor and text.strip():
                    rng = selection.getByIndex(0)
                    self._saved_cursor = rng.getText().createTextCursorByRange(rng)
                return text
        except Exception:
            pass
        return ""

    def _replace_selection(self, new_text):
        """Replace text using the saved cursor (survives focus changes)."""
        if self._saved_cursor:
            self._saved_cursor.setString(new_text)
            self._saved_cursor = None
            return
        # Fallback: try current selection
        desktop = self._ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self._ctx)
        doc = desktop.getCurrentComponent()
        if doc and hasattr(doc, "Text"):
            selection = doc.CurrentController.getSelection()
            if selection and selection.getCount() > 0:
                selection.getByIndex(0).setString(new_text)

    def _append_after_selection(self, new_text):
        """Insert text right after the saved cursor (for Continue action)."""
        if self._saved_cursor:
            cursor = self._saved_cursor.getText().createTextCursorByRange(
                self._saved_cursor)
            cursor.collapseToEnd()
            cursor.getText().insertString(cursor, " " + new_text, False)
            self._saved_cursor = None
            return
        # Fallback: insert at current cursor position
        desktop = self._ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self._ctx)
        doc = desktop.getCurrentComponent()
        if doc and hasattr(doc, "Text"):
            view_cursor = doc.CurrentController.getViewCursor()
            text = doc.getText()
            text.insertString(view_cursor, " " + new_text, False)

    def _insert_comment(self, comment_text):
        """Insert an annotation using saved cursor or current selection."""
        desktop = self._ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self._ctx)
        doc = desktop.getCurrentComponent()
        if not doc or not hasattr(doc, "Text"):
            return
        # Use saved cursor if available, otherwise current selection
        text_range = self._saved_cursor
        if not text_range:
            selection = doc.CurrentController.getSelection()
            if selection and selection.getCount() > 0:
                text_range = selection.getByIndex(0)
        if not text_range:
            return
        try:
            annotation = doc.createInstance(
                "com.sun.star.text.TextField.Annotation")
            annotation.Content = comment_text
            annotation.Author = "AI Assistant"
            text_range.getText().insertTextContent(
                text_range, annotation, False)
        except Exception:
            cursor = text_range.getText().createTextCursorByRange(
                text_range)
            cursor.collapseToEnd()
            cursor.getText().insertString(
                cursor, f" ({comment_text})", False)
        self._saved_cursor = None

    def _update_selection_display(self, text):
        """Update the selection preview and word count."""
        sel_ctrl = self._dialog.getControl("selection_box")
        info_ctrl = self._dialog.getControl("selection_info")

        if text.strip():
            # Show a truncated preview
            preview = text[:300]
            if len(text) > 300:
                preview += "..."
            sel_ctrl.setText(preview)
            words = len(text.split())
            chars = len(text)
            info_ctrl.setText(f"{words} words, {chars} characters selected")
        else:
            sel_ctrl.setText("")
            info_ctrl.setText("No text selected — highlight text in the document")

    # -- button handlers --
    def _on_refresh_selection(self):
        """Refresh the selected text display."""
        text = self._get_selection_text()
        self._selection_text = text
        self._update_selection_display(text)
        if text.strip():
            self._set_status("Selection updated. Ready to generate.")
        else:
            self._set_status("No text selected.")

    def _on_generate(self):
        try:
            self._set_status("Reading selection...")
            text = self._get_selection_text(save_cursor=True)
            self._selection_text = text
            self._update_selection_display(text)

            if not text.strip():
                self._set_status("No text selected — highlight text first")
                self._set_preview("")
                return

            action = self._get_action()
            tone = self._get_tone()
            custom = self._get_custom_instructions()
            words = len(text.split())

            labels = {
                "rewrite": "Rewriting", "summarize": "Summarizing",
                "grammar": "Fixing grammar in", "translate": "Translating",
                "continue": "Continuing", "simplify": "Simplifying",
                "custom": "Processing",
            }
            self._set_status(f"{labels.get(action, 'Processing')} {words} words...")
            prompt = build_prompt(action, tone, text, custom)
            result = ollama_generate(prompt)
            self._last_action = action
            self._last_output = result
            self._set_preview(result)

            result_words = len(result.split())
            if action == "continue":
                self._set_status(
                    f"Done! {result_words} words generated. "
                    f"Apply will append after your text.")
            else:
                self._set_status(
                    f"Done! {result_words} words generated. Click Apply to use.")
        except Exception as e:
            err_msg = str(e)
            if "timed out" in err_msg.lower():
                self._set_status("Timed out — try shorter text or check Ollama")
            elif "failed to reach" in err_msg.lower():
                self._set_status("Cannot reach Ollama — is it running?")
            else:
                self._set_status(f"Error: {err_msg[:60]}")
            self._last_output = ""

    def _on_apply(self):
        try:
            # Read whatever is in the preview box (user may have edited it)
            apply_text = self._dialog.getControl("preview_box").getText()
            if not apply_text.strip():
                self._set_status("Nothing to apply — Generate first")
                return

            mode = self._get_output_mode()
            if mode == "comment":
                self._insert_comment(apply_text)
                self._set_status("Inserted as comment!")
            elif self._last_action == "continue":
                self._append_after_selection(apply_text)
                self._set_status("Text appended after selection!")
            else:
                self._replace_selection(apply_text)
                self._set_status("Selection replaced!")
            # Clear preview after applying
            self._set_preview("")
        except Exception as e:
            self._set_status(f"Error applying: {str(e)[:60]}")


# ---------- Main UNO component ----------

class AIAssistant(unohelper.Base, XJobExecutor):
    """Main UNO component for AI Assistant extension."""

    def __init__(self, ctx):
        self.ctx = ctx

    # -- text helpers (used by quick menu actions) --
    def _get_selection_text(self):
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)
        doc = desktop.getCurrentComponent()
        if not hasattr(doc, "Text"):
            return None
        selection = doc.CurrentController.getSelection()
        if selection and selection.getCount() > 0:
            return selection.getByIndex(0).getString()
        return None

    def _replace_selection(self, new_text):
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)
        doc = desktop.getCurrentComponent()
        if hasattr(doc, "Text"):
            selection = doc.CurrentController.getSelection()
            if selection and selection.getCount() > 0:
                selection.getByIndex(0).setString(new_text)

    def _insert_comment(self, comment_text):
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)
        doc = desktop.getCurrentComponent()
        if hasattr(doc, "Text"):
            selection = doc.CurrentController.getSelection()
            if selection and selection.getCount() > 0:
                text_range = selection.getByIndex(0)
                try:
                    annotation = doc.createInstance(
                        "com.sun.star.text.TextField.Annotation")
                    annotation.Content = comment_text
                    annotation.Author = "AI Assistant"
                    text_range.getText().insertTextContent(
                        text_range, annotation, False)
                except Exception:
                    cursor = text_range.getText().createTextCursorByRange(
                        text_range)
                    cursor.collapseToEnd()
                    cursor.getText().insertString(
                        cursor, f" ({comment_text})", False)

    def _show_choice_dialog(self, title, message, choices):
        """Show a modal dialog with multiple choice buttons."""
        WIDTH = 400
        HEIGHT = 150
        BUTTON_WIDTH = 120
        BUTTON_HEIGHT = 30
        MARGIN = 10

        ctx = uno.getComponentContext()
        sm = ctx.getServiceManager()

        dialog = sm.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialog", ctx)
        dialog_model = sm.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialogModel", ctx)
        dialog.setModel(dialog_model)
        dialog.setTitle(title)
        dialog.setPosSize(0, 0, WIDTH, HEIGHT, SIZE)

        label_model = dialog_model.createInstance(
            "com.sun.star.awt.UnoControlFixedTextModel")
        dialog_model.insertByName("label", label_model)
        label_model.Label = message
        label_control = dialog.getControl("label")
        label_control.setPosSize(MARGIN, MARGIN, WIDTH - 2 * MARGIN, 40, POSSIZE)

        result = [None]

        class ChoiceListener(unohelper.Base, XActionListener):
            def __init__(self, choice_value, dlg, res):
                self._choice = choice_value
                self._dialog = dlg
                self._result = res

            def actionPerformed(self, event):
                self._result[0] = self._choice
                self._dialog.endExecute()

            def disposing(self, event):
                pass

        y_pos = 60
        for i, choice in enumerate(choices):
            btn_name = f"btn_{i}"
            btn_model = dialog_model.createInstance(
                "com.sun.star.awt.UnoControlButtonModel")
            dialog_model.insertByName(btn_name, btn_model)
            btn_model.Label = choice
            btn_control = dialog.getControl(btn_name)
            x_pos = MARGIN + i * (BUTTON_WIDTH + MARGIN)
            btn_control.setPosSize(
                x_pos, y_pos, BUTTON_WIDTH, BUTTON_HEIGHT, POSSIZE)
            btn_control.addActionListener(
                ChoiceListener(choice, dialog, result))

        frame = sm.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx).getCurrentFrame()
        window = frame.getContainerWindow() if frame else None
        dialog.createPeer(
            sm.createInstanceWithContext(
                "com.sun.star.awt.Toolkit", ctx), window)

        if window:
            ps = window.getPosSize()
            dialog.setPosSize(
                ps.Width // 2 - WIDTH // 2,
                ps.Height // 2 - HEIGHT // 2, 0, 0, POS)

        dialog.execute()
        dialog.dispose()
        return result[0]

    def _show_error(self, message):
        try:
            toolkit = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.awt.Toolkit", self.ctx)
            parent = toolkit.getDesktopWindow()
            msgbox = toolkit.createMessageBox(
                parent,
                uno.Enum("com.sun.star.awt.MessageBoxType", "ERRORBOX"),
                MSG_BUTTONS.BUTTONS_OK,
                "AI Assistant Error",
                message,
            )
            msgbox.execute()
        except Exception:
            pass

    # -- entry point --
    def trigger(self, args):
        """Called by LibreOffice when a menu item is clicked."""
        try:
            if args == "rewrite":
                self._handle_rewrite()
            elif args == "summarize":
                self._handle_summarize()
            elif args == "dialog":
                self._open_dialog()
            else:
                self._show_error(f"Unknown action: {args}")
        except Exception as e:
            self._show_error(f"Error: {str(e)}")

    # -- quick menu actions --
    def _handle_rewrite(self):
        text = self._get_selection_text()
        if not text or not text.strip():
            self._show_error("Please select some text first")
            return
        tone = self._show_choice_dialog(
            "Rewrite Text", "Select tone for rewriting:",
            ["Formal", "Concise", "Academic"])
        if not tone:
            return
        try:
            prompt = build_prompt("rewrite", tone, text)
            result = ollama_generate(prompt)
            self._replace_selection(result)
        except Exception as e:
            self._show_error(str(e))

    def _handle_summarize(self):
        text = self._get_selection_text()
        if not text or not text.strip():
            self._show_error("Please select some text first")
            return
        mode = self._show_choice_dialog(
            "Summarize Text", "How should the summary be inserted?",
            ["Replace", "Comment"])
        if not mode:
            return
        try:
            prompt = build_prompt("summarize", "", text)
            result = ollama_generate(prompt)
            if mode == "Replace":
                self._replace_selection(result)
            else:
                self._insert_comment(result)
        except Exception as e:
            self._show_error(str(e))

    # -- dialog UI --
    def _open_dialog(self):
        """Open the modeless AI Assistant dialog."""
        self._open_uno_dialog()

    def _open_uno_dialog(self):
        """Fallback UNO-based dialog."""
        global _g_dialog, _g_handler, _g_close_listener, _g_action_listener

        if _g_dialog is not None:
            try:
                _g_dialog.setVisible(True)
                _g_dialog.toFront()
                if _g_handler:
                    _g_handler._on_refresh_selection()
                return
            except Exception:
                _g_dialog = None
                _g_handler = None

        ctx = uno.getComponentContext()
        sm = ctx.getServiceManager()

        # ---- build dialog model ----
        DLG_W = 250
        model = sm.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialogModel", ctx)
        model.Width = DLG_W
        model.Title = "AI Assistant"

        # -- helper functions --
        def add_groupbox(name, label, x, y, w, h):
            m = model.createInstance(
                "com.sun.star.awt.UnoControlGroupBoxModel")
            m.Name = name
            m.Label = label
            m.PositionX = x
            m.PositionY = y
            m.Width = w
            m.Height = h
            model.insertByName(name, m)

        def add_radio(name, label, x, y, w=70, h=12, selected=False):
            m = model.createInstance(
                "com.sun.star.awt.UnoControlRadioButtonModel")
            m.Name = name
            m.Label = label
            m.PositionX = x
            m.PositionY = y
            m.Width = w
            m.Height = h
            if selected:
                m.State = 1
            model.insertByName(name, m)

        def add_button(name, label, x, y, w=65, h=16):
            m = model.createInstance(
                "com.sun.star.awt.UnoControlButtonModel")
            m.Name = name
            m.Label = label
            m.PositionX = x
            m.PositionY = y
            m.Width = w
            m.Height = h
            model.insertByName(name, m)

        def add_label(name, label, x, y, w=210, h=10):
            m = model.createInstance(
                "com.sun.star.awt.UnoControlFixedTextModel")
            m.Name = name
            m.Label = label
            m.PositionX = x
            m.PositionY = y
            m.Width = w
            m.Height = h
            model.insertByName(name, m)

        def add_multiline(name, x, y, w=210, h=50, readonly=True):
            m = model.createInstance(
                "com.sun.star.awt.UnoControlEditModel")
            m.Name = name
            m.MultiLine = True
            m.ReadOnly = readonly
            m.VScroll = True
            m.PositionX = x
            m.PositionY = y
            m.Width = w
            m.Height = h
            model.insertByName(name, m)

        def add_separator(name, x, y, w):
            m = model.createInstance(
                "com.sun.star.awt.UnoControlFixedLineModel")
            m.Name = name
            m.PositionX = x
            m.PositionY = y
            m.Width = w
            m.Height = 1
            m.Orientation = 0  # horizontal
            model.insertByName(name, m)

        # ---- layout ----
        X = 8
        W = DLG_W - 16  # content width with margin
        Y = 4

        # == Section 1: Selected Text ==
        add_label("sel_title", "Selected Text:", X, Y, W, 10)
        Y += 12
        add_multiline("selection_box", X, Y, W, 36, readonly=True)
        Y += 38
        add_label("selection_info", "No text selected", X, Y, W - 65, 10)
        add_button("refresh_btn", "Refresh", X + W - 60, Y - 2, 60, 14)
        Y += 14

        add_separator("sep1", X, Y, W)
        Y += 4

        # == Section 2: Action ==
        add_groupbox("action_group", "Action", X, Y, W, 48)
        # Row 1
        r1y = Y + 12
        add_radio("action_rewrite", "Rewrite", X + 8, r1y, 55,
                  selected=True)
        add_radio("action_summarize", "Summarize", X + 65, r1y, 55)
        add_radio("action_grammar", "Grammar Fix", X + 125, r1y, 65)
        # Row 2
        r2y = Y + 24
        add_radio("action_translate", "Translate", X + 8, r2y, 55)
        add_radio("action_continue", "Continue", X + 65, r2y, 55)
        add_radio("action_simplify", "Simplify", X + 125, r2y, 55)
        # Row 3
        r3y = Y + 36
        add_radio("action_custom", "Custom Prompt", X + 8, r3y, 80)

        # GroupBox breaks radio group; Tone starts new group
        Y += 52
        add_groupbox("tone_group", "Tone", X, Y, W, 24)
        add_radio("tone_formal", "Formal", X + 8, Y + 12, 50,
                  selected=True)
        add_radio("tone_concise", "Concise", X + 65, Y + 12, 50)
        add_radio("tone_academic", "Academic", X + 125, Y + 12, 60)

        Y += 28
        add_groupbox("output_group", "Output", X, Y, W, 24)
        add_radio("output_replace", "Replace Selection",
                  X + 8, Y + 12, 90, selected=True)
        add_radio("output_comment", "Insert as Comment",
                  X + 110, Y + 12, 90)

        Y += 30
        # == Section: Custom Instructions ==
        add_label("custom_label",
                  "Additional instructions (optional):", X, Y, W, 10)
        Y += 12
        add_multiline("custom_box", X, Y, W, 30, readonly=False)
        Y += 34

        add_separator("sep2", X, Y, W)
        Y += 5

        # == Section 3: Buttons ==
        btn_w = (W - 10) // 3
        add_button("generate_btn", "Generate", X, Y, btn_w, 18)
        add_button("apply_btn", "Apply",
                   X + btn_w + 5, Y, btn_w, 18)
        add_button("close_btn", "Close",
                   X + 2 * (btn_w + 5), Y, btn_w, 18)

        Y += 24
        add_separator("sep3", X, Y, W)
        Y += 4

        # == Section 4: Result Preview (editable) ==
        add_label("preview_label",
                  "Result Preview (edit before applying):", X, Y, W, 10)
        Y += 12
        add_multiline("preview_box", X, Y, W, 120, readonly=False)

        Y += 124
        add_separator("sep4", X, Y, W)
        Y += 4

        # == Status bar ==
        add_label("status_label",
                  "Select text in document, then click Generate.",
                  X, Y, W, 12)
        Y += 16

        model.Height = Y

        # ---- create dialog control ----
        dialog = sm.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialog", ctx)
        dialog.setModel(model)

        # -- attach handlers --
        handler = _DialogHandler(dialog, self.ctx)
        dialog.getControl("generate_btn").addActionListener(handler)
        dialog.getControl("apply_btn").addActionListener(handler)
        dialog.getControl("close_btn").addActionListener(handler)
        dialog.getControl("refresh_btn").addActionListener(handler)

        # Action radio listener: update Tone and label on action change
        action_listener = _ActionRadioListener(dialog)
        for rname in ("action_rewrite", "action_summarize", "action_grammar",
                      "action_translate", "action_continue", "action_simplify",
                      "action_custom"):
            dialog.getControl(rname).addItemListener(action_listener)

        # -- show modeless --
        toolkit = sm.createInstanceWithContext(
            "com.sun.star.awt.Toolkit", ctx)
        desktop = sm.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx)
        frame = desktop.getCurrentFrame()
        parent_window = frame.getContainerWindow() if frame else None
        dialog.createPeer(toolkit, parent_window)

        # listen for X button
        close_listener = _CloseListener()
        dialog.addTopWindowListener(close_listener)

        dialog.setVisible(True)

        # auto-refresh selection on open
        handler._on_refresh_selection()

        # keep references alive
        _g_dialog = dialog
        _g_handler = handler
        _g_close_listener = close_listener
        _g_action_listener = action_listener


# ---------- UNO component registration ----------
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    AIAssistant,
    "org.libreoffice.aiassistant.do",
    ("com.sun.star.task.Job",),
)
