# Error-taxonomy annotation rubric

Used for the manual analysis of the 916 gap cases (GPT-4o and Qwen-7B; Section 8
of the paper). A gap case is an example where every Pass-1 piece question was
answered correctly but the composed Pass-2 answer was wrong. One author labeled
all 916 cases; a second author independently labeled 200 (21.8%), with Cohen's
kappa = 0.74. Categories are mutually exclusive; assign the single category that
best explains the composed failure.

| Category | Assign when | Typical evidence |
|---|---|---|
| **Partial composition** | The composed answer uses some but not all of the pieces the model recovered in Pass 1. | A required join, condition, aggregation, or premise recovered in Pass 1 is missing from the composed answer. |
| **Correct structure, wrong execution** | The composed answer uses the right template over the right pieces but carries it out incorrectly. | Arithmetic or boundary error with the right operations; correct query template with a wrong constant; correct logical form with a wrong final label. |
| **Hallucinated structure** | The composed answer introduces structural relations that neither the input nor the recovered pieces support. | Joins to tables the question never references; invented conditions; premises not in the input. |
| **Wrong structure selection** | The pieces are correct but the composed answer is built on the wrong template. | Nested query where a simple selection was needed (or vice versa); wrong composition path through the schema; wrong operation order for a correctly extracted set of quantities. |

Tie-breaking: if a case shows both a missing piece and an invented relation,
label by the error that determines the wrong final answer. Code cases were
labeled under the plan-consistency protocol (paper Section 3.4): "structure"
there refers to the control-flow plan the model itself stated in Pass 1.

Worked examples of each category, taken verbatim from the prediction logs, are
in Appendix G of the paper. Per-example labels for the 916 cases are held in
the authors' annotation spreadsheet and are not part of this release.
