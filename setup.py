from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

g = {}
with open("pdbattach/__init__.py") as f:
    exec(f.read(), g, g)

setup(
    name="pdbattach",
    packages=find_packages(),
    include_package_data=True,
    version=g["__version__"],
    license="MIT",
    description="pdb attach a Python process",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="gray",
    author_email="greyschwinger@gmail.com",
    url="https://github.com/jschwinger233/pdbattach",
    platform=("linux"),
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=[
        "syscall@https://github.com/jschwinger233/py-linux-syscall/zipball/main#egg=syscall==0.0.2",
        "click>=8.0.0,<9.0.0",
    ],
    entry_points={
        "console_scripts": [
            "pdbattach = pdbattach.main:main",
        ],
    },
)
