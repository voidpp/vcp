About
-
Organize repositories.

If you have to make something, and do this by modularly, you have to handle a lots of repositories. When you have 10+ repos it will be annoying. This is a lightweight command line tool to gather the repos to projects and do some things with these.

For more command use `vcp --help`

Limitations
-
* Currently works only with git repositories


Usage examples
-
```bash
# create a project
vcp project create webstuff1
# "create" repositories (you can use relative path too)
vcp repository create /path/to/js-package-one
# add this repo to the project
vcp project modify webstuff1 repository add js-package-one
# "create" repositories with project addition shortcut
vcp repository create /path/to/js-package-two --add-to webstuff1
# this will print the status of all the repos with the 'webstuff1' project
vcp status webstuff1

```

Install
-
`pip install vcp`

For bash completition activate argcomplete:
```
activate-global-python-argcomplete
```

If the global activation is not working or you just don't want to activate globally, completition could install locally by add this line the end of the ~/.bashrc file
```
eval "$(register-python-argcomplete vcp)"
```
