# eval_verify summary

## Headline aggregates

| experiment | triple | aligned | ind | prop | literal | ast |
|---|---|---|---|---|---|---|
| extraction (n=27) | 0.975 | 0.959 | 0.995 | 0.992 | 0.968 | — |
| generation (n=27) | — | — | — | — | — | 0.858 (parse 1.000) |
| crossfw (n=54) | 0.351 | 0.566 | 0.768 | 0.737 | 0.414 | 0.578 |

## Cross-fw per-direction means

| src -> tgt | triple | aligned | ind | prop | literal | ast |
|---|---|---|---|---|---|---|
| crewai -> langgraph | 0.285 | 0.541 | 0.781 | 0.701 | 0.482 | 0.541 |
| crewai -> autogen | 0.479 | 0.719 | 0.928 | 0.926 | 0.550 | 0.830 |
| langgraph -> crewai | 0.227 | 0.572 | 0.831 | 0.834 | 0.382 | 0.520 |
| langgraph -> autogen | 0.512 | 0.750 | 0.913 | 0.900 | 0.595 | 0.801 |
| autogen -> crewai | 0.308 | 0.447 | 0.624 | 0.627 | 0.247 | 0.405 |
| autogen -> langgraph | 0.294 | 0.367 | 0.533 | 0.434 | 0.230 | 0.370 |
