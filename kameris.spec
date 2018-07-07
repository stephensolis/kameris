from kameris.utils.platform_utils import platform_name


a = Analysis(['kameris.py'],
             pathex=[os.getcwd()],
             binaries=[],
             datas=[
                ('kameris/scripts/make_plots.wls', 'kameris/scripts'),
                ('kameris/scripts/generation_cgr_' + platform_name() + '_*', 'kameris/scripts'),
                ('kameris/scripts/generation_dists_' + platform_name() + '_*', 'kameris/scripts')
             ],
             hiddenimports=[
                 'sklearn.neighbors.typedefs', 'sklearn.neighbors.quad_tree', 'sklearn.tree._utils',
                 'scipy._lib.messagestream',
                 'kameris.subcommands.run_job', 'kameris.subcommands.summarize'
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False)

pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='kameris-' + platform_name(),
          debug=False,
          strip=False,
          upx=False,
          runtime_tmpdir=None,
          console=True,
          icon='logo/logo.ico')
