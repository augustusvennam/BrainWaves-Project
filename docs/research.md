# Cortex integration research

The current implementation and verified source references are maintained in
[REQUIREMENTS.md](REQUIREMENTS.md). The old notes have been replaced because they
listed an unsupported remote endpoint, fixed metric ordering, and demo behavior
that did not match the actual Python/Android protocol.

The implemented connection is local `wss://localhost:6868`. The Basic integration
uses `met`, `pow`, `dev`, and `eq`; decoding follows subscription column metadata.
Mood estimates are heuristic and require fresh usable data. No mental-command
profile or raw EEG access is required for this milestone.
