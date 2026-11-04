# Release and plugin bundle workflow (not executed in Round 4)

Round 4 source is under feat/round4-layer-aware-painting, development version
0.5.0.dev0. Prior Round 1/2/3 features have documented acceptance, but NEW
Round 4 capabilities are not runtime verified. Do not claim a production
release based only on a source commit.

## Future manual steps

1. Confirm exactly one official Krita build, its process ownership, user
   profile and shared resource directory. Make backups of existing pykrita.
2. After separate authorization, run offline static checks and pytest.
3. Review source and execute scripts/build_plugin_bundle.py --output
   dist/krita-agent-0.5.0.dev0-pykrita.zip. This only builds an archive.
4. Inspect ZIP paths, SHA256 and licenses. Archive entries install below
   the user pykrita directory (not the Krita executable tree).
5. Deploy via scripts/install_plugin.py dry-run first, then explicit --apply.
   Use --replace only after backup inspection and manual approval.
6. Enable Python Plugin Manager, restart *test-owned* Krita; verify Qt5 and
   Qt6 separately. Back up and restore prior plugin if issues arise.
7. Execute docs/ROUND4-ACCEPTANCE.md; repair failures and generate real
   REPORT-011 + sanitized evidence before PR merge.
8. Keep GitHub Actions workflow_dispatch only until user explicitly permits
   automatic PR checks.

Safety: no automatic third-party plugin installation; no silent overwrite
of preexisting brushes or user artwork; no database or telemetry upload.
