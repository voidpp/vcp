from setuptools import setup, find_packages
from setuptools.command.install import install
import subprocess

setup(
    name = "vcp",
    version = "1.4.3",
    description = "Version Control Projects - organize repositories",
    author = 'Lajos Santa',
    author_email = 'santa.lajos@coldline.hu',
    url = 'https://github.com/voidpp/vcp.git',
    license = 'MIT',
    install_requires = [
        "prettytable==0.7.2",
        "argcomplete==1.0.0",
        "voidpp-tools>=1.3.0"
    ],
    packages = find_packages(),
    scripts = [
        'bin/vcp',
    ],
)
