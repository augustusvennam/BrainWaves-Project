# Estimated state heuristic

This is an application demonstration heuristic, not a probability model, validated confidence, medical diagnosis, or accurate emotion recognition. No measured accuracy is claimed. Cortex performance metrics are themselves vendor estimates. Attention remains a separate vendor measurement and contributes to none of these scores.

Require active finite `rel`, `eng`, `exc`, `str` values in [0,1], fresh acquisition timestamps, connected headset, fresh contact/EEG quality, contact and EEG overall >=60 by default, and sample-rate quality >=0.9. Missing inputs return **Insufficient data**. Suitable inputs without a clear winner return **Unknown**. The quality gate is deliberately conservative and does not constitute artifact rejection.

For each required metric k, baseline B[k] is the arithmetic mean of valid baseline samples. Baseline requires at least 10 samples spanning at least 30 seconds, with no gap over the configured freshness bound. Assessment begins with new samples. At acquisition timestamp t, average valid assessment samples in [t−15,t] to obtain M[k]. Changes d[k] = M[k]−B[k]. The smoothing window uses timestamps, not browser frame counts or an assumed stream rate; means are sample-weighted within that time window.

| Heuristic score | Formula |
|---|---|
| Relaxed | d[rel] − d[str] |
| Engaged | d[eng] − 0.5 d[str] |
| Excited | d[exc] − 0.5 d[str] |
| Stressed | d[str] − d[rel] |

A named winner needs score >=0.10 and a margin >=0.05 over the runner-up. Otherwise the candidate is Unknown. Candidate must persist for >=5 seconds of valid timestamped observations before display/review. Invalid quality/metrics interrupts candidate persistence. Assessment requires at least 10 valid samples spanning >=20 seconds before review; time alone never succeeds. Long gaps restart coverage. Once reviewed, the estimate is a result for that assessment; it is not continuously recomputed. Freshness/quality failure masks it as Insufficient data and prevents robot confirmation. End/reset clears it.

Thresholds and weights are design choices without validation. Metrics are correlated; movements, blinks, fitting, fatigue, task context and individual differences may confound them. A participant baseline does not establish emotion or remove these confounds. Small score differences have no calibrated interpretation. The four labels may fail to reflect a participant's experience, and Unknown/Insufficient data should remain common acceptable outcomes.

## Voluntary hardware evaluation

Obtain consent, explain that labels may be wrong, allow stopping without consequence, and avoid clinical or stressful provocation. Record acquisition/device/software versions, stream rates, quality thresholds and heuristic configuration. Use rest and ordinary voluntary tasks; collect independent participant self-reports at marked timestamps before showing estimates. Report exclusions, stale/invalid intervals, abstention rate, timestamp alignment, confusion counts and sample size. Separate development participants from later evaluation participants before changing thresholds. Compare to simple baselines and document the procedure and uncertainty. Do not claim accuracy until actual measured results exist. Self-report is subjective evidence, not ground truth for a clinical diagnosis.
