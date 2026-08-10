# LLM baseline (parallel corpus)

Provider: openai  Model: gpt-5-mini

## Per-cell

| family | framework | triple | aligned | ind | prop | literal | err |
|---|---|---|---|---|---|---|---|
| joke | crewai | 0.000 | 0.402 | 0.835 | 0.617 | 0.500 | |
| joke | langgraph | 0.000 | 0.307 | 0.640 | 0.274 | 0.407 | |
| joke | autogen | 0.000 | 0.341 | 0.683 | 0.511 | 0.320 | |
| code-review | crewai | 0.159 | 0.470 | 0.735 | 0.556 | 0.604 | |
| code-review | langgraph | 0.000 | 0.301 | 0.655 | 0.596 | 0.333 | |
| code-review | autogen | 0.000 | 0.315 | 0.683 | 0.551 | 0.179 | |
| tech-blog | crewai | 0.131 | 0.352 | 0.706 | 0.612 | 0.565 | |
| tech-blog | langgraph | 0.000 | 0.341 | 0.635 | 0.536 | 0.370 | |
| tech-blog | autogen | 0.000 | 0.344 | 0.636 | 0.524 | 0.320 | |
| meeting-assistant-flow | crewai | 0.000 | 0.265 | 0.525 | 0.388 | 0.459 | |
| meeting-assistant-flow | langgraph | — | — | — | — | — | parse failed |
| meeting-assistant-flow | autogen | 0.000 | 0.278 | 0.743 | 0.500 | 0.077 | |
| travel-planning | crewai | 0.000 | 0.461 | 0.883 | 0.629 | 0.618 | |
| travel-planning | langgraph | 0.000 | 0.367 | 0.716 | 0.554 | 0.325 | |
| travel-planning | autogen | 0.000 | 0.375 | 0.772 | 0.549 | 0.438 | |
| maths | crewai | 0.000 | 0.356 | 0.737 | 0.637 | 0.447 | |
| maths | langgraph | 0.000 | 0.223 | 0.622 | 0.455 | 0.267 | |
| maths | autogen | 0.000 | 0.270 | 0.649 | 0.386 | 0.259 | |

## Aggregates

| group | triple | aligned | ind | prop | literal |
|---|---|---|---|---|---|
| crewai | 0.048 | 0.384 | 0.737 | 0.573 | 0.532 |
| langgraph | 0.000 | 0.308 | 0.654 | 0.483 | 0.341 |
| autogen | 0.000 | 0.321 | 0.694 | 0.503 | 0.265 |
| joke | 0.000 | 0.350 | 0.719 | 0.467 | 0.409 |
| code-review | 0.053 | 0.362 | 0.691 | 0.567 | 0.372 |
| tech-blog | 0.044 | 0.346 | 0.659 | 0.557 | 0.419 |
| meeting-assistant-flow | 0.000 | 0.272 | 0.634 | 0.444 | 0.268 |
| travel-planning | 0.000 | 0.401 | 0.790 | 0.577 | 0.460 |
| maths | 0.000 | 0.283 | 0.669 | 0.492 | 0.324 |

**Mean** triple=0.017  aligned=0.339  ind=0.697  prop=0.522  lit=0.382
