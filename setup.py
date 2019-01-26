import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="txbillsearch",
    version="0.1.6",
    author="Ed Vinyard",
    author_email="ed.vinyard@gmail.com",
    description="Scrape Texas Legislature Online Bill Search results.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/EdVinyard/TxBillSearch",
    packages=setuptools.find_packages(),
    install_requires=[
        # KLUDGE: Keep this in sync with Pipfile manually for now!
        # See https://github.com/pypa/pipenv/issues/1263#issuecomment-362600555
        # for an alternate approach.
        'requests',
        'bs4',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
