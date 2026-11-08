# Usage reference

Python 3.9+, standard library only. Work in a local checkout of this public
repository; the README clone command requires authenticated gh access. No package installation is needed.
Read [SKILL.md](../SKILL.md) for the agent-led profile, polishing and edit-learning
workflow, and [DESIGN.md](DESIGN.md) for implementation detail. The README example
runs the pipeline; with an empty temporary home it has no personal messages to
process. It is not evidence that every supported adapter works on current data.

The pipeline collects local messages, denoises them, discovers sensitive entities,
filters text, computes statistics, builds a profile and checks the profile for
leaks. Without --no-llm the agent may review entity candidates. With --no-llm,
unresolved review candidates are redacted. Inspect the outputs before use.

run.py accepts --reviewed, --no-llm, --include-suspect and --profile-out. Profiles
normally live in ~/.style-polish/. check.py accepts a draft plus --profile, or
--stats, or --leak-gate. A passing leak gate is evidence for the configured
patterns/entities, not a guarantee that no private information remains.

The hero was generated from an actual check.py --leak-gate run against
examples/spoken.example.md in a disposable copy. That profile is synthetic.
No real personal conversation was read for this README's illustration.

Run all tests with `python3 -m unittest discover -s tests -v`. Tests use disposable
homes and synthetic Claude Code/Codex sessions, exercise empty inputs and privacy
filtering, generate a profile, and verify passing/failing leak gates. GitHub Actions
runs this suite and the example leak gate on Python 3.9 and 3.13.

When collection, denoising or filtering leaves zero usable messages, `run.py`
prints a setup/filter hint and exits successfully without writing a profile.
Existing profiles are preserved. This is a no-data outcome, not a completed build.

To regenerate images use the readme-from-code skill's art command, targeting
this repository and docs/readme/art.json. Capture inputs and source evidence are
kept alongside the spec. The workflow image is an illustration.
