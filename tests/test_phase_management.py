from src.services.phase_management import PhaseGate, PhaseManager


def test_phase_manager_promotes_and_regresses_based_on_metrics() -> None:
    manager = PhaseManager()

    strong_metrics = {"opportunity_score": 0.75, "expected_roi": 0.8}
    decision1 = manager.record_cycle("venture-1", strong_metrics, risk_level="Low")
    assert decision1.decision == "promote"
    assert decision1.next_phase == "Phase 2: Validate"

    stronger_metrics = {"opportunity_score": 0.8, "expected_roi": 0.9}
    decision2 = manager.record_cycle("venture-1", stronger_metrics, risk_level="Ultra Low")
    assert decision2.decision in {"promote", "stabilize"}
    assert manager.portfolio_summary()["venture-1"]["phase"] in {"Phase 2: Validate", "Phase 3: Scale"}

    risky_metrics = {"opportunity_score": 0.4, "expected_roi": 0.2}
    decision3 = manager.record_cycle("venture-1", risky_metrics, risk_level="Very High")
    assert decision3.decision in {"regress", "stabilize"}
    assert manager.portfolio_summary()["venture-1"]["phase"] in {"Phase 1: Explore", "Phase 2: Validate"}


def test_custom_phase_gate_can_lower_thresholds() -> None:
    experimental_phase = PhaseGate(
        name="Phase 0: Incubate",
        minimum_opportunity_score=0.2,
        minimum_expected_roi=0.1,
        maximum_risk_level="Very High",
        reinvestment_rate=0.1,
        description="Tiny experiments to spin up the loop quickly",
    )
    manager = PhaseManager(phases=[experimental_phase] + manager_phases())

    decision = manager.record_cycle(
        "venture-2",
        metrics={"opportunity_score": 0.25, "expected_roi": 0.15},
        risk_level="High",
    )
    assert decision.decision in {"stabilize", "promote"}
    assert decision.reinvestment_rate == experimental_phase.reinvestment_rate


def manager_phases():
    return [
        PhaseGate(
            name="Phase 1: Explore",
            minimum_opportunity_score=0.45,
            minimum_expected_roi=0.25,
            maximum_risk_level="High",
            reinvestment_rate=0.2,
            description="Small, low-risk experiments",
        ),
        PhaseGate(
            name="Phase 2: Validate",
            minimum_opportunity_score=0.6,
            minimum_expected_roi=0.45,
            maximum_risk_level="Moderate",
            reinvestment_rate=0.35,
            description="Validated bets ready for structured pilots",
        ),
        PhaseGate(
            name="Phase 3: Scale",
            minimum_opportunity_score=0.7,
            minimum_expected_roi=0.7,
            maximum_risk_level="Low",
            reinvestment_rate=0.5,
            description="Scaling portfolio with disciplined reinvestment",
        ),
    ]
