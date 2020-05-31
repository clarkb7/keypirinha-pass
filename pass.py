import os
import threading
import hashlib
import ast

import keypirinha as kp
import keypirinha_util as kpu

class Pass(kp.Plugin):
    """
    Provides an interface to a [password store](https://www.passwordstore.org/).
    """
    CAT_FILE = kp.ItemCategory.USER_BASE + 1
    CAT_FILE_LINE = kp.ItemCategory.USER_BASE + 2
    CAT_FILE_LINE_INDEX = kp.ItemCategory.USER_BASE + 3

    DEFAULT_CLIP_TIME = 45
    DEFAULT_SHOW_SECRETS = False
    DEFAULT_SAFE_KEYS = ["URL", "Username"]

    def __init__(self):
        super().__init__()

    def _read_config(self):
        settings = self.load_settings()

        backend = settings.get('backend', 'main', fallback='wsl')
        if backend == 'wsl':
            from .backends.wsl import WslBackend
            self.backend = WslBackend()
        elif backend == 'gpg4win':
            from .backends.gpg4win import Gpg4WinBackend
            self.backend = Gpg4WinBackend()
        else:
            raise ValueError("Unknown backend: {}".format(backend))

        pass_store = settings.get('path', 'pass',
            fallback=self.backend.password_store)
        self.backend.set_password_store(pass_store)

        self.log("Password store: {}".format(pass_store))
        self.CLIP_TIME = settings.get('clip_time', 'pass',
            fallback=self.DEFAULT_CLIP_TIME)
        self._clip_timer = None

        self.SHOW_SECRETS = settings.get_bool('show_secrets', 'main',
            fallback=self.DEFAULT_SHOW_SECRETS)

        safe_keys = settings.get('safe_keys', 'main',
            fallback=None)
        if safe_keys is None:
            safe_keys = self.DEFAULT_SAFE_KEYS
        else:
            safe_keys = ast.literal_eval(safe_keys)
        self.SAFE_KEYS = [x.lower() for x in safe_keys]

    def on_start(self):
        self._read_config()

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self._read_config()

    def on_catalog(self):
        # Refresh list of names in password-store
        self.names = self.backend.get_pass_list()
        self.log("Found {} files in password store".format(len(self.names)))

        # Add pass command to catalog
        catalog = []
        catalog.append(
            self.create_item(
                category=kp.ItemCategory.KEYWORD,
                label="Pass",
                short_desc="Password Store",
                target="pass",
                args_hint=kp.ItemArgsHint.ACCEPTED,
                hit_hint=kp.ItemHitHint.IGNORE
            )
        )
        self.set_catalog(catalog)

    def on_suggest(self, user_input, items_chain):
        if not items_chain:
            return

        items = []
        if items_chain[-1].target() == 'pass':
            # Display list of pass files
            for name in self.names:
                items.append(self.create_item(
                    category=self.CAT_FILE,
                    label=name,
                    short_desc="",
                    target=name,
                    args_hint=kp.ItemArgsHint.ACCEPTED,
                    hit_hint=kp.ItemHitHint.IGNORE,
                    loop_on_suggest=True # tab will show contents of file
                ))
            self.set_suggestions(items, kp.Match.FUZZY, kp.Sort.SCORE_DESC)
        else:
            # User pressed tab on a pass file, show its contents
            pass_name = items_chain[-1].target()
            # Display pass file contents
            lines = self.backend.get_pass_contents(pass_name).split('\n')
            for i,l in enumerate(lines):
                # Skip empty lines
                if not l:
                    continue
                # Show full line if SHOW_SECRETS or a safe key
                k = None
                if i > 0:
                    # Don't kv split the first line
                    k,_ = self._pass_kv_split(l)
                if self.SHOW_SECRETS or (k is not None and k.lower() in self.SAFE_KEYS):
                    shown = l
                    cat = self.CAT_FILE_LINE
                    # Store index of line so we can decide whether or not to kv split it
                    target = str((l,i))
                else:
                    # Otherwise, display only KEY if it exists, otherwise asterisks
                    shown = '*'*8 if k is None else k
                    cat = self.CAT_FILE_LINE_INDEX
                    # Store index of line so we can get the full value later
                    # index also helps us decide whether or not to kv split the line
                    # This helps us keep secrets out of the log, too, if a user
                    # uses the "show item properties" shortcut
                    target = str((pass_name,i))
                items.append(self.create_item(
                    category=cat,
                    label=shown,
                    short_desc="",
                    target=target,
                    args_hint=kp.ItemArgsHint.FORBIDDEN,
                    hit_hint=kp.ItemHitHint.IGNORE
                ))
            self.set_suggestions(items, kp.Match.FUZZY, kp.Sort.NONE)

    def on_execute(self, item, action):
        data = None
        if item.category() == self.CAT_FILE:
            # User selected file, put password in clipboard
            data = self.backend.get_password(item.target())
        elif item.category() == self.CAT_FILE_LINE:
            # User selected a line from the pass file
            tuple_val = ast.literal_eval(item.target())
            data,lineno = tuple_val
        elif item.category() == self.CAT_FILE_LINE_INDEX:
            # User selected a line from the pass file
            tuple_val = ast.literal_eval(item.target())
            pass_name,lineno = tuple_val
            data = self.backend.get_pass_contents(pass_name).split('\n')[int(lineno)]

        if item.category() in [self.CAT_FILE_LINE, self.CAT_FILE_LINE_INDEX]:
            # Don't kv split the first line
            if lineno > 0:
                # If it is a 'Key: Value' format, put Value in clipboard
                # Otherwise, put full line in clipboard
                data = self._pass_kv_split(data)[1]

        if data is not None:
            self._put_data_in_clipboard(data)

    def _put_data_in_clipboard(self, data):
        # XXX: This only works with text clipboard data, not fancy Windows objects (files, office content, etc)
        orig_clip = kpu.get_clipboard()
        pass_hash = hashlib.md5(data.encode()).digest()

        # keypirinha.delay isn't implemented yet, so a timer will do
        kwargs = {'orig_clip': orig_clip, 'pass_hash': pass_hash}
        self._clip_timer = threading.Timer(self.CLIP_TIME, self._timer_reset_clipboard, kwargs=kwargs)

        kpu.set_clipboard(data)
        self._clip_timer.start()

    @staticmethod
    def _timer_reset_clipboard(orig_clip=None, pass_hash=None):
        if orig_clip is None or pass_hash is None:
            return
        # Only reset clip if clipboard still contains pass
        cur_clip = kpu.get_clipboard()
        clip_hash = hashlib.md5(cur_clip.encode()).digest()
        if clip_hash == pass_hash:
            kpu.set_clipboard(orig_clip)

    @staticmethod
    def _pass_kv_split(line):
        """Splits key value pair from a pass file, returns a tuple.
        Always returns a value, returns None for key if it does not exist.
        Example:
            >>> _pass_kv_split("URL: *.example.com/*")
            ("URL", "*.example.com/*")
        """
        if ': ' in line:
            return line.split(': ', 1)
        return None,line
