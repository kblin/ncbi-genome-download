import os
import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand

import ncbi_genome_download


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def read_requires(fname):
    with open(fname, 'r') as fh:
        requires = [l.strip() for l in fh.readlines()]

    return requires

tests_require_path = os.path.join('tests', 'requirements.txt')

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errcode = pytest.main(self.test_args)
        sys.exit(errcode)


setup(
    name='ncbi-genome-download',
    version=ncbi_genome_download.__version__,
    author='Kai Blin',
    author_email='kblin@biosustain.dtu.dk',
    description='Download genome files from the NCBI FTP server.',
    long_description=read('README.md'),
    install_requires=read_requires('requirements.txt'),
    tests_require=read_requires(tests_require_path),
    cmdclass={'test': PyTest},
    entry_points={
        'console_scripts': [
            'ncbi-genome-download=ncbi_genome_download.__main__:main'
        ],
    },
    packages=['ncbi_genome_download'],
    url='https://github.com/kblin/ncbi-genome-download/',
    license='Apache Software License',
    classifiers=[
        'Programming Language :: Python',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
    ],
    extras_require={
        'testing': read_requires(tests_require_path),
    },
)
