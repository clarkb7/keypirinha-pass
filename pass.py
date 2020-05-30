import threading
import hashlib

import keypirinha as kp
import keypirinha_util as kpu

class Pass(kp.Plugin):
    """
    Provides an interface to a [password store](https://www.passwordstore.org/).
    """
    CAT_FILE = kp.ItemCategory.USER_BASE + 1
    CAT_FILE_LINE = kp.ItemCategory.USER_BASE + 2

    def __init__(self):
        super().__init__()

    def _read_config(self):
        settings = self.load_settings()

        backend = settings.get('backend', 'main', fallback='wsl')
        if backend == 'wsl':
            from .backends.wsl import WslBackend
            self.backend = WslBackend()
        else:
            raise ValueError("Unknown backend: {}".format(backend))

        pass_store = settings.get('path', 'pass',
            fallback=self.backend.password_store)
        self.backend.set_password_store(pass_store)

        self.log("Password store: {}".format(pass_store))
        self.CLIP_TIME = settings.get('clip_time', 'pass', fallback=45)
        self._clip_timer = None

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
                    short_desc=name,
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
            for l in lines:
                # Skip empty lines
                if not l:
                    continue
                items.append(self.create_item(
                    category=self.CAT_FILE_LINE,
                    label=l,
                    short_desc=l,
                    target=l,
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
            # If it is a 'Key: Value' format, put Value in clipboard
            # Otherwise, put full line in clipboard
            data = self._pass_kv_split(item.target())[1]
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
