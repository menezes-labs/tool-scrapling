# Used PC Salvage Scout — status

Updated: 2026-10-04 UTC

## Goal

Long-running, resumable Scrapling campaign to find cheap used or defective donor PCs/components
that can materially upgrade an i3-8100/H310-class DDR4 desktop.

## Implemented

- deterministic BRL price parsing;
- service-ad rejection;
- hardware signal extraction and upgrade-value scoring;
- defect-risk classification;
- OLX and Mercado Livre listing URL discovery/deduplication;
- resumable Scrapling Spider with checkpoint directory;
- robots.txt compliance, per-domain concurrency limits, download delay and AutoThrottle;
- ranked JSON + Markdown reports;
- CodeBuild buildspec with focused test gate before crawling.

## Verification

- local RED: focused tests failed before implementation because campaign modules did not exist;
- local GREEN: 8/8 focused tests passed after implementation;
- GitHub-hosted smoke run 37165207504 failed before any job step executed, so it is not counted as test evidence.

## CodeBuild control-plane blocker

A discovery workflow was run from `menezesx2k26-byte/ops-gabriel-ops` branch
`ops/scrapling-codebuild-scout-20261003`.

Run: `37164673520`.

The validated desktop runner `DESKTOP-L6CITUI` executed the job, but AWS CLI authentication had expired:

`aws: [ERROR]: Your session has expired. Please reauthenticate using 'aws login'.`

No CodeBuild project was started or modified. No AWS project metadata could be inventoried until authentication is refreshed.

## Default crawl envelope

- max listing price: R$ 1,200;
- max search-result pages per seed: 10;
- max global concurrency: 6;
- max per-domain concurrency: 2;
- robots.txt: obeyed;
- AutoThrottle: enabled;
- checkpoint interval: 120 seconds.

These limits are environment-variable overrides in the buildspec/runner.
