"""
Ontology schema definitions for the WealthMachineOntology Framework
Defines the core relationships and entities in the knowledge graph
"""

class OntologySchema:
    """Base class for ontology schema definitions"""
    def __init__(self):
        self.entities = {}
        self.relationships = {}
    
    def add_entity(self, entity_type, properties):
        """Add a new entity type to the ontology"""
        self.entities[entity_type] = properties
    
    def add_relationship(self, source, target, relation_type):
        """Define a relationship between entities"""
        if not self.relationships.get(source):
            self.relationships[source] = {}
        self.relationships[source][target] = relation_type
