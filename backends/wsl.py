import os
import subprocess
import glob
import shlex

from . import PassBackend

class WslBackend(PassBackend):
    ENV_PASS_STORE_DIR = 'PASSWORD_STORE_DIR'
    # API
    @classmethod
    def get_default_password_store(cls):
        args = ['bash', '-c', 'echo ${}'.format(cls.ENV_PASS_STORE_DIR)]
        cp = cls.__subp_run(args)
        passdir = cp.stdout.strip()
        if not passdir:
            return os.path.join(cls._get_wsl_home(), '.password-store')
        return passdir

    def get_pass_list(self):
        paths = glob.glob(os.path.join(self.password_store, '**', '*.gpg'), recursive=True)
        names = [self._winpath_to_name(os.path.relpath(p, self.password_store)) for p in paths]
        return names

    def get_pass_contents(self, name):
        args = ['bash', '-c', 'pass show {}'.format(shlex.quote(name))]
        cp = self._subp_run(args)
        if not cp.stdout:
            # Might need to enter passphrase, so open a new console to let gpg request it
            # XXX: This could all be done in one call if I could get subprocess to leave stdin a tty and use PIPE for stdout
            cp = self._subp_run(args, hide=False, collect_output=False)
            cp = self._subp_run(args)
        lines = cp.stdout
        return lines

    # Helpers
    @staticmethod
    def _winpath_to_name(path):
        return path.replace('\\','/')[:-len('.gpg')]

    @staticmethod
    def _get_wsl_home():
        """Returns $HOME as a windows path"""
        cp = WslBackend.__subp_run(['bash', '-c', 'wslpath -w "$HOME"'])
        if cp.stdout:
            return cp.stdout.strip()
        return None

    def _subp_run(self, args, hide=True, collect_output=True):
        return self.__subp_run(args, hide=hide, collect_output=collect_output,
            env={self.ENV_PASS_STORE_DIR:self.password_store})

    @staticmethod
    def __subp_run(args, hide=True, collect_output=True, env=None):
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
        # XXX: keypirinha is at python3.6, the capture_output kwarg wasn't added until 3.7
        cp = subprocess.run(args, encoding='utf-8',
            env=env,
            startupinfo=startupinfo, stdout=stdout, creationflags=creationflags)
        return cp
