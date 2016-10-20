from setuptools import setup, find_packages
from setuptools.command.install import install
import subprocess

setup(
    name = "vcp",
    version = "2.4.2",
    description = "Version Control Projects - organize repositories",
    author = 'Lajos Santa',
    author_email = 'santa.lajos@coldline.hu',
    url = 'https://github.com/voidpp/vcp.git',
    license = 'MIT',
    install_requires = [
        "prettytable==0.7.2",
        "argcomplete==1.0.0",
        "voidpp-tools>=1.5.0",
        "PyYAML==3.11",
        "GitPython==2.0.3",
        "virtualenv-api==2.1.10",
    ],
    packages = find_packages(),
    scripts = [
        'bin/vcp',
        'vcp_tools.sh',
    ],
)
