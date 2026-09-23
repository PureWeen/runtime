# Runtime exact-signature history review example

This is a public-safe packaging of a closed, bounded REST history spike, not
a scanner replacement or production rollout. Only this experiment directory
is added. No workflows, shipping code, settings, dependency manifests or issue
policy change. The example needs Python 3.10+ and its standard library.

## Offline use

Use the **one canonical client, contract and fixture service** in the companion
[PureWeen/aspnetcore#75](https://github.com/PureWeen/aspnetcore/pull/75) review
change, under `experiments/ci-history-rest`, pinned to commit
[`73fa66c082718e44624f5e949ac4583096d8525c`](https://github.com/PureWeen/aspnetcore/tree/73fa66c082718e44624f5e949ac4583096d8525c/experiments/ci-history-rest).
There is no copied service or second contract here. Prepare a separate ASP.NET
checkout at that exact commit before going offline, not at a moving PR branch.
Alternatively, download the
[pinned source archive](https://github.com/PureWeen/aspnetcore/archive/73fa66c082718e44624f5e949ac4583096d8525c.tar.gz)
while online and extract its top-level directory to a new sibling `../aspnetcore`
directory. Do not overwrite an existing checkout. Given both source trees side
by side, run from this runtime checkout:

```sh
SHARED=../aspnetcore/experiments/ci-history-rest
python3 -B experiments/ci-history-rest/demo.py --shared-root "$SHARED"
python3 -B experiments/ci-history-rest/test_demo.py --shared-root "$SHARED"
```

`--shared-root` explicitly selects that checkout for Python imports. Neither
command fetches source data, logs in, installs anything or needs organizational
credentials. Each fixture context starts an actual loopback HTTP server with
an ephemeral local token and tears down its listener and token. The dependency
must already be checked out before offline execution.

The JSON demo shows two parameter cases sharing the same parent references
without merging their identities; a missing indexed follow-up signature;
a native crash placeholder with and without synthetic console evidence; and
infrastructure without tests. Three service faults produce explicitly incomplete
answers, not empty successes. The tests also exercise each exact identity field,
case-sensitive signatures, nullable versus empty arguments, scope rejection,
all-unverified-build enrichment and owned-resource cleanup.

All fixture IDs, names and console text are invented. `synthetic_fixture.py`
stands in for independently verified original evidence; it is not an
implementation of the production console parser, identity verification or
source completeness. Its `negative` verdict means signature absent from the
complete inspected original evidence, **never test passed**.

## Proposed integration boundary

The retained prototype's `runtime_http.request_for`, `HttpProvider.question`
and `runtime_history.decision` are reduced here to their focused offline seam.
The provider uses the canonical `HistoryClient.query` over
`POST /v1/repositories/dotnet/runtime/test-history/query`. The original caller
still supplies the selected builds, source and follow-up. The common client
validates membership, exact predicates and unverified reference semantics;
runtime's adapter preserves pipeline, workitem, queue, stress/run label,
parameter text and opaque argument hash. No parameter hash is recomputed.

| Existing production location | What stays in runtime |
| --- | --- |
| [Scanner Step 2](../../.github/workflows/ci-failure-scan.md#step-2--walk-pipelines) | Pipeline list, main/completed build selection, time windows, source/follow-up selection and widening. |
| [Scanner Step 3.5](../../.github/workflows/ci-failure-scan.md#step-35--follow-up-build-presence-gate) | Original result/console verification, signature absence and follow-up interpretation. |
| [Scanner Step 4](../../.github/workflows/ci-failure-scan.md#step-4--per-signature-walk) | Queue/stress-aware dedup, Build Analysis and existing-KBE matching. |
| [Scanner Step 5](../../.github/workflows/ci-failure-scan.md#step-5--decide-and-emit) | Severity, required-gate escalation, blocking exceptions, match-count checks and issue/publication policy. |
| [Shared KBE instructions](../../.github/workflows/shared/create-kbe.instructions.md) | Verbatim original evidence, native assertion handling and final body verification. |
| [Fix workflow](../../.github/workflows/ci-failure-fix.md) | All later mitigation and owner follow-up. |

These links identify a proposed provider seam in the existing prompt-driven
flow, not a newly wired production Python call site. The example's historical
pre-matcher gate is deliberately not the full current scanner policy.

Every unverified selected build still reaches original enrichment, including
indexed candidates. Aliased run/result IDs are references, not case keys;
`workItemId` remains numeric and `helixJobId` comes from source `JobName`.
Native assertions omit `errorContains` because the indexed crash placeholder
does not contain the assertion. Only original console evidence establishes it.
Query completion does not establish complete ingestion, attempts, currentness,
execution counts, passage or eligibility to unquarantine.

The [anonymous-only scanner rule](../../.github/workflows/ci-failure-scan.md#hard-rules--non-negotiable)
still needs a separately approved adoption path. Successful locally
authenticated queries did not authorize changing that rule.

## Retained evidence versus this new demo

The closed runtime comparison preserved five exact-signature questions over
37 distinct builds: 36 selected plus one older XML comparison build. Original
positive, signature-absent and unknown sets were preserved. The seal checked
1,486 fingerprint entries plus a separate seal. Native assertion classification
required original console evidence; infrastructure with no tests stayed unknown.
These are curated conclusions from retained evidence, **not a reexecution by
this PR**. Raw captures, private notes, source receipts and machine paths are
intentionally not published here.

At cross-repository closure, the four final consumer versions passed one whole
retained-source HTTP replay. Live evidence consists of separately successful
components, not a successful final whole-live invocation: both source-503
failures remain failures. SDK found six of seven indexed memberships but kept
eight identical dossiers and the same 233 logical GETs / 52 unique requests
after synthetic suppression. That integration eliminated zero demonstrated
source work. No universal cost reduction or full collector substitution follows.

The historical prototype's fixture-only source-receipt path/hash bookkeeping
gap remains unsupported. This new synthetic harness does not repair those
receipts and its tests are not the historical 333-request / 338-check run.
Production hosting, authentication, SLOs and complete ingestion remain unproved.
The approved contract SHA-256 is
`a3f63bb1d6d11455ca7fe569431051cfac88bd0427752247b5cd8962e9e7fe7e`.

## Owner review questions

Is this exact-signature history seam useful while original verification stays
mandatory? What approved authentication path could satisfy the anonymous-only
workflow? What source identity and ingestion guarantees would be required before
removing any existing retrieval or changing issue policy?

> [!NOTE]
> This review example and summary were prepared with GitHub Copilot.
