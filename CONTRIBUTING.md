# Contributing

Describe the problem, platform, package version, display scaling and VDI client
when filing an issue. Do not include private clipboard contents, credentials or
screenshots containing sensitive documents.

For changes, keep Windows and Linux behavior documented separately. Add a focused
regression test for input, image-pixel or lifecycle bugs; run the relevant checks
in docs/BUILDING.md. Use an isolated test desktop for clipboard/input tests.
Do not commit generated executables, local configuration or API keys.

Release notes should state the actual build platform, compatibility limits and
checks performed. Attach executable archives to Releases with SHA-256 checksums.
