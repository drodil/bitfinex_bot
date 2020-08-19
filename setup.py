from setuptools import setup, find_packages

setup(name='bitfinex-bot',
      version='0.1.0',
      packages=find_packages(),
      install_requires=[
          'requests',
          'numpy',
          'pandas',
          'talib',
          'google-cloud-logging'
      ],
      entry_points={
          'console_scripts': [
              'bitfinex-bot = bot.__main__:main'
          ]
      },
      )
