""" Setup file """
import os
from setuptools import setup

HERE = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(HERE, 'README.rst')).read()


def get_version():
    with open("context.py") as f:
        for line in f:
            if line.startswith("__version__"):
                return eval(line.split("=")[-1])

REQUIREMENTS = []

TEST_REQUIREMENTS = [
    'coverage',
    'flake8',
    'pytest',
    'tox',
]

if __name__ == "__main__":
    setup(
        name='texas',
        version=get_version(),
        description="nested dictionaries with paths",
        long_description=README,
        classifiers=[
            'Development Status :: 2 - Pre-Alpha',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Topic :: Software Development :: Libraries'
        ],
        author='Joe Cross',
        author_email='joe.mcross@gmail.com',
        url='https://github.com/numberoverzero/texas',
        license='MIT',
        keywords='dict nested context',
        platforms='any',
        include_package_data=True,
        py_modules=["context"],
        install_requires=REQUIREMENTS,
        tests_require=REQUIREMENTS + TEST_REQUIREMENTS,
    )
