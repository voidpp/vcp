from setuptools import setup, find_packages

setup(
    name = "vcp",
    version = "1.0",
    description = "Version Control Projects - organize repositories",
    author = 'Lajos Santa',
    author_email = 'santa.lajos@coldline.hu',
    install_requires = [
        "prettytable==0.7.2",
    ],
    packages = find_packages(),
    scripts = [
        'bin/vcp'
    ]
)
