from setuptools import setup, find_packages
from modmap_toolkit import __version__
from modmap_toolkit.utils.platform_utils import platform_name


try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel

    class bdist_wheel(_bdist_wheel):
        def finalize_options(self):
            _bdist_wheel.finalize_options(self)
            self.root_is_pure = False

        def get_tag(self):
            if platform_name() == 'windows':
                platform_tag = 'win_amd64'
            elif platform_name() == 'mac':
                platform_tag = 'macosx_10_6_intel'
            elif platform_name() == 'linux':
                platform_tag = 'manylinux1_x86_64'
            return 'py2.py3', 'none', platform_tag
except ImportError:
    bdist_wheel = None


setup(
    name='modmap-toolkit',
    version=__version__,
    description=('Generation, analysis, and evaluation tools for Molecular '
                 'Distance Maps.'),
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
    url='https://github.com/stephensolis/modmap-toolkit/',
    license='MIT',
    packages=find_packages(),
    package_data={
        'modmap_toolkit': [
            'scripts/make_plots.wls',
            'scripts/generation_cgr_' + platform_name() + '_*',
            'scripts/generation_dists_' + platform_name() + '_*'
        ]
    },
    entry_points={
        'console_scripts': [
            'modmap-toolkit = modmap_toolkit.__main__:main'
        ]
    },
    install_requires=[
        'modmap-generator-formats',
        'numpy',
        'ruamel.yaml',
        'psutil',
        # it's necessary to freeze scikit-learn since models are neither
        # forward nor backward-compatible
        # modmap-toolkit classify will warn if the current scikit-learn
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
