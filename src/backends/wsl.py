import os
import shlex

from . import PassBackend

class WslBackend(PassBackend):
    ENV_PASS_STORE_DIR = 'PASSWORD_STORE_DIR'
    # API
    @classmethod
    def get_default_password_store(cls):
        args = ['bash', '-c', 'echo ${}'.format(cls.ENV_PASS_STORE_DIR)]
        cp = PassBackend._subp_run(args)
        passdir = cp.stdout.strip()
        if not passdir:
            return os.path.join(cls._get_wsl_home(), '.password-store')
        return passdir

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
    def _get_wsl_home():
        """Returns $HOME as a windows path"""
        cp = PassBackend._subp_run(['bash', '-c', 'wslpath -w "$HOME"'])
        if cp.stdout:
            return cp.stdout.strip()
        return None

    def _subp_run(self, args, hide=True, collect_output=True):
        return super()._subp_run(args, hide=hide, collect_output=collect_output,
            env={self.ENV_PASS_STORE_DIR:self.password_store})

