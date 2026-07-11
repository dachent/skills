# Selective CodeQL trigger overhead

Measured July 11, 2026 with 15 runs per case. CodeQL itself is not invoked in the default path.

| Modules | Fixture | Cold delta | Warm delta | Default-policy median |
| ---: | --- | ---: | ---: | ---: |
| 12 | structural | -8.22% | +0.86% | 0.575 ms |
| 12 | sink-heavy | +0.89% | -7.90% | 0.592 ms |
| 122 | structural | +3.69% | +0.54% | 0.557 ms |
| 122 | sink-heavy | +8.56% | +2.75% | 0.785 ms |
| 602 | structural | -4.34% | -2.04% | 0.665 ms |
| 602 | sink-heavy | +0.36% | +6.75% | 1.092 ms |

Negative deltas are measurement noise. Maximum positive median overhead was 8.56% cold and 6.75% warm, below the 10% gate. The largest default-policy median was 1.092 ms, below the 5 ms gate.

```text
python scripts/benchmark_codeql_overhead.py --runs 15
```
