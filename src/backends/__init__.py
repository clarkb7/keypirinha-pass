import glob
import os
import subprocess

class PassBackend():
    def __init__(self):
        self.password_store = self.get_default_password_store()

    # API
    def get_pass_contents(self, name):
        """Get decrypted contents of @name from the password store"""
        raise NotImplementedError()

    @classmethod
    def get_default_password_store(cls):
        """Return default path to password store"""
        return os.path.join(os.getenv('USERPROFILE'), '.password-store')

    def set_password_store(self, password_store):
        """Set path to use for password store"""
        password_store = os.path.expandvars(password_store)
        self.password_store = password_store

    def get_pass_list(self):
        """Get a list of passwords available in password_store.
        Formatted as would be passed to "pass show XXX/YYY".
        """
        paths = glob.glob(os.path.join(self.password_store, '**', '*.gpg'), recursive=True)
        names = [self._winpath_to_name(os.path.relpath(p, self.password_store)) for p in paths]
        return names

    def get_password(self, name):
        """Get the first line of @name from the password store"""
        return self.get_pass_contents(name).split('\n')[0]

    # Helpers
    @staticmethod
    def _winpath_to_name(path):
        return path.replace('\\','/')[:-len('.gpg')]
    @staticmethod
    def _name_to_winpath(path):
        return path.replace('/','\\')+'.gpg'

    @staticmethod
    def _subp_run(args, hide=True, collect_output=True, env=None):
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
