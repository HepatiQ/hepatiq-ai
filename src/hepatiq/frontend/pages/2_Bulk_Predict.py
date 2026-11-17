from pathlib import Path


def _main() -> None:
    import sys

    src = str(Path(__file__).resolve().parents[2])
    if src not in sys.path:
        sys.path.insert(0, src)
    from hepatiq.frontend.bulk_upload import render_bulk_upload

    render_bulk_upload()


_main()
