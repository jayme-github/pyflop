from setuptools import setup, find_packages

setup(
    name="pyflop",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'pyflop=pyflop.pyflop:main',
        ],
    },
    install_requires=[],
    python_requires='>=3.9',
)
