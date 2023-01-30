import os

from setuptools import find_packages, setup


def version():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")
    with open(path) as f:
        ver = f.read().strip()
    return ver


with open("README.md", "r") as f:
    long_description = f.read()


setup(
    name="pycircleci",
    version=version(),
    description="Python client for CircleCI API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alpinweis/pycircleci",
    author="Adrian Kazaku",
    author_email="alpinweis@gmail.com",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
    ],
    keywords="circleci ci cd api",
    packages=find_packages(),
    install_requires=["requests", "requests-toolbelt"],
    python_requires=">=3",
    zip_safe=False,
)
