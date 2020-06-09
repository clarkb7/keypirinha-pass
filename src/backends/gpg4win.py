import os

from . import PassBackend

class Gpg4WinBackend(PassBackend):
    # API
    def get_pass_contents(self, name):
        pass_path = os.path.join(self.password_store, self._name_to_winpath(name))
        args = ['gpg.exe', '--decrypt', pass_path]
        cp = self._subp_run(args)
        return cp.stdout

