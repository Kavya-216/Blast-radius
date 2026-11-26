# ML Design

No ML risk model is trained or deployed. The prediction endpoint returns `not_available` until a valid labelled dataset and temporal evaluation exist.

A future implementation will use scikit-learn and features derived from changed files, symbols, tests, graph degree, diff size, history, and incident links. Labels will be temporally defined from observed regressions. Precision, recall, F1, PR-AUC, and calibration will be reported. Accuracy alone is not sufficient for rare incidents.
