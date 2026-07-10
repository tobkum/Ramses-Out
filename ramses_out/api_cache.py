"""Daemon data caching for Ramses Out — batched, testable, no Qt.

Replaces the old per-sequence shot fetching (N+1 socket calls) with two bulk
queries and adds shot/step status lookup so the UI can show the pipeline
state (WIP/OK/…) next to each preview.
"""

from typing import Dict, List, Tuple

from . import paths  # noqa: F401 — side effect: lib/ on sys.path


def build_api_maps(sequences, shots, steps, states) -> dict:
    """Build lookup maps from bulk daemon results.

    Args:
        sequences: RamSequence list (with data) — ``daemon.getSequences(includeData=True)``
        shots: RamShot list (with data) — ``daemon.getShots(includeData=True)``;
            one call returns ALL shots with their sequence uuid, replacing the
            old one-call-per-sequence pattern.
        steps: RamStep list — ``project.steps(StepType.SHOT_PRODUCTION, lazyLoading=False)``
        states: RamState list — ``Ramses.states()``

    Returns:
        dict with:
            api_sequences: sorted sequence short names
            api_steps: step short names
            shot_seq_map: shot short name -> sequence short name
            shot_uuid_map: SHOT SHORT NAME (upper) -> uuid
            step_uuid_map: STEP SHORT NAME (upper) -> uuid
            state_map: state uuid -> (short name, color hex)
    """
    seq_names: Dict[str, str] = {}
    api_sequences: List[str] = []
    for seq in sequences:
        name = seq.shortName()
        if not name:
            continue
        seq_names[str(seq.uuid())] = name
        api_sequences.append(name)

    shot_seq_map: Dict[str, str] = {}
    shot_uuid_map: Dict[str, str] = {}
    for shot in shots:
        name = shot.shortName()
        if not name:
            continue
        shot_uuid_map[name.upper()] = str(shot.uuid())
        seq_uuid = str(shot.get("sequence", "") or "")
        seq_name = seq_names.get(seq_uuid)
        if seq_name:
            shot_seq_map[name] = seq_name

    api_steps: List[str] = []
    step_uuid_map: Dict[str, str] = {}
    for step in steps:
        name = step.shortName()
        if not name:
            continue
        api_steps.append(name)
        step_uuid_map[name.upper()] = str(step.uuid())

    state_map: Dict[str, Tuple[str, str]] = {}
    for state in states:
        state_map[str(state.uuid())] = (state.shortName(), state.colorName())

    return {
        "api_sequences": api_sequences,
        "api_steps": api_steps,
        "shot_seq_map": shot_seq_map,
        "shot_uuid_map": shot_uuid_map,
        "step_uuid_map": step_uuid_map,
        "state_map": state_map,
    }


def fetch_status_map(daemon, pairs, shot_uuid_map, step_uuid_map, state_map) -> Dict[tuple, Tuple[str, str]]:
    """Fetch the DB status for each (shot_id, step_id) pair.

    Args:
        daemon: RamDaemonInterface instance
        pairs: iterable of (shot short name, step short name)
        shot_uuid_map / step_uuid_map / state_map: from :func:`build_api_maps`

    Returns:
        {(shot_id, step_id): (state short name, color hex)} — pairs whose
        shot/step is unknown to the DB, or that have no status yet, are absent.
    """
    status_map: Dict[tuple, Tuple[str, str]] = {}
    for shot_id, step_id in pairs:
        shot_uuid = shot_uuid_map.get((shot_id or "").upper())
        step_uuid = step_uuid_map.get((step_id or "").upper())
        if not shot_uuid or not step_uuid:
            continue
        try:
            status = daemon.getStatus(shot_uuid, step_uuid)
        except Exception:
            continue
        if not status:
            continue
        state_uuid = str(status.get("state", "") or "")
        state_info = state_map.get(state_uuid)
        if state_info:
            status_map[(shot_id, step_id)] = state_info
    return status_map
