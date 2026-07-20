# WealthMachine Foundry Underwriting Adapter

WealthMachine evaluates an OpportunityPacket and preserves competing bull, bear, fraud, incumbent-response, adoption-friction, do-nothing, and opportunity-cost cases. Its assessment remains a recommendation.

`src/services/foundry_adapter.py` combines a validated packet, validated assessment, and separately verified commercial foundation into a proposal-only Foundry underwriting envelope.

Readiness requires:

- a `go` verdict;
- no unresolved high-severity case against the opportunity;
- completed legal review;
- named buyer, beneficiary, pain owner, and budget owner;
- recurring transaction and trapped value;
- accepted artifact and external consequence;
- lawful path and evidence.

A high score cannot erase a blocking case. Every output retains:

- `requires_human_approval: true`;
- `execution_authority: none`;
- source packet and assessment digests;
- explicit missing fields and blocking reasons.

## Intended flow

```text
OpportunityPacket
-> adversarial VentureAssessment
-> verified commercial foundation
-> Foundry underwriting envelope
-> canonical UNIIMENTE Foundry intake
```

The adapter does not create a capability grant, launch a venture, contact a buyer, spend money, or alter the Kernel. Those effects remain subject to human authorization and the canonical Consequence Gate.
