"""
PyInstaller 빌드 스크립트
========================
python build_exe.py → dist/SecureOps.exe
"""

import PyInstaller.__main__
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    os.path.join(BASE_DIR, "main.py"),
    "--onefile",
    "--name", "SecureOps",
    "--icon", "NONE",
    "--add-data", f"{os.path.join(BASE_DIR, 'interceptor')};interceptor",
    "--hidden-import", "pystray",
    "--hidden-import", "PIL",
    "--console",   # 디버깅용 콘솔 표시 (배포 시 --noconsole로 변경)
    "--clean",
])

print("\n✅ 빌드 완료: dist/SecureOps.exe")
