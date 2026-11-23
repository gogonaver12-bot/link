"""exe 빌드용 시작 파일 (PyInstaller)."""
import sys

from office_suite.__main__ import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
