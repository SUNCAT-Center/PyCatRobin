from setuptools import setup, find_packages

setup(
    name='pycatrobin',
    version='0.1.0',
    author='Dongjae Shin',
    packages=find_packages(),
    install_requires=[
        'pandas==2.2.3',
        'openpyxl==3.1.5',
        'mplcursors==0.6',
        'seaborn==0.13.2',
        'statsmodels==0.14.4',
        'numpy==1.26.4',
        'matplotlib==3.9.2',
        'ipython==8.25.0',
        'scikit-fda==0.10.1',
        'pyside6==6.10.0',
        'scipy==1.13.1'
    ]
)
