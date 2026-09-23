# Licensed to the .NET Foundation under one or more agreements.
# The .NET Foundation licenses this file to you under the MIT license.

"""Run synthetic runtime questions through the one canonical loopback service."""

import argparse
import json
from pathlib import Path
import sys

from runtime_history import HttpProvider, investigate
from synthetic_fixture import (
    BUILD_IDS, NATIVE_SIGNATURE, SIGNATURE, fixture, identity, native_identity,
    originals, verifier,
)


def load_shared(shared_root):
    root = Path(shared_root).resolve(strict=True)
    if not (root / "fixture_service.py").is_file():
        raise ValueError("--shared-root must contain the canonical fixture_service.py")
    sys.path.insert(0, str(root))


def run():
    from fixture_service import fixture_service
    from history_http_common import Problem

    results = {}
    with fixture_service(fixture()) as client:
        provider = HttpProvider(client)
        for options in ("None", "Asynchronous"):
            case = identity(options)
            records = originals(case, SIGNATURE, BUILD_IDS[:2], [700003])
            results[options] = investigate(
                provider, BUILD_IDS, case, SIGNATURE, 700002, 700003,
                verifier(records))
        case = native_identity()
        results["nativeWithoutConsole"] = investigate(
            provider, BUILD_IDS, case, NATIVE_SIGNATURE, 700002, 700003,
            verifier({}), native_assertion=True)
        results["nativeWithConsole"] = investigate(
            provider, BUILD_IDS, case, NATIVE_SIGNATURE, 700002, 700003,
            verifier(originals(case, NATIVE_SIGNATURE, [700002], [700003])),
            native_assertion=True)
        results["infrastructureWithoutTests"] = investigate(
            provider, BUILD_IDS, {**identity(), "TestName": "Example.NoTests"},
            SIGNATURE, 700002, 700003, verifier({}))
    failures = {}
    for fault in ("partial", "unavailable", "invalid"):
        try:
            with fixture_service({**fixture(), "fault": {"kind": fault}}) as client:
                investigate(HttpProvider(client), BUILD_IDS, identity(), SIGNATURE,
                            700002, 700003, verifier({}))
        except Problem as error:
            failures[fault] = {
                "queryCompleted": False,
                "status": error.status,
                "kind": error.kind,
                "unknownBuildIds": BUILD_IDS,
            }
        else:
            raise AssertionError("Synthetic source failure unexpectedly succeeded")
    return {
        "evidence": "new synthetic fixture over loopback HTTP, not historical replay",
        "cases": results,
        "serviceFailures": failures,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-root", required=True)
    args = parser.parse_args()
    load_shared(args.shared_root)
    print(json.dumps(run(), indent=2, sort_keys=True))
