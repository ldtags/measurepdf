# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['cli.py'],
    pathex=[],
    binaries=[],
    datas=[('src\\assets\\images\\etrm.ico', 'src\\assets\\images'), ('src\\assets\\images\\folder.png', 'src\\assets\\images'), ('src\\assets\\images\\plus.png', 'src\\assets\\images'), ('src\\assets\\images\\reset.png', 'src\\assets\\images'), ('src\\assets\\images\\search.png', 'src\\assets\\images'), ('src\\assets\\fonts\\arial\\Arial-Bold.ttf', 'src\\assets\\fonts\\arial'), ('src\\assets\\fonts\\arial\\Arial-BoldItalic.ttf', 'src\\assets\\fonts\\arial'), ('src\\assets\\fonts\\arial\\Arial-Italic.ttf', 'src\\assets\\fonts\\arial'), ('src\\assets\\fonts\\arial\\Arial-Regular.ttf', 'src\\assets\\fonts\\arial'), ('src\\assets\\fonts\\helvetica\\Helvetica-Bold.ttf', 'src\\assets\\fonts\\helvetica'), ('src\\assets\\fonts\\helvetica\\Helvetica-BoldItalic.ttf', 'src\\assets\\fonts\\helvetica'), ('src\\assets\\fonts\\helvetica\\Helvetica-Italic.ttf', 'src\\assets\\fonts\\helvetica'), ('src\\assets\\fonts\\helvetica\\Helvetica-Regular.ttf', 'src\\assets\\fonts\\helvetica'), ('src\\assets\\fonts\\merriweather\\Merriweather-Black.ttf', 'src\\assets\\fonts\\merriweather'), ('src\\assets\\fonts\\merriweather\\Merriweather-BlackItalic.ttf', 'src\\assets\\fonts\\merriweather'), ('src\\assets\\fonts\\merriweather\\Merriweather-Bold.ttf', 'src\\assets\\fonts\\merriweather'), ('src\\assets\\fonts\\merriweather\\Merriweather-BoldItalic.ttf', 'src\\assets\\fonts\\merriweather'), ('src\\assets\\fonts\\merriweather\\Merriweather-Italic.ttf', 'src\\assets\\fonts\\merriweather'), ('src\\assets\\fonts\\merriweather\\Merriweather-Light.ttf', 'src\\assets\\fonts\\merriweather'), ('src\\assets\\fonts\\merriweather\\Merriweather-LightItalic.ttf', 'src\\assets\\fonts\\merriweather'), ('src\\assets\\fonts\\merriweather\\Merriweather-Regular.ttf', 'src\\assets\\fonts\\merriweather'), ('src\\assets\\fonts\\source-sans-pro\\SourceSansPro-Black.ttf', 'src\\assets\\fonts\\source-sans-pro'), ('src\\assets\\fonts\\source-sans-pro\\SourceSansPro-BlackItalic.ttf', 'src\\assets\\fonts\\source-sans-pro'), ('src\\assets\\fonts\\source-sans-pro\\SourceSansPro-Bold.ttf', 'src\\assets\\fonts\\source-sans-pro'), ('src\\assets\\fonts\\source-sans-pro\\SourceSansPro-BoldItalic.ttf', 'src\\assets\\fonts\\source-sans-pro'), ('src\\assets\\fonts\\source-sans-pro\\SourceSansPro-ExtraLight.ttf', 'src\\assets\\fonts\\source-sans-pro'), ('src\\assets\\fonts\\source-sans-pro\\SourceSansPro-ExtraLightItalic.ttf', 'src\\assets\\fonts\\source-sans-pro'), ('src\\assets\\fonts\\source-sans-pro\\SourceSansPro-Italic.ttf', 'src\\assets\\fonts\\source-sans-pro'), ('src\\assets\\fonts\\source-sans-pro\\SourceSansPro-Light.ttf', 'src\\assets\\fonts\\source-sans-pro'), ('src\\assets\\fonts\\source-sans-pro\\SourceSansPro-LightItalic.ttf', 'src\\assets\\fonts\\source-sans-pro'), ('src\\assets\\fonts\\source-sans-pro\\SourceSansPro-Regular.ttf', 'src\\assets\\fonts\\source-sans-pro'), ('src\\assets\\fonts\\source-sans-pro\\SourceSansPro-Semibold.ttf', 'src\\assets\\fonts\\source-sans-pro'), ('src\\assets\\fonts\\source-sans-pro\\SourceSansPro-SemiboldItalic.ttf', 'src\\assets\\fonts\\source-sans-pro')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MeasureSummary',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src\\assets\\images\\etrm.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MeasureSummary',
)
