from setuptools import setup, find_packages

setup(
    name='forex_bot',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'typer',
        'pydantic',
        'PyYAML',
        'numpy',
    ],
    entry_points={
        'console_scripts': [
            'forex-bot=app.main:app'
        ]
    }
)
