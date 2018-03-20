from modmap_toolkit.utils.platform_utils import platform_name
import platform


a = Analysis(['modmap-toolkit.py'],
             pathex=[os.getcwd()],
             binaries=[],
             datas=[],
             hiddenimports=[
                 'sklearn.neighbors.typedefs', 'sklearn.neighbors.quad_tree', 'sklearn.tree._utils',
                 'scipy._lib.messagestream',
                 'modmap_toolkit.subcommands.run_job', 'modmap_toolkit.subcommands.summarize'
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
          name='modmap-toolkit-' + platform_name(),
          debug=False,
          strip=False,
          upx=False,
          runtime_tmpdir=None,
          console=True,
          icon='logo/logo.ico')
