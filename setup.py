from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='ERS_NRB',
    version='0.1.5',
    description="Prototype processor for the ERS Normalized Radar Backscatter (ERS NRB) product",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/SAR-ARD/ERS_NRB",
    author="John Truckenbrodt, Marco Wolsza, Ricardo Noguera",
    author_email="ricardo.noguera@telespazio.com",
    packages=find_packages(where='.'),
    include_package_data=True,
    install_requires=['gdal>=3.4.1',
                      'click',
                      'lxml',
                      'pystac',
                      'pyroSAR',
                      'scipy'],
    python_requires='>=3.6',
    zip_safe=False,
    entry_points={
        'console_scripts': ['ers_nrb=ERS_NRB.cli:cli']
    }
)
