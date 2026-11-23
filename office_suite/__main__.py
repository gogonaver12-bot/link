import sys

from . import core


def main(argv):
    if argv[:1] == ["list"]:
        for p in core.load_plugins():
            print(f"{p.key:16} {p.name}  {('[오류] ' + p.error) if p.error else p.desc}")
        return 0
    if argv[:1] == ["run"] and len(argv) >= 2:   # python -m office_suite run ppt 제목=보고서 ...
        plug = next((p for p in core.load_plugins() if p.key == argv[1]), None)
        if not plug:
            print("없는 기능:", argv[1]); return 1
        raw = dict(a.split("=", 1) for a in argv[2:] if "=" in a)
        res = core.run_plugin(plug, raw)
        print(res.message, *res.files, sep="\n")
        return 0 if res.ok else 1
    from . import gui
    gui.main()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
