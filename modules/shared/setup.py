from setuptools import setup, find_packages

setup(
    name='shared',
    version='0.1.0',
    description='Shared utilities for wis2downloader modules',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'redis>=4.0.0',
        'shapely>=2.0.0',
    ],
    python_requires='>=3.10',
)
