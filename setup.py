# -*- coding: utf-8 -*-

import setuptools

import weread_exporter

with open("README.md", "rb") as fp:
    README = fp.read().decode()


with open("requirements.txt") as fp:
    text = fp.read()
    REQUIREMENTS = text.split("\n")


def find_packages():
    packages = []
    for pkg in setuptools.find_packages():
        if not pkg.startswith("test"):
            print(pkg)
            packages.append(pkg)
    return packages


setuptools.setup(
    author="drunkdream",
    author_email="drunkdream@qq.com",
    name="weread-exporter",
    license="MIT",
    description="Securely export accessible WeRead books to EPUB, TXT, or Markdown.",
    version=weread_exporter.VERSION,
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/vibecodingengine/weread-exporter-skill",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=REQUIREMENTS,
    extras_require={},
    classifiers=[
        # Trove classifiers
        # (https://pypi.python.org/pypi?%3Aaction=list_classifiers)
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Intended Audience :: Developers",
    ],
    entry_points={
        "console_scripts": [
            "weread-exporter = weread_exporter.__main__:main",
        ],
    },
)
