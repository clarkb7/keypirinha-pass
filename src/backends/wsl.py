import os
import shlex

from . import PassBackend

class WslBackend(PassBackend):
    ENV_PASS_STORE_DIR = 'PASSWORD_STORE_DIR'
    # API
    @classmethod
    def get_default_password_store(cls):
        args = ['bash', '-c', 'echo ${}'.format(cls.ENV_PASS_STORE_DIR)]
        cp = super()._subp_run(args)
        passdir = cp.stdout.strip()
        if not passdir:
            return os.path.join(cls._get_wsl_home(), '.password-store')
        return cls._wslpath_win(passdir)

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

    def set_password_store(self, password_store):
        """Set path to use for password store"""
        super().set_password_store(password_store)
        if os.path.exists(self.password_store):
            # Must be a windows path
            self._wsl_password_store = self._wslpath_wsl(self.password_store)
        else:
            # Must be a wslpath
            self._wsl_password_store = self._wsl_expandvars(self.password_store)
            winpath = self._wslpath_win(self._wsl_password_store)
            super().set_password_store(winpath)

    # Helpers
    @classmethod
    def _wslpath(cls, path, style):
        cp = super()._subp_run(['bash', '-c', 'wslpath {} "{}"'.format(style, path)])
        if cp.stdout:
            return cp.stdout.strip()
        return None
    @classmethod
    def _wslpath_wsl(cls, path, **kwargs):
        return cls._wslpath(path.replace('\\','\\\\'), '-u', **kwargs)
    @classmethod
    def _wslpath_win(cls, path, **kwargs):
        return cls._wslpath(path, '-w', **kwargs)

    @classmethod
    def _get_wsl_home(cls):
        """Returns $HOME as a windows path"""
        return cls._wslpath_win("$HOME")

    @classmethod
    def _wsl_expandvars(cls, path):
        """Returns path with vars expanded in wsl"""
        args = ['bash', '-c', 'echo "{}"'.format(path)]
        cp = super()._subp_run(args)
        return cp.stdout.strip()

    def _subp_run(self, args, hide=True, collect_output=True):
        if self._wsl_password_store:
            env = os.environ.copy()
            env[self.ENV_PASS_STORE_DIR] = self._wsl_password_store
            # Ensure windows copies our env var into WSLs env
            wslenv = '{}/u'.format(self.ENV_PASS_STORE_DIR)
            if 'WSLENV' in env:
                env['WSLENV'] += ':'+wslenv
            else:
                env['WSLENV'] = wslenv
        else:
            env = None
        return super()._subp_run(args, hide=hide, collect_output=collect_output, env=env)

