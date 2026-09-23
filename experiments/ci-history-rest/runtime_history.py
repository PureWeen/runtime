# Licensed to the .NET Foundation under one or more agreements.
# The .NET Foundation licenses this file to you under the MIT license.

"""Offline review seam adapted from the retained runtime history consumer."""

WIRE_FIELDS = {
    "BuildDefinitionId": "pipelineId",
    "WorkItemFriendlyName": "workItemFriendlyName",
    "QueueName": "queue",
    "TestRunName": "testRunName",
    "TestName": "testName",
    "Arguments": "arguments",
    "ArgumentHash": "argumentHash",
}


def request_for(build_ids, identity, pattern):
    request = {
        "buildIds": sorted(build_ids),
        "projection": "case",
        "outcome": "Failed",
        "filters": {wire: identity[field] for field, wire in WIRE_FIELDS.items()},
    }
    if pattern is not None:
        if not pattern:
            raise ValueError("An error substring must be nonempty when specified")
        request["filters"]["errorContains"] = pattern
    return request


class HttpProvider:
    """Only history retrieval moves here; selection and enrichment stay outside."""

    def __init__(self, client):
        self.client = client

    def question(self, build_ids, identity, pattern):
        request = request_for(build_ids, identity, pattern)
        result = self.client.query("dotnet/runtime", request)
        if result["repository"] != "dotnet/runtime" or result["query"] != request:
            raise ValueError("HTTP result does not belong to the exact runtime question")
        required = {
            "queryCompleteness": "complete",
            "dataCompleteness": "unknown",
            "snapshotConsistency": "notGuaranteed",
            "identityVerification": "notChecked",
            "referenceDetail": "caseReferences",
        }
        if any(result[key] != value for key, value in required.items()):
            raise ValueError("HTTP result overclaims completeness or verification")
        return result


def decision(source, follow_up, positives, negatives, unknown):
    """Retained historical pre-matcher gate, not the full scanner issue policy."""
    positives, negatives, unknown = map(set, (positives, negatives, unknown))
    if positives & negatives or positives & unknown or negatives & unknown:
        raise ValueError("Contradictory authoritative verdicts")
    if source not in positives:
        return "unknown-source"
    if follow_up in negatives:
        return "skipped: signature absent from follow-up"
    if follow_up not in positives:
        return "unknown-follow-up"
    if len(positives - {follow_up}) >= 2:
        return "stable: continue unchanged matcher/severity policy"
    if unknown:
        return "unknown-stability"
    return "skipped: < 2 occurrences and not blocking"


def investigate(provider, build_ids, identity, signature, source, follow_up,
                verify_original, *, native_assertion=False):
    """Feed history into the retained all-unverified-build enrichment boundary.

    verify_original receives each build, the full case identity, the original
    signature and that build's unverified references. It must return positive,
    negative (signature absent), or unknown. Production verification is not
    implemented by this offline example.
    """
    if not signature:
        raise ValueError("A verbatim nonempty signature is required")
    if source == follow_up or not {source, follow_up} <= set(build_ids):
        raise ValueError("Distinct selected source and follow-up builds are required")
    result = provider.question(
        build_ids, identity, None if native_assertion else signature)
    observed = sorted({build for group in result["groups"]
                       for build in group["matchingBuildIds"]})
    verdicts = {"positive": [], "negative": [], "unknown": []}
    for build in sorted(build_ids):
        references = [reference for group in result["groups"]
                      for reference in group["references"]
                      if reference["buildId"] == build]
        verdict = verify_original(build, identity, signature, references)
        if verdict not in verdicts:
            raise ValueError("Original evidence must be positive, negative, or unknown")
        verdicts[verdict].append(build)
    return {
        "queryCompleted": True,
        "dataCompleteness": "unknown",
        "indexedCandidates": observed,
        "notObserved": result["notObservedBuildIds"],
        "originalEvidence": verdicts,
        "preMatcherDecision": decision(
            source, follow_up, verdicts["positive"],
            verdicts["negative"], verdicts["unknown"]),
    }
