# Market Intelligence & Decision Engine

This document describes the local implementation of the Market Intelligence Agent, the Decision Engine and the accompanying Knowledge Graph Connector. These components expand upon the plans outlined in the original market-intelligence-agent.md plan by providing hardened code and a clear execution model.

## Components

### Knowledge Graph Connector (`src/core/knowledge_graph_connector.py`)

The **KnowledgeGraphConnector** synchronises data between the in‑memory knowledge graph and the persistent SQL database. Its key responsibilities include:

- Updating venture status and metrics both in the graph and the database.
- Persisting AI outputs such as sentiment analysis, LSTM predictions, forecasts and risk assessments.
- Retrieving competitor information and attaching new opportunities to ventures.
- Providing a unified `notify_role()` interface that delegates to the `src/utils/notifications.py` module or simply logs notifications in environments where messaging systems are unavailable.

### Decision Engine (`src/services/decision_engine.py`)

The **DecisionEngine** loads rules from a JSON file (for example `automation/sample-rules.json`) and evaluates them against venture metrics. Each rule is defined by a condition tree (supporting nested `AND`/`OR` logic) and an action specification. Supported action types include:

- `update_venture_status`: sets a new venture status and optionally notifies roles.
- `trigger_review`: assigns a review task to a specialist role.
- `optimize_funnel`: notifies marketing roles to optimise key e‑commerce processes.
- `compliance_review`: alerts compliance and legal teams to deficiencies in regulatory scores.

The engine is decoupled from FastAPI and can be invoked directly in background workers or tests.

### Market Monitor (`src/services/market_monitor.py`)

The **MarketMonitor** provides a concrete example of how to connect data collection with the decision engine. It periodically iterates over all ventures (using the database if available or falling back to the knowledge graph), collects simulated metrics, persists them via the connector and invokes the decision engine. In production the metric collection method would be replaced with calls to real data sources.

## Usage

1. Ensure your environment is configured with a valid `DATABASE_URL` if you want to persist data; otherwise the connector will operate entirely in memory.
2. Define your rules in a JSON file. A sample ruleset is provided in `automation/sample-rules.json` and includes examples for SaaS and e‑commerce ventures as well as compliance and risk alerts.
3. Initialise the decision engine:

   ```python
   from src.services.decision_engine import DecisionEngine
   engine = DecisionEngine.from_json_file('automation/sample-rules.json')
   outcomes = engine.evaluate('venture‑123', 'SaaSVenture', {
       'market_volatility': 0.9,
       'risk_profile': 'High',
       'monthly_churn_rate': 0.06,
       'mrr_growth_rate': 0.05,
   })
   ```

4. To run continuous monitoring use the market monitor:

   ```bash
   python -m src.services.market_monitor --rules automation/sample-rules.json --interval 60
   ```

5. Integrate the connector into your FastAPI routes or background tasks to ensure that updates from AI agents are persisted consistently.

## Extensibility

- **Additional Rule Types**: To add new actions simply extend the `_execute_action` method in `decision_engine.py`.
- **Complex Conditions**: The condition parser can be extended to support range checks, regex matching or custom evaluators by enhancing `ConditionNode.from_dict`.
- **Messaging Integrations**: Replace the implementation in `src/utils/notifications.py` with calls to email, Slack or other messaging APIs.
- **Database Schema**: For forecasts or additional AI outputs add columns or new tables to `src/database/models.py` and extend the connector accordingly.

## Conclusion

The Market Intelligence agent described here provides a full stack implementation of the plans outlined in the repository. By combining a rule engine with a knowledge graph connector and a monitoring service, ventures can be continuously evaluated and appropriate actions automatically orchestrated.
