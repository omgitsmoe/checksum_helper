import setuptools

with open("README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()


setuptools.setup(
    name="ChecksumHelper",
    version="0.1",
    description="Helper tool for checksum file operations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    author="nilfoer",
    author_email="",
    license="MIT",
    keywords="script checksum verify sha512 md5 sha256",
    packages=setuptools.find_packages(exclude=['tests*']),
    python_requires='>=3.6',
    install_requires=[],
    tests_require=['pytest'],
    # non-python data that should be included in the pkg
    # mapping from package name to a list of relative path names that should be copied into the package
    package_data={},
    entry_points={
        'console_scripts': [
            # linking the executable 4cdl here to running the python function main in the fourcdl module
            'checksum_helper=checksum_helper:main',
        ]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)