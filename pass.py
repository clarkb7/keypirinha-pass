from datetime import datetime
import os
import subprocess
import glob
import shlex
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
        self.PASS_STORE = settings.get('path', 'pass',
            fallback=os.path.join(self._get_wsl_home(), '.password-store'))
        self.log("Password store: {}".format(self.PASS_STORE))
        self.CLIP_TIME = settings.get('clip_time', 'pass', fallback=45)
        self._clip_timer = None

    def on_start(self):
        self._read_config()

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self._read_config()

    def on_catalog(self):
        # Refresh list of paths in password-store
        paths = list(glob.glob(os.path.join(self.PASS_STORE, '**', '*.gpg'), recursive=True))
        self.paths = [os.path.relpath(p, self.PASS_STORE) for p in paths]
        self.log("Found {} files in password store".format(len(self.paths)))

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
            for p in self.paths:
                name = self._winpath_to_name(p)
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
            lines = self._get_pass_contents(pass_name)
            for l in lines:
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
            data = self._get_password(item.target())
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

    def _winpath_to_name(self, path):
        return path.replace('\\','/')[:-len('.gpg')]

    def _get_password(self, name):
        return self._get_pass_contents(name)[0]

    def _get_pass_contents(self, name):
        args = ['bash', '-c', 'pass show {}'.format(shlex.quote(name))]
        cp = self._subp_run(args)
        if not cp.stdout:
            # Might need to enter passphrase, so open a new console to let gpg request it
            # XXX: This could all be done in one call if I could get subprocess to leave stdin a tty and use PIPE for stdout
            cp = self._subp_run(args, hide=False, collect_output=False)
            cp = self._subp_run(args)
        lines = cp.stdout
        return [l for l in lines.split('\n') if l]

    def _pass_kv_split(self, line):
        if ': ' in line:
            return line.split(': ', 1)
        return None,line

    @staticmethod
    def _get_wsl_home():
        cp = Pass._subp_run(['bash', '-c', 'wslpath -w "$HOME"'])
        if cp.stdout:
            return cp.stdout.strip()
        return None

    @staticmethod
    def _subp_run(args, hide=True, collect_output=True):
        # Hide the console window
        startupinfo = None
        creationflags = 0
        if hide:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        else:
            creationflags = creationflags=subprocess.CREATE_NEW_CONSOLE
        stdout = None
        if collect_output:
            stdout = subprocess.PIPE
        cp = subprocess.run(args, encoding='utf-8',
            startupinfo=startupinfo, stdout=stdout, creationflags=creationflags)
        return cp
