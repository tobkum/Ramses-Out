"""Tests for the batched daemon-data maps used by Ramses Out."""

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ramses_out.api_cache import build_api_maps, fetch_status_map, find_state, advance_statuses


def _obj(uuid, short_name, **data):
    o = MagicMock()
    o.uuid.return_value = uuid
    o.shortName.return_value = short_name
    o.get.side_effect = lambda k, d=None: data.get(k, d)
    o.colorName.return_value = data.get("color", "#e3e3e3")
    return o


class TestBuildApiMaps(unittest.TestCase):
    def setUp(self):
        self.sequences = [_obj("seq-1", "SEQ01"), _obj("seq-2", "SEQ02")]
        self.shots = [
            _obj("shot-1", "SH010", sequence="seq-1"),
            _obj("shot-2", "SH020", sequence="seq-2"),
            _obj("shot-3", "SH030", sequence=""),       # no sequence
            _obj("shot-4", "", sequence="seq-1"),        # nameless → skipped
        ]
        self.steps = [_obj("step-1", "COMP"), _obj("step-2", "ANIM")]
        self.states = [
            _obj("state-ok", "OK", color="#00aa00"),
            _obj("state-wip", "WIP", color="#f39c12"),
        ]

    def test_maps_built_from_bulk_results(self):
        maps = build_api_maps(self.sequences, self.shots, self.steps, self.states)

        self.assertEqual(maps["api_sequences"], ["SEQ01", "SEQ02"])
        self.assertEqual(maps["api_steps"], ["COMP", "ANIM"])
        # Shot→sequence resolved through the shot's sequence uuid — this is
        # the single-bulk-call replacement for the old per-sequence fetching.
        self.assertEqual(maps["shot_seq_map"], {"SH010": "SEQ01", "SH020": "SEQ02"})
        self.assertEqual(maps["shot_uuid_map"]["SH010"], "shot-1")
        self.assertNotIn("SH030", maps["shot_seq_map"])   # no sequence
        self.assertIn("SH030", maps["shot_uuid_map"])     # but still addressable
        self.assertEqual(maps["step_uuid_map"], {"COMP": "step-1", "ANIM": "step-2"})
        self.assertEqual(maps["state_map"]["state-ok"], ("OK", "#00aa00"))


class TestFetchStatusMap(unittest.TestCase):
    def test_status_resolution(self):
        maps = build_api_maps(
            [_obj("seq-1", "SEQ01")],
            [_obj("shot-1", "SH010", sequence="seq-1")],
            [_obj("step-1", "COMP")],
            [_obj("state-ok", "OK", color="#00aa00")],
        )

        status = MagicMock()
        status.get.side_effect = lambda k, d=None: {"state": "state-ok"}.get(k, d)
        daemon = MagicMock()
        daemon.getStatus.return_value = status

        result = fetch_status_map(
            daemon,
            [("SH010", "COMP"), ("SH999", "COMP")],   # SH999 unknown → skipped
            maps["shot_uuid_map"], maps["step_uuid_map"], maps["state_map"],
        )

        self.assertEqual(result, {("SH010", "COMP"): ("OK", "#00aa00")})
        daemon.getStatus.assert_called_once_with("shot-1", "step-1")

    def test_missing_status_and_daemon_errors_are_skipped(self):
        maps = build_api_maps(
            [], [_obj("shot-1", "SH010")], [_obj("step-1", "COMP")], []
        )
        daemon = MagicMock()
        daemon.getStatus.side_effect = [None, RuntimeError("socket")]

        result = fetch_status_map(
            daemon, [("SH010", "COMP"), ("SH010", "COMP")],
            maps["shot_uuid_map"], maps["step_uuid_map"], maps["state_map"],
        )
        self.assertEqual(result, {})


class TestFindState(unittest.TestCase):
    def setUp(self):
        self.states = [_obj("s-rfr", "RFR"), _obj("s-chk", "CHK"), _obj("s-ok", "OK")]

    def test_found_case_insensitive(self):
        self.assertIs(find_state(self.states, "chk"), self.states[1])

    def test_not_found(self):
        self.assertIsNone(find_state(self.states, "ZZZ"))

    def test_empty_name(self):
        self.assertIsNone(find_state(self.states, ""))


class TestAdvanceStatuses(unittest.TestCase):
    def setUp(self):
        maps = build_api_maps(
            [], [_obj("shot-1", "SH010"), _obj("shot-2", "SH020")],
            [_obj("step-1", "COMP")], [],
        )
        self.shot_uuid_map = maps["shot_uuid_map"]
        self.step_uuid_map = maps["step_uuid_map"]
        self.target = _obj("s-chk", "CHK")

    def _status(self, uuid="st-1"):
        st = MagicMock()
        st.uuid.return_value = uuid
        return st

    def test_advances_each_pair_and_records_modifier(self):
        st1, st2 = self._status("st-1"), self._status("st-2")
        daemon = MagicMock()
        daemon.getStatus.side_effect = [st1, st2]

        ok, fail = advance_statuses(
            daemon, [("SH010", "COMP"), ("SH020", "COMP")], self.target,
            self.shot_uuid_map, self.step_uuid_map,
        )
        self.assertEqual((ok, fail), (2, 0))
        st1.setState.assert_called_once_with(self.target)
        st2.setState.assert_called_once_with(self.target)
        # The modifier is recorded against each status' own uuid.
        daemon.setStatusModifiedBy.assert_any_call("st-1")
        daemon.setStatusModifiedBy.assert_any_call("st-2")

    def test_unknown_shot_or_step_counts_as_failure(self):
        daemon = MagicMock()
        daemon.getStatus.return_value = self._status()
        ok, fail = advance_statuses(
            daemon, [("SH999", "COMP"), ("SH010", "ZZZ")], self.target,
            self.shot_uuid_map, self.step_uuid_map,
        )
        self.assertEqual((ok, fail), (0, 2))
        daemon.getStatus.assert_not_called()

    def test_missing_status_and_errors_are_failures_not_raises(self):
        daemon = MagicMock()
        daemon.getStatus.side_effect = [None, RuntimeError("socket")]
        ok, fail = advance_statuses(
            daemon, [("SH010", "COMP"), ("SH020", "COMP")], self.target,
            self.shot_uuid_map, self.step_uuid_map,
        )
        self.assertEqual((ok, fail), (0, 2))


if __name__ == "__main__":
    unittest.main()
