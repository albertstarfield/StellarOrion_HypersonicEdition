"""Regression tests for the validation-pipeline defects repaired on 2026-09-30.

Each test below pins one specific defect that existed in
``src/python/validation_pipeline.py`` or ``src/python/ada_pinn_wrapper.py``.
They are deliberately narrow: they exercise the exact contract that was broken
so a future refactor cannot silently reintroduce it.

Defects pinned here
-------------------
R1. ``run_validation_pipeline`` omitted the ``output_dir`` parameter even though
    ``main()`` calls it with ``output_dir=args.output_dir`` and the function
    body reads ``output_dir``. Calling it the way the CLI does raised
    ``TypeError: run_validation_pipeline() got an unexpected keyword argument
    'output_dir'``, which aborted the whole pipeline.
R2. ``_generate_pinn_vtu`` read VTU geometry with ``piece.get(...)``,
    ``.find(...).text`` and ``.text`` without ``None`` checks. A corrupt or
    non-VTU input produced ``AttributeError: 'NoneType' object has no
    attribute 'text'`` or silently fabricated a zero count instead of failing
    loudly with the offending attribute and file name.
R3. ``ada_pinn_wrapper`` defined ``dynamic_pressure`` twice; the second
    definition silently shadowed the first (Ruff F811), so the PINN Ada entry
    point was unreachable dead code while the public name kept working.

Run with:
    python3 -m pytest tests/test_validation_pipeline_regressions.py -v
    # or
    python3 -m unittest tests.test_validation_pipeline_regressions -v
"""

import inspect
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from unittest import main as unittest_main

