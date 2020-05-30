class PassBackend():
    def __init__(self):
        self.password_store = self.get_default_password_store()

    # API
    @classmethod
    def get_default_password_store(cls):
        """Return default path to password store"""
        raise NotImplementedError()
    def set_password_store(self, password_store):
        """Set path to use for password store"""
        self.password_store = password_store
    def get_pass_list(self):
        """Get a list of passwords available in password_store.
        Formatted as would be passed to "pass show XXX/YYY".
        """
        raise NotImplementedError()
    def get_pass_contents(self, name):
        """Get decrypted contents of @name from the password store"""
        raise NotImplementedError()
    def get_password(self, name):
        """Get the first line of @name from the password store"""
        return self.get_pass_contents(name).split('\n')[0]
