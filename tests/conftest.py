import itertools as it
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Tuple

import pytest
import segyio
from filelock import FileLock
from segyio import SegyFile, TraceSortingFormat

import tilesegy
from tilesegy import TileSegy, cli

from .segyio_utils import generate_structured_segy, generate_unstructured_segy

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES_DIR.mkdir(exist_ok=True)

UNSTRUCTURED_SEGY_COMBOS = {
    "sorting": [TraceSortingFormat.UNKNOWN_SORTING],
    "traces": [6300],
    "samples": [10],
}
STRUCTURED_SEGY_COMBOS = {
    "sorting": [
        TraceSortingFormat.CROSSLINE_SORTING,
        TraceSortingFormat.INLINE_SORTING,
    ],
    "ilines": [28],
    "xlines": [90],
    "offsets": [1, 5],
    "samples": [10],
}


def iter_tsgy_sgy_files(
    structured: Optional[bool] = None, multiple_offsets: Optional[bool] = None
) -> Iterator[Tuple[TileSegy, SegyFile]]:
    if structured is None:
        yield from iter_tsgy_sgy_files(False, multiple_offsets)
        yield from iter_tsgy_sgy_files(True, multiple_offsets)
        return

    generate_segy: Callable[..., None]
    if structured:
        combos = STRUCTURED_SEGY_COMBOS
        generate_segy = generate_structured_segy
    else:
        combos = UNSTRUCTURED_SEGY_COMBOS
        generate_segy = generate_unstructured_segy

    for values in it.product(*combos.values()):
        kwargs = dict(zip(combos.keys(), values))
        if (
            structured
            and multiple_offsets is not None
            and bool(multiple_offsets) == (kwargs["offsets"] < 2)
        ):
            continue

        basename = "-".join("{}={}".format(*item) for item in kwargs.items())
        sgy_path = FIXTURES_DIR / (basename + ".sgy")
        tsgy_path = FIXTURES_DIR / (basename + ".tsgy")

        with FileLock(FIXTURES_DIR / (basename + ".lock")):
            if not sgy_path.exists():
                generate_segy(sgy_path, **kwargs)
            if not tsgy_path.exists():
                cli.main(list(map(str, [sgy_path, tsgy_path])))

        yield tilesegy.open(tsgy_path), segyio.open(sgy_path, strict=False)


def parametrize_tilesegy_segyfiles(
    tilesegy_name: str,
    segyfile_name: str,
    structured: Optional[bool] = None,
    multiple_offsets: Optional[bool] = None,
) -> Any:
    return pytest.mark.parametrize(
        (tilesegy_name, segyfile_name),
        iter_tsgy_sgy_files(structured, multiple_offsets),
        ids=lambda x: Path(x.uri).stem if isinstance(x, TileSegy) else None,
    )
