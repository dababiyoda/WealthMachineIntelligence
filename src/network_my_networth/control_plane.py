"""Evidence-gated control plane for NetworkMyNetworth.

The agent loops produce hypotheses and recommendations. They do not possess
execution authority. This module converts those recommendations into a
stage-gated operator decision with explicit proof, budget, and stop criteria.

The control plane is intentionally deterministic and side-effect free. It may