# Ensure the sidecar package directory is importable. validation_pipeline.py
# lives in src/python, and it imports sibling modules (ada_pinn_wrapper) by bare
# name, so that directory must be on sys.path before the import below.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SIDECAR_DIR = _PROJECT_ROOT / "src" / "python"
for _path in (str(_PROJECT_ROOT), str(_SIDECAR_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import validation_pipeline as vp  # noqa: E402  (path setup must precede import)

# ---------------------------------------------------------------------------
# Minimal VTK XML UnstructuredGrid fixtures.
#
# AXIOM: these fixtures exercise the PARSER only. They are intentionally the
# smallest legal VTK XML document containing the elements
# ``_generate_pinn_vtu`` reads, so a test failure can only be caused by the
# parsing contract under test and never by unrelated geometry.
#
# [Reference: VTK XML UnstructuredGrid file format
#  https://vtk.org/wp-content/uploads/2015/04/file-formats.pdf]
# ---------------------------------------------------------------------------

#: A structurally complete Piece: 2 points, 1 quad cell (4 nodes).
_VALID_PIECE_BODY = """
      <Points>
        <DataArray NumberOfComponents="3" type="Float64">
          0.0 0.0 0.0 1.0 0.0 0.0 1.0 1.0 0.0 0.0 1.0 0.0
        </DataArray>
      </Points>
      <Cells>
        <DataArray type="Int32" Name="connectivity">0 1 2 3</DataArray>
        <DataArray type="Int32" Name="offsets">4</DataArray>
        <DataArray type="Int32" Name="types">9</DataArray>
      </Cells>
"""


def _wrap_vtu(piece_attrs: str, piece_body: str) -> str:
    """Build a VTK XML UnstructuredGrid document around the supplied Piece.

    AXIOM: ``piece_attrs`` is injected verbatim into the ``<Piece>`` start tag
    so a test can omit a required attribute, and ``piece_body`` replaces the
    geometry block so a test can omit a required DataArray. Nothing else
    varies, which isolates the behaviour under test.

    Args:
      piece_attrs: Attribute string for the ``<Piece>`` start tag.
      piece_body: Inner XML of the Piece element.

    Returns: A complete, well-formed VTK XML UnstructuredGrid document.
    """
    return (
        '<?xml version="1.0"?>\n'
        '<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian">\n'
        "  <UnstructuredGrid>\n"
        f"    <Piece{piece_attrs}>\n"
        f"{piece_body}"
        "    </Piece>\n"
        "  </UnstructuredGrid>\n"
        "</VTKFile>\n"
    )


class TestRunValidationPipelineSignature(unittest.TestCase):
    """Pin the public signature contract (regression R1)."""

    def test_output_dir_is_an_accepted_keyword(self) -> None:
        """``output_dir`` must be bindable as a keyword, as ``main()`` does.

        This is the exact call shape that previously raised
        ``TypeError: got an unexpected keyword argument 'output_dir'``.
        Inspecting the signature proves bindability without executing the
        multi-minute pipeline.
        """
        params = inspect.signature(vp.run_validation_pipeline).parameters
        self.assertIn(
            "output_dir",
            params,
            "run_validation_pipeline must accept output_dir; main() passes it "
            "as a keyword argument",
        )
        self.assertIs(
            vp.run_validation_pipeline.__code__.co_varnames[: len(params)][
                list(params).index("output_dir")
            ],
            "output_dir",
            "output_dir must be a named parameter, not a **kwargs catch-all",
        )

    def test_output_dir_defaults_to_none(self) -> None:
        """``output_dir`` must default to ``None`` so existing callers work."""
        default = inspect.signature(
            vp.run_validation_pipeline
        ).parameters["output_dir"].default
        self.assertIsNone(default)

    def test_csv_path_remains_the_first_positional_parameter(self) -> None:
        """The leading positional order must stay backward compatible."""
        names = list(inspect.signature(vp.run_validation_pipeline).parameters)
        self.assertEqual(names[0], "csv_path")
        self.assertEqual(names[-1], "output_dir")


class TestRequireIntAttr(unittest.TestCase):
    """Pin ``_require_int_attr`` behaviour (regression R2, count attributes)."""

    def test_returns_integer_for_valid_attribute(self) -> None:
        """A well-formed attribute is returned as an ``int``."""
        element = ET.fromstring('<Piece NumberOfPoints="2200" NumberOfCells="1"/>')
        self.assertEqual(vp._require_int_attr(element, "NumberOfPoints", "ctx.vtu"), 2200)

    def test_missing_attribute_raises_with_attribute_and_context(self) -> None:
        """A missing attribute fails loudly, naming BOTH the attribute and file.

        Without the context in the message an operator cannot tell which of
        thousands of VTU files is corrupt.
        """
        element = ET.fromstring("<Piece NumberOfCells='1'/>")
        with self.assertRaises(ValueError) as ctx:
            vp._require_int_attr(element, "NumberOfPoints", "/data/surf_2200.vtu")
        message = str(ctx.exception)
        self.assertIn("NumberOfPoints", message)
        self.assertIn("/data/surf_2200.vtu", message)

    def test_non_integer_attribute_raises_and_quotes_offending_value(self) -> None:
        """Garbage in the attribute is reported verbatim, not swallowed.

        ``int()`` would otherwise fail with a bare message that omits which
        value was bad.
        """
        element = ET.fromstring('<Piece NumberOfPoints="not-a-number"/>')
        with self.assertRaises(ValueError) as ctx:
            vp._require_int_attr(element, "NumberOfPoints", "ctx.vtu")
        self.assertIn("not-a-number", str(ctx.exception))


class TestRequireElementText(unittest.TestCase):
    """Pin ``_require_element_text`` behaviour (regression R2, DataArrays)."""

    def test_returns_stripped_payload(self) -> None:
        """A populated DataArray yields its stripped character data."""
        element = ET.fromstring(
            '<Piece><Points><DataArray>  1.0 2.0 3.0  </DataArray></Points></Piece>'
        )
        self.assertEqual(
            vp._require_element_text(element, "Points/DataArray", "ctx.vtu"),
            "1.0 2.0 3.0",
        )

    def test_missing_element_raises_naming_xpath_and_context(self) -> None:
        """An absent element raises ``ValueError``, not ``AttributeError``."""
        element = ET.fromstring("<Piece><Points/></Piece>")
        with self.assertRaises(ValueError) as ctx:
            vp._require_element_text(element, "Points/DataArray", "/data/surf_1.vtu")
        message = str(ctx.exception)
        self.assertIn("Points/DataArray", message)
        self.assertIn("/data/surf_1.vtu", message)

    def test_empty_dataarray_raises(self) -> None:
        """A self-closed/blank DataArray raises instead of yielding ``""``.

        ElementTree reports both ``<DataArray/>`` and whitespace-only content as
        unusable geometry; returning ``""`` would let a zero-geometry VTU be
        written and rendered as an empty ParaView scene.
        """
        element = ET.fromstring("<Piece><Points><DataArray/></Points></Piece>")
        with self.assertRaises(ValueError):
            vp._require_element_text(element, "Points/DataArray", "ctx.vtu")

    def test_whitespace_only_dataarray_raises(self) -> None:
        """Whitespace-only character data is also unusable geometry."""
        element = ET.fromstring(
            "<Piece><Points><DataArray>   \n  </DataArray></Points></Piece>"
        )
        with self.assertRaises(ValueError):
            vp._require_element_text(element, "Points/DataArray", "ctx.vtu")


class TestOptionalElementText(unittest.TestCase):
    """Pin ``_optional_element_text`` behaviour (regression R2, Drag_N/Lift_N).

    AXIOM: ``Drag_N``/``Lift_N`` are OPTIONAL. VTUs written before those fields
    existed still render in ParaView, so their absence must collapse to ``""``
    and must never abort generation.
    """

    def test_missing_element_returns_empty_string(self) -> None:
        """Absence collapses to ``""`` rather than raising."""
        element = ET.fromstring("<Piece><CellData/></Piece>")
        self.assertEqual(
            vp._optional_element_text(
                element, 'CellData/DataArray[@Name="Drag_N"]'
            ),
            "",
        )

    def test_none_text_returns_empty_string(self) -> None:
        """An element with no character data collapses to ``""`` too."""
        element = ET.fromstring(
            '<Piece><CellData><DataArray Name="Lift_N"/></CellData></Piece>'
        )
        self.assertEqual(
            vp._optional_element_text(
                element, 'CellData/DataArray[@Name="Lift_N"]'
            ),
            "",
        )

    def test_present_field_is_returned_stripped(self) -> None:
        """A present optional field is returned normally."""
        element = ET.fromstring(
            '<Piece><CellData><DataArray Name="Drag_N"> 12.5 13.5 </DataArray>'
            "</CellData></Piece>"
        )
        self.assertEqual(
            vp._optional_element_text(
                element, 'CellData/DataArray[@Name="Drag_N"]'
            ),
            "12.5 13.5",
        )


class TestGeneratePinnVtuFailsLoudly(unittest.TestCase):
    """Pin end-to-end failure behaviour of ``_generate_pinn_vtu`` (R2).

    These are integration tests: they drive the real function against a real
    (deliberately corrupt) VTU on disk, proving the helpers are actually wired
    into the parse path and not merely defined.
    """

    def _run_generate(self, vtu_xml: str) -> str:
        """Invoke ``_generate_pinn_vtu`` against a single corrupt VTU file.

        AXIOM: the function derives its VTU search directory from
        ``dirname(csv_path)``, so writing the fixture to
        ``<tmp>/paraview/surf_2200.vtu`` places it exactly where production
        looks, and a non-existent CSV path is sufficient because parsing
        fails before the CSV is ever read.

        Args:
          vtu_xml: The full VTK XML document to write as the fixture.

        Returns: The message of the ``ValueError`` that was raised.
        """
        with tempfile.TemporaryDirectory() as tmp:
            paraview_dir = Path(tmp) / "paraview"
            os.makedirs(paraview_dir, exist_ok=True)
            (paraview_dir / "surf_2200.vtu").write_text(vtu_xml, encoding="utf-8")

            csv_path = str(Path(tmp) / "validation_timeseries.csv")
            # The reported context must be the offending file, so the message
            # is asserted to contain the fixture's real absolute path.
            with self.assertRaises(ValueError) as ctx:
                vp._generate_pinn_vtu(
                    results={},
                    output_dir=tmp,
                    csv_path=csv_path,
                    hf_avg=1.0,
                    hf_max=2.0,
                    qload=3.0,
                    g_load=4.0,
                    cd=0.5,
                )
            return str(ctx.exception)

    def test_missing_number_of_points_attribute_raises_valueerror(self) -> None:
        """Omitting ``NumberOfPoints`` raises ``ValueError`` naming the attribute.

        Before the fix this produced
        ``TypeError: int() argument must be a string...`` from ``int(None)``.
        """
        message = self._run_generate(
            _wrap_vtu(' NumberOfCells="1"', _VALID_PIECE_BODY)
        )
        self.assertIn("NumberOfPoints", message)
        self.assertIn("surf_2200.vtu", message)

    def test_missing_points_dataarray_raises_valueerror(self) -> None:
        """Omitting ``Points/DataArray`` raises ``ValueError`` naming the XPath.

        Before the fix this produced
        ``AttributeError: 'NoneType' object has no attribute 'text'``.
        """
        piece_body = """
      <Cells>
        <DataArray type="Int32" Name="connectivity">0 1 2 3</DataArray>
        <DataArray type="Int32" Name="offsets">4</DataArray>
        <DataArray type="Int32" Name="types">9</DataArray>
      </Cells>
"""
        message = self._run_generate(
            _wrap_vtu(' NumberOfPoints="4" NumberOfCells="1"', piece_body)
        )
        self.assertIn("Points/DataArray", message)
        self.assertIn("surf_2200.vtu", message)

    def test_empty_points_payload_raises_valueerror(self) -> None:
        """A blank ``Points/DataArray`` raises rather than writing empty geometry."""
        piece_body = """
      <Points>
        <DataArray NumberOfComponents="3" type="Float64"></DataArray>
      </Points>
      <Cells>
        <DataArray type="Int32" Name="connectivity">0 1 2 3</DataArray>
        <DataArray type="Int32" Name="offsets">4</DataArray>
        <DataArray type="Int32" Name="types">9</DataArray>
      </Cells>
"""
        message = self._run_generate(
            _wrap_vtu(' NumberOfPoints="4" NumberOfCells="1"', piece_body)
        )
        self.assertIn("Points/DataArray", message)


class TestDynamicPressureApiPreserved(unittest.TestCase):
    """Pin the ``ada_pinn_wrapper`` duplicate-definition fix (regression R3)."""

    def test_public_dynamic_pressure_is_importable_and_unique(self) -> None:
        """``dynamic_pressure`` must remain importable with its original signature.

        ``validation_pipeline`` and ``pinn_test`` both do
        ``from ada_pinn_wrapper import dynamic_pressure``; renaming the public
        symbol would break them at import time.
        """
        import ada_pinn_wrapper

        self.assertTrue(callable(ada_pinn_wrapper.dynamic_pressure))
        params = list(
            inspect.signature(ada_pinn_wrapper.dynamic_pressure).parameters
        )
        self.assertEqual(params, ["density_kgm3", "velocity_ms"])

    def test_pinn_entry_point_is_reachable_under_a_distinct_name(self) -> None:
        """The previously shadowed PINN binding must no longer be dead code.

        Both Ada entry points compute q = 0.5*rho*V^2, so the wrapper should
        still be present and callable once the shadowing is removed.
        """
        import ada_pinn_wrapper

        self.assertTrue(callable(ada_pinn_wrapper.dynamic_pressure_pinn_trajectory))

    def test_module_defines_no_duplicate_top_level_functions(self) -> None:
        """No top-level function may be defined twice (guards against F811 relapse).

        Two same-named definitions mean the first is unreachable, which is the
        exact defect that produced the original F811.
        """
        import ast

        import ada_pinn_wrapper

        tree = ast.parse(Path(ada_pinn_wrapper.__file__).read_text(encoding="utf-8"))
        names = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        self.assertEqual(
            duplicates,
            [],
            f"duplicate top-level definitions shadow earlier ones: {duplicates}",
        )


class TestHelperDocstrings(unittest.TestCase):
    """Assert the new helpers keep their mandated documentation."""

    def test_each_helper_has_a_docstring(self) -> None:
        """Project standard requires documentation on every helper."""
        for name in (
            "_require_int_attr",
            "_require_element_text",
            "_optional_element_text",
        ):
            helper: Any = getattr(vp, name)
            with self.subTest(helper=name):
                self.assertTrue(
                    (helper.__doc__ or "").strip(),
                    f"{name} must carry a docstring",
                )


if __name__ == "__main__":
    unittest_main()
