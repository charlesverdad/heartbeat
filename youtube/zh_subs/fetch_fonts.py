#!/usr/bin/env python3
"""Download the two subtitle fonts into ./fonts (gitignored, ~16 MB).

libass on macOS cannot see PingFang, and the only installed Traditional face
with Latin coverage is Heiti TC Light, too thin for an older reader. A missing
family does not error -- libass draws empty boxes -- so the burn uses these
bundled files through `fontsdir` instead of whatever is installed.
"""
import io, pathlib, urllib.request, zipfile

FONTS = pathlib.Path(__file__).parent / "fonts"
NOTO = "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Medium.otf"
VAZIR = "https://github.com/rastikerdar/vazirmatn/releases/download/v33.003/vazirmatn-v33.003.zip"

def get(url):
    print("fetching", url)
    with urllib.request.urlopen(url) as r:
        return r.read()

if __name__ == "__main__":
    FONTS.mkdir(exist_ok=True)
    noto = FONTS / "NotoSansCJKtc-Medium.otf"
    if not noto.exists():
        noto.write_bytes(get(NOTO))
    want = {"Vazirmatn-SemiBold.ttf", "Vazirmatn-Medium.ttf"}
    if not all((FONTS / w).exists() for w in want):
        with zipfile.ZipFile(io.BytesIO(get(VAZIR))) as z:
            for name in z.namelist():
                # the zip carries the same faces under several dirs; take the plain TTFs
                if pathlib.PurePath(name).name in want and "/ttf/" in f"/{name}" and "Vazirmatn-UI" not in name:
                    (FONTS / pathlib.PurePath(name).name).write_bytes(z.read(name))
    print("fonts:", sorted(p.name for p in FONTS.glob("*.*")))
