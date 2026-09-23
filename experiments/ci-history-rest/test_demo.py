# Licensed to the .NET Foundation under one or more agreements.
# The .NET Foundation licenses this file to you under the MIT license.

"""Focused offline tests; invoke directly with --shared-root."""

import argparse
from copy import deepcopy
import socket
import unittest
from urllib.parse import urlsplit

from demo import load_shared, run
from runtime_history import HttpProvider, WIRE_FIELDS, decision, investigate, request_for
from synthetic_fixture import (
    BUILD_IDS, NATIVE_SIGNATURE, SIGNATURE, fixture, identity, native_identity,
    originals, verifier,
)


class RuntimeHistoryTests(unittest.TestCase):
    def test_exact_question_and_opaque_values(self):
        case = identity()
        request = request_for(list(reversed(BUILD_IDS)), case, SIGNATURE)
        self.assertEqual(request["buildIds"], BUILD_IDS)
        self.assertEqual(request["projection"], "case")
        self.assertEqual(request["outcome"], "Failed")
        self.assertEqual(request["filters"], {
            **{wire: case[field] for field, wire in WIRE_FIELDS.items()},
            "errorContains": SIGNATURE,
        })
        self.assertNotIn("errorContains", request_for(BUILD_IDS, case, None)["filters"])
        with self.assertRaisesRegex(ValueError, "nonempty"):
            request_for(BUILD_IDS, case, "")

    def test_parameter_cases_keep_aliased_references(self):
        with fixture_service(fixture()) as client:
            provider = HttpProvider(client)
            first = provider.question(BUILD_IDS, identity(), SIGNATURE)
            second = provider.question(BUILD_IDS, identity("Asynchronous"), SIGNATURE)
        self.assertEqual(len(first["groups"]), 1)
        self.assertEqual(len(second["groups"]), 1)
        left, right = first["groups"][0], second["groups"][0]
        self.assertEqual(left["matchingBuildIds"], [700001, 700002])
        self.assertEqual(right["matchingBuildIds"], [700001, 700002])
        self.assertNotEqual(left["identity"], right["identity"])
        self.assertEqual(left["references"], right["references"])
        self.assertEqual(left["references"][0]["workItemId"], 7)
        self.assertEqual(left["references"][0]["helixJobId"],
                         "00000000-0000-4000-8000-000000000001")
        self.assertEqual(left["references"][0]["referenceVerification"], "notChecked")

    def test_each_identity_predicate_is_needed(self):
        with fixture_service(fixture()) as client:
            exact = request_for(BUILD_IDS, identity(), SIGNATURE)
            self.assertEqual(client.query("dotnet/runtime", exact)["notObservedBuildIds"],
                             [700003])
            for field in WIRE_FIELDS.values():
                with self.subTest(field=field):
                    weakened = deepcopy(exact)
                    del weakened["filters"][field]
                    result = client.query("dotnet/runtime", weakened)
                    self.assertEqual(result["notObservedBuildIds"], [])

    def test_signature_is_case_sensitive(self):
        with fixture_service(fixture()) as client:
            answer = HttpProvider(client).question(BUILD_IDS, identity(), SIGNATURE.lower())
        self.assertEqual(answer["groups"][0]["matchingBuildIds"], [700003])
        self.assertEqual(answer["notObservedBuildIds"], [700001, 700002])

    def test_all_unverified_builds_need_originals_even_when_indexed(self):
        calls = []

        def unknown(build, case, signature, references):
            calls.append((build, references))
            return "unknown"

        with fixture_service(fixture()) as client:
            result = investigate(HttpProvider(client), BUILD_IDS, identity(), SIGNATURE,
                                 700002, 700003, unknown)
        self.assertEqual([build for build, _ in calls], BUILD_IDS)
        self.assertTrue(calls[0][1])
        self.assertFalse(calls[2][1])
        self.assertEqual(result["originalEvidence"],
                         {"positive": [], "negative": [], "unknown": BUILD_IDS})
        self.assertEqual(result["preMatcherDecision"], "unknown-source")

    def test_wrong_case_or_incomplete_console_is_unknown(self):
        records = originals(identity(), SIGNATURE, [700002])
        check = verifier(records)
        self.assertEqual(check(700002, identity("Asynchronous"), SIGNATURE, []), "unknown")
        records[700002]["complete"] = False
        self.assertEqual(check(700002, identity(), SIGNATURE, []), "unknown")

    def test_unobserved_follow_up_without_originals_remains_unknown(self):
        with fixture_service(fixture()) as client:
            result = investigate(
                HttpProvider(client), BUILD_IDS, identity(), SIGNATURE, 700002, 700003,
                verifier(originals(identity(), SIGNATURE, BUILD_IDS[:2])))
        self.assertEqual(result["notObserved"], [700003])
        self.assertEqual(result["originalEvidence"],
                         {"positive": [700001, 700002], "negative": [], "unknown": [700003]})
        self.assertEqual(result["preMatcherDecision"], "unknown-follow-up")

    def test_native_assertion_requires_console(self):
        case = native_identity()
        with fixture_service(fixture()) as client:
            provider = HttpProvider(client)
            self.assertEqual(provider.question(BUILD_IDS, case, NATIVE_SIGNATURE)["groups"], [])
            without = investigate(provider, BUILD_IDS, case, NATIVE_SIGNATURE,
                                  700002, 700003, verifier({}), native_assertion=True)
            with_console = investigate(
                provider, BUILD_IDS, case, NATIVE_SIGNATURE, 700002, 700003,
                verifier(originals(case, NATIVE_SIGNATURE, [700002], [700003])),
                native_assertion=True)
        self.assertEqual(without["indexedCandidates"], [700002])
        self.assertEqual(without["originalEvidence"]["positive"], [])
        self.assertEqual(with_console["originalEvidence"],
                         {"positive": [700002], "negative": [700003], "unknown": [700001]})
        self.assertEqual(with_console["preMatcherDecision"],
                         "skipped: signature absent from follow-up")

    def test_no_tests_is_unknown_not_passed(self):
        with fixture_service(fixture()) as client:
            result = investigate(
                HttpProvider(client), BUILD_IDS, {**identity(), "TestName": "Example.NoTests"},
                SIGNATURE, 700002, 700003, verifier({}))
        self.assertTrue(result["queryCompleted"])
        self.assertEqual(result["dataCompleteness"], "unknown")
        self.assertEqual(result["notObserved"], BUILD_IDS)
        self.assertEqual(result["originalEvidence"]["unknown"], BUILD_IDS)
        self.assertEqual(result["preMatcherDecision"], "unknown-source")

    def test_service_errors_propagate_without_empty_success(self):
        expected = {"partial": (502, "source-incomplete"),
                    "invalid": (502, "source-invalid"),
                    "unavailable": (503, "dependency-unavailable")}
        for fault, problem in expected.items():
            with self.subTest(fault=fault):
                with fixture_service({**fixture(), "fault": {"kind": fault}}) as client:
                    with self.assertRaises(Problem) as caught:
                        investigate(HttpProvider(client), BUILD_IDS, identity(), SIGNATURE,
                                    700002, 700003, lambda *args: self.fail("Enrichment ran"))
                self.assertEqual((caught.exception.status, caught.exception.kind), problem)

    def test_scope_and_duplicate_ids_fail_closed(self):
        with fixture_service(fixture()) as client:
            for ids, status in (([700001, 700001], 400), ([700001, 799999], 404)):
                with self.subTest(ids=ids):
                    with self.assertRaises(Problem) as caught:
                        HttpProvider(client).question(ids, identity(), SIGNATURE)
                    self.assertEqual(caught.exception.status, status)

    def test_empty_and_missing_arguments_are_distinct(self):
        data = fixture()
        case = native_identity()
        data["rows"].append({
            **data["rows"][4], "BuildId": 700001, "Arguments": None,
        })
        with fixture_service(data) as client:
            result = HttpProvider(client).question(BUILD_IDS, case, None)
        self.assertEqual(result["groups"][0]["identity"]["arguments"], "")
        self.assertEqual(result["groups"][0]["matchingBuildIds"], [700002])

    def test_existing_pre_matcher_decisions(self):
        cases = [
            ([700001, 700002, 700003], [], [], "stable: continue unchanged matcher/severity policy"),
            ([700002], [700003], [700001], "skipped: signature absent from follow-up"),
            ([700002], [], [700001, 700003], "unknown-follow-up"),
            ([], [], BUILD_IDS, "unknown-source"),
            ([700002, 700003], [], [700001], "unknown-stability"),
            ([700002, 700003], [700001], [], "skipped: < 2 occurrences and not blocking"),
        ]
        for positive, negative, unknown, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(decision(700002, 700003, positive, negative, unknown), expected)
        with self.assertRaisesRegex(ValueError, "Contradictory"):
            decision(700002, 700003, [700002], [700002], [])

    def test_invalid_enrichment_and_selection_raise(self):
        with fixture_service(fixture()) as client:
            provider = HttpProvider(client)
            with self.assertRaisesRegex(ValueError, "Original evidence"):
                investigate(provider, BUILD_IDS, identity(), SIGNATURE,
                            700002, 700003, lambda *args: "passed")
            for source, follow_up in ((700002, 700002), (799999, 700003)):
                with self.subTest(source=source, follow_up=follow_up):
                    with self.assertRaisesRegex(ValueError, "Distinct selected"):
                        investigate(provider, BUILD_IDS, identity(), SIGNATURE,
                                    source, follow_up, verifier({}))

    def test_owned_listener_and_token_are_removed(self):
        with fixture_service(fixture()) as client:
            HttpProvider(client).question(BUILD_IDS, identity(), SIGNATURE)
            address = urlsplit(client.base_url)
            token_file = client.token_file
            self.assertTrue(token_file.is_file())
        self.assertFalse(token_file.exists())
        with socket.socket() as probe:
            probe.settimeout(1)
            self.assertNotEqual(probe.connect_ex((address.hostname, address.port)), 0)

    def test_demo_output_distinguishes_fixture_evidence_and_failures(self):
        result = run()
        self.assertIn("not historical replay", result["evidence"])
        for case in ("None", "Asynchronous"):
            self.assertEqual(result["cases"][case]["indexedCandidates"], [700001, 700002])
            self.assertEqual(result["cases"][case]["preMatcherDecision"],
                             "skipped: signature absent from follow-up")
        for failure in result["serviceFailures"].values():
            self.assertFalse(failure["queryCompleted"])
            self.assertEqual(failure["unknownBuildIds"], BUILD_IDS)
            self.assertNotIn("groups", failure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-root", required=True)
    args = parser.parse_args()
    load_shared(args.shared_root)
    from fixture_service import fixture_service
    from history_http_common import Problem

    unittest.main(argv=[__file__], verbosity=2)
