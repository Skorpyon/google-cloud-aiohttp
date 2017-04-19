from importlib.machinery import SourceFileLoader
from pathlib import Path
from setuptools import setup, find_packages

THIS_DIR = Path(__file__).resolve().parent
long_description = THIS_DIR.joinpath('README.rst').read_text()

# avoid loading the package before requirements are installed:
version = SourceFileLoader('version', 'aiogoogle/version.py').load_module()

package = THIS_DIR.joinpath('aiogoogle')

start_package_data = []


setup(
    name='aiogoogle',
    version=str(version.VERSION),
    description='Aiohttp API Client library for Google Cloud.',
    long_description=long_description,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Framework :: Aiohttp'
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Intended Audience :: Information Technology',
        'License :: Apache 2.0',
        'Operating System :: POSIX :: Linux'
    ],
    author='Anton Trishenkov',
    author_email='anton.trishenkov@gmail.com',
    url='https://github.com/Skorpyon/google-cloud-aiohttp',
    license='Apache 2.0',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    include_package_data=True,
    namespace_packages=[
        'aiogoogle',
        'aiogoogle.auth',
        'aiogoogle.oauth2',
        'aiogoogle.cloud',
    ],
    zip_safe=True,
    install_requires=[
        'google-cloud-core==0.24.1',
        'google-cloud-storage >= 1.0.0, < 2.0dev',
        'ujson==1.35',
        'aiohttp>=2.0.7'
    ],
)
