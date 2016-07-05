About
-
Organize repositories.

If you have to make something, and do this by modularly, you have to handle a lots of repositories. When you have 10+ repos it will be annoying. This is a command line tool to manage projects projects, and do things with it.

For more command use `vcp --help`

Limitations
-
* Currently works only with git repositories

Install
-
`pip install vcp`

For bash completition activate argcomplete:
```bash
activate-global-python-argcomplete
```

If the global activation is not working or you just don't want to activate globally, completition could install locally by add this line the end of the ~/.bashrc file
```bash
eval "$(register-python-argcomplete vcp)"
```

To use `vj` command you must add this line the end of the ~/.bashrc file
```bash
source /usr/local/bin/vcp_tools.sh
```
