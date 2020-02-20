from setuptools import setup

VERSION = "0.2.0"

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="pycircleci",
    version=VERSION,
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3 :: Only",
    ],
    keywords="circleci ci cd api",
    packages=["pycircleci"],
    install_requires=["requests"],
    python_requires=">=3",
    zip_safe=False,
)
