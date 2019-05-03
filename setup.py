from setuptools import setup, find_packages

setup(
    name = "vcp",
    description = "Version Control Projects - organize repositories",
    author = 'Lajos Santa',
    author_email = 'santa.lajos@gmail.com',
    url = 'https://github.com/voidpp/vcp.git',
    license = 'MIT',
    setup_requires = ["setuptools_scm"],
    include_package_data = True,
    use_scm_version = True,
    install_requires = [
        "prettytable~=0.7",
        "argcomplete~=1.0",
        "voidpp-tools~=1.5",
        "PyYAML~=3.11",
        "GitPython~=2.0",
        "virtualenv-api~=2.1",
    ],
    packages = find_packages(),
    scripts = [
        'bin/vcp',
        'vcp_tools.sh',
    ],
)
