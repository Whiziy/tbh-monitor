# Build with: pyinstaller build.spec
# Output: dist/tbh-monitor.exe (single file, no console window)

a = Analysis(
    ["main.py"],
    pathex=[".", "reader"],
    binaries=[],
    datas=[("config.json", "."), ("reader", "reader"), ("assets", "assets")],
    hiddenimports=["reader.shared.memory", "reader.shared.utils", "reader.il2cpp.resolver", 
                   "reader.il2cpp.typeinfo", "reader.il2cpp.finder", "reader.game.models",
                   "reader.game.save", "reader.game.build", "reader.game.obscured",
                   "reader.metrics.dps", "reader.metrics.gold", "reader.metrics.xp",
                   "reader.config.offsets", "pypresence", "core.discord_rpc"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="tbh-monitor",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    onefile=True,
    icon="assets/icon.ico",
)
