import os
import platform
from setuptools import setup, find_packages

from kameris import __version__
from kameris.utils.platform_utils import platform_name


try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel

    class bdist_wheel(_bdist_wheel):
        def finalize_options(self):
            _bdist_wheel.finalize_options(self)
            self.root_is_pure = False

        def get_tag(self):
            if platform.system() == 'Windows':
                platform_tag = 'win_amd64'
            elif platform.system() == 'Linux':
                platform_tag = 'manylinux1_x86_64'
            elif platform.system() == 'Darwin':
                platform_tag = 'macosx_10_6_intel'
            return 'py2.py3', 'none', platform_tag
except ImportError:
    bdist_wheel = None

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    long_description = readme.read()


setup(
    name='kameris',
    version=__version__,
    description=('A fast, user-friendly analysis and evaluation pipeline '
                 'for some DNA sequence classification tasks.'),
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/stephensolis/kameris/',

    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Scientific/Engineering :: Bio-Informatics'
    ],

    author='Stephen',
    author_email='stephsolis@gmail.com',
    license='MIT',
    packages=find_packages(),
    package_data={
        'kameris': [
            'schemas/*',
            'scripts/make_plots.wls',
            'scripts/generation_cgr_' + platform_name() + '_*',
            'scripts/generation_dists_' + platform_name() + '_*'
        ]
    },
    entry_points={
        'console_scripts': [
            'kameris = kameris.__main__:main'
        ]
    },
    install_requires=[
        'appdirs',
        'backports.tempfile',
        'jsonschema',
        'kameris-formats',
        'numpy',
        'requests',
        'ruamel.yaml',
        'psutil',
        # it's necessary to freeze scikit-learn since models are neither
        # forward nor backward-compatible
        # kameris classify will warn if the current scikit-learn
        # version doesn't match the version at train time
        'scikit-learn==0.19.1',
        'scipy',
        'six',
        'stopit',
        'tabulate',
        'tqdm',
        'watchtower',
        'x86cpu'
    ],
    cmdclass={
        'bdist_wheel': bdist_wheel
    }
)
