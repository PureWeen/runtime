# Licensed to the .NET Foundation under one or more agreements.
# The .NET Foundation licenses this file to you under the MIT license.

"""Invented identities, build IDs and console text, not historical captures."""

BUILD_IDS = [700001, 700002, 700003]
SIGNATURE = "Synthetic assertion: expected false"
NATIVE_SIGNATURE = "Synthetic native assertion: missing profile flag"


def identity(options="None"):
    return {
        "BuildDefinitionId": 138,
        "WorkItemFriendlyName": "Example.FileSystem.Tests",
        "QueueName": "example-windows-x86",
        "TestRunName": "example-release-x86-jitstress2_tiered",
        "TestName": "Example.FileTests.Dispose",
        "Arguments": f"bufferSize: 1, options: {options}",
        "ArgumentHash": f"synthetic-{options}",
    }


def native_identity():
    return {
        **identity(),
        "TestName": "Example.NativeCrash",
        "Arguments": "",
        "ArgumentHash": "",
    }


def row(build, case, message=SIGNATURE):
    return {
        **case,
        "BuildId": build,
        "Outcome": "Failed",
        "TestRunId": 900001,
        "TestResultId": 42,
        "JobName": "00000000-0000-4000-8000-000000000001",
        "WorkItemId": 7,
        "WorkItemName": "00000000-0000-4000-8000-000000000002",
        "Message": message,
    }


def fixture():
    rows = [row(build, identity(options))
            for options in ("None", "Asynchronous") for build in BUILD_IDS[:2]]
    rows.append(row(700002, native_identity(), "Synthetic process exited"))
    # Each near match would create a false follow-up positive if its field were lost.
    decoys = {
        "BuildDefinitionId": 109,
        "QueueName": "example-linux-x64",
        "TestRunName": "example-release-x86-jitstress1",
        "WorkItemFriendlyName": "Example.Other.Tests",
        "TestName": "Example.FileTests.Other",
        "Arguments": "bufferSize: 2, options: None",
        "ArgumentHash": "synthetic-other",
    }
    rows.extend(row(700003, {**identity(), field: value})
                for field, value in decoys.items())
    rows.append({**row(700003, identity()), "Outcome": "Passed"})
    rows.append(row(700003, identity(), SIGNATURE.lower()))
    return {
        "builds": [
            {"id": build, "repository": {"id": "dotnet/runtime"},
             "project": {"name": "public"}, "definition": {"id": 138}}
            for build in BUILD_IDS
        ],
        "rows": rows,
    }


def originals(case, signature, positives, negatives=()):
    """Stand-in for already verified, complete original result/console evidence."""
    records = {
        build: {"identity": dict(case), "console": signature, "complete": True}
        for build in positives
    }
    records.update({
        build: {"identity": dict(case), "console": "Synthetic completed inspection",
                "complete": True}
        for build in negatives
    })
    return records


def verifier(records):
    def verify(build, case, signature, references):
        record = records.get(build)
        # Aliased parent IDs never establish which parameter case was inspected.
        if (record is None or record["identity"] != case
                or not record["complete"]):
            return "unknown"
        return "positive" if signature in record["console"] else "negative"
    return verify
