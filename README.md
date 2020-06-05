# Keypirinha Plugin: pass

This is a plugin for the [Keypirinha](http://keypirinha.com) launcher that provides an interface to a [password store](https://www.passwordstore.org/). I wanted [passmenu](https://git.zx2c4.com/password-store/tree/contrib/dmenu) for Windows.

## Usage
To display a list of your password files, activate keypirinha (default `Ctrl+Win+K`), type `Password Store` until the item comes up then press `tab`.

To temporarily copy the password to your clipboard, select a password file in the list and activate it (press `enter`).

To display each line in a password file, select it in the list and press `tab`. By default, pass will censor the first line (the password) of a file. Subsequent lines that follow the recommended `KEY: VALUE` syntax will display only the `KEY` part. If a line does not contain a `KEY: VALUE` pair, the full line will be censored. If you activate (press `enter`) a `KEY` line, only the `VALUE` part will be temporarily copied to your clipboard (even though it is not shown in keypirinha).

## Configuration

**IMPORTANT:** The following options affect the security of your data and you should be aware of them and their default values.

* `safe_keys` - Each `KEY` in this list will always have its `VALUE` part shown in keypirinha. Default: `["URL", "Username"]`
* `show_secrets` - Always show the full uncensored line in keypirinha. Default: `False`
* `clip_time` - Number of seconds to wait before restoring the clipboard. Default: `45`
* `save_history` - Save selected password file names to keypirinha history. Default: `True`

See the [configuration file](pass.ini) for other options and their descriptions.

## Backends

### Gpg4win
Depends
* [Gpg4win installed](https://www.gpg4win.org/)
* `gpg.exe` on Windows PATH

### WSL
Depends
* [WSL installed](https://docs.microsoft.com/en-us/windows/wsl/install-win10)
* `bash.exe` on Windows PATH
* `pass` installed in WSL
* `pass` and `wslpath` on WSL path

**NOTE: Currently in experimental development.**
