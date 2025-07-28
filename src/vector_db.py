"""
Utility functions for connecting to and querying a Milvus vector database.

These helpers establish a connection to Milvus and perform similarity searches
against a given collection. They can be extended to support other operations
such as creating and inserting embeddings.
"""
from typing import List, Any, Optional
from pymilvus import Collection, connections


def init_milvus(
    host: str = "localhost",
    port: int = 19530,
    collection_name: str = "your_collection",
) -> Collection:
    """Connect to Milvus and return a collection handle.

    Args:
        host: Milvus host address.
        port: Milvus port number.
        collection_name: Name of the collection to work with.

    Returns:
        A Milvus Collection instance.
    """
    # Establish the connection (idempotent if called multiple times)
    connections.connect(alias="default", host=host, port=port)
    return Collection(collection_name)


def search_vectors(
    collection: Collection,
    query_vectors: List[List[float]],
    top_k: int = 5,
    filter_expr: str = "",
    output_fields: Optional[List[str]] = None,
) -> List[Any]:
    """Perform a vector similarity search on the collection.

    Args:
        collection: The Milvus Collection object.
        query_vectors: A list of query vectors (each vector is a list of floats).
        top_k: Number of nearest neighbors to return.
        filter_expr: Optional boolean expression to filter search results.
        output_fields: Additional fields to return with each result.

    Returns:
        Search results from Milvus.
    """
    search_params = {
        "metric_type": "L2",
        "params": {"nprobe": 16},
    }
    output_fields = output_fields or []
    results = collection.search(
        query_vectors,
        "embedding",
        search_params,
        limit=top_k,
        expr=filter_expr,
        output_fields=output_fields,
    )
    return results
