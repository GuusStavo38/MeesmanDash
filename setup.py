from setuptools import setup, find_packages

setup(
    name='MeesmanDash',
    version='0.0.2.dev3',
    description='Meesman dashboard from scraped data',
    author='Guus van Heijningen',
    author_email='gvheijningen@gmail.com',
    url='https://crunchanalytics.be',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    scripts=[
        'scripts/meesman_monthlyETL',
        'scripts/meesman_weeklyETL'
    ],
    install_requires=[
        'selenium',
        'chromedriver',
        'pandas',
        'dateparser',
        'sqlalchemy',
        'sqlalchemy-utils',
        'configparser',
        'argparse',
        'mysqlclient'
   ]
)
