# Knowledge Graph Queries Documentation

## Overview
This document outlines the structure and usage of knowledge graph queries within the WealthMachineOntology_DigitalAI framework. The queries are designed to extract meaningful insights from our ontological model of digital ventures, roles, and AI processes.

Knowledge graph queries are essential for:
1. Real-time decision support (e.g., checking venture compliance status)
2. Resource allocation optimization (e.g., role assignments)
3. Risk assessment and monitoring
4. Performance tracking and optimization
5. Compliance verification and reporting

## Query Structure

### Basic Components
1. **Node Types**
   - Ventures (SaaSVenture, EcommerceVenture, ContentPlatform)
   - Roles (EmergingTechSpecialist, StrategicMarketTrendAnalyst, etc.)
   - Processes (AIProcess)
   - Profiles (RiskProfile, MarketSegment)

2. **Relationships**
   - contributesTo (Role → DigitalVenture)
   - automates (AIProcess → Role)
   - implementsAI (DigitalVenture → AIProcess)
   - targets (DigitalVenture → MarketSegment)

### Query Parameters
- `phase`: Current development phase of ventures
- `venture_type`: Type of digital venture (SaaS, Ecommerce, Content)
- `ai_module`: Boolean flag for AI integration
- `role_id`: Identifier for specific roles
- `process_type`: Type of AI process

## Query Types

### 1. Basic Retrieval Queries
- List all active digital ventures
- Retrieve all roles in the system
- Get all AI processes
Example:
```yaml
# List all ventures
match:
  venture:
    type: "DigitalVenture"
return:
  - venture.id
  - venture.name
  - venture.business_model
```

### 2. Conditional/Filter Queries
- Find ventures in specific phases
- Identify ventures with ML requirements
- List roles with specific AI capabilities
Example:
```yaml
# Find Phase3 ventures with ML models
match:
  venture:
    type: "DigitalVenture"
    properties:
      current_phase: "Phase3"
      requiresMLModel: true
return:
  - venture.id
  - venture.name
  - venture.automationLevel
```

### 3. Relationship Traversal Queries
- Map role collaborations across ventures
- Track AI process implementations
- Analyze venture-market relationships
Example:
```yaml
# Find all roles and processes for a venture
match:
  venture:
    type: "DigitalVenture"
    id: "$venture_id"
  roles:
    relationship: "contributesTo"
    target: "venture"
  processes:
    relationship: "implementsAI"
    source: "venture"
return:
  - roles.*
  - processes.*
```

## Ontology Schema Integration
### Direct Mappings to ontology-schema.yaml
1. **Class Mappings**
   ```yaml
   # From ontology-schema.yaml
   classes:
     DigitalVenture:
       properties:
         - usesAIModule
         - requiresMLModel

   # Query Implementation
   match:
     venture:
       type: "DigitalVenture"
       properties:
         usesAIModule: true
   ```

2. **Relationship Mappings**
   ```yaml
   # From ontology-schema.yaml
   relationships:
     - name: implementsAI
       source: DigitalVenture
       target: AIProcess

   # Query Usage
   match:
     venture:
       type: "DigitalVenture"
     process:
       type: "AIProcess"
       relationship: "implementsAI"
   ```

### Property Validation
Queries automatically validate against schema constraints:
- Enum validations (e.g., business_model types)
- Cardinality rules (e.g., one-to-many relationships)
- Required properties based on phase

## Future Graph Database Integration
### Implementation Steps

1. **Graph Database Selection**
   - Neo4j: For enterprise-scale graph operations
   - Apache Jena: For RDF/OWL compatibility
   - Stardog: For advanced reasoning capabilities

2. **Data Migration Strategy**
   ```python
   # Example Neo4j migration
   def migrate_to_neo4j():
       # Load ontology schema
       schema = load_yaml("ontology-schema.yaml")

       # Create node constraints
       create_unique_constraints()

       # Import class hierarchies
       import_class_hierarchies()

       # Import relationships
       import_relationships()
   ```

3. **Query Adaptation**
   - Convert YAML patterns to native query language
   - Implement query builders for each database
   - Maintain schema validation layer

4. **Integration Architecture**
   ```plaintext
   [Ontology Schema]
         ↓
   [Query Translator]
         ↓
   [Database Adapter]
         ↓
   [Graph Database]
   ```

### Database-Specific Implementations

1. **Neo4j (Cypher)**
   ```cypher
   MATCH (v:DigitalVenture)-[:IMPLEMENTS_AI]->(p:AIProcess)
   WHERE v.current_phase = 'Phase2'
   RETURN v, p
   ```

2. **Apache Jena (SPARQL)**
   ```sparql
   SELECT ?venture ?process
   WHERE {
     ?venture a :DigitalVenture ;
              :implementsAI ?process .
     ?process a :AIProcess .
   }
   ```

3. **Stardog**
   ```sparql
   PREFIX onto: <http://wmo-digital-ai.org/ontology#>
   SELECT ?venture
   WHERE {
     ?venture a onto:DigitalVenture ;
              onto:usesAIModule true .
   }
   ```

## Best Practices
1. Always specify node types explicitly
2. Use relationship constraints for precise results
3. Include phase and AI module filters where relevant
4. Consider ontology constraints in queries