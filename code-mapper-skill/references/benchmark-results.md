# Runtime benchmark

## Method

The complete `blast_radius.py` CLI was measured as a subprocess against the unchanged base implementation and the enhanced implementation.

- Python 3.13.5
- Linux 4.4.0 x86_64 container
- identical fixture and interpreter for each comparison
- baseline and candidate order alternated to reduce drift
- stdout discarded
- default module-only and module-plus-Jedi modes tested
- cold mode cleared each checkout's code-mapper caches before every measured run

The fixtures contained 11, 123, and 603 Python modules plus OpenAPI, AsyncAPI, GraphQL, Protobuf, and Backstage files.

## Release measurements

### Warm, 123-module fixture, module-only

- baseline median: 1.636 s
- enhanced median: 1.703 s
- delta: +0.067 s / +4.08%
- gate: <=10% and <=0.25 s
- result: pass

### Cold, 603-module fixture, module-only

- baseline median: 1.411 s
- enhanced median: 1.532 s
- delta: +0.121 s / +8.59%
- gate: <=20% and <=0.25 s
- result: pass

### Warm, 123-module fixture, Jedi function references

- baseline median: 2.568 s
- enhanced median: 2.664 s
- delta: +0.097 s / +3.76%
- gate: <=10% and <=0.25 s
- result: pass

Additional five-run checks across the 11-, 123-, and 603-module fixtures placed warm median change between approximately -1% and +3%. The direct warm relationship layer on the 608-candidate-file fixture measured approximately 70 ms after the aggregate-cache optimization.

These numbers are environment-specific. Re-run `scripts/benchmark_runtime.py` on the target workstation before tightening the thresholds.
