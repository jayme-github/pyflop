from setuptools import setup, find_packages

setup(
    name="pyflop",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'pyflop=pyflop.pyflop:main',
        ],
    },
    install_requires=[],
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    python_requires='>=3.9',
)
