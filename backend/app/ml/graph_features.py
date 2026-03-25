"""
app/ml/graph_features.py — Enhancement 3: Corporate graph network features.

Computes graph-based features from MongoDB director interlock graph.
Phase 6: NetworkX centrality metrics (fast, no GPU required).
Phase 10 (future): Replace with GraphSAGE embeddings (PyTorch Geometric).

MongoDB collection: oracle_corporate_graph
Node document: {_id: company_id, name, sector, score_30d}
Edge document (in edges collection): {source: company_id, target: company_id,
    shared_directors: [names], weight: int, last_verified_at: datetime}

Features produced:
    graph_centrality:      normalised degree centrality in director interlock graph
    peer_distress_score:   weighted average mandate probability of connected peers
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import Any

import networkx as nx

log = logging.getLogger(__name__)

# Minimum edge weight (shared directors) to include an edge in the graph
MIN_EDGE_WEIGHT: int = 1
# Maximum graph size for in-memory processing without sampling
MAX_GRAPH_NODES: int = 50_000


# ── Graph builder ─────────────────────────────────────────────────────────────


def build_interlock_graph(
    edge_records: list[dict[str, Any]],
) -> nx.Graph:
    """
    Build NetworkX graph from MongoDB edge records.

    Args:
        edge_records: List of {source, target, weight, ...} dicts.
                      source/target are company_id integers.
    Returns:
        Undirected weighted graph.
    """
    G = nx.Graph()

    for rec in edge_records:
        source = rec.get("source")
        target = rec.get("target")
        weight = rec.get("weight", 1)

        if source is None or target is None:
            continue
        if weight < MIN_EDGE_WEIGHT:
            continue

        G.add_edge(source, target, weight=weight)

    log.info(
        "Built interlock graph: %d nodes, %d edges",
        G.number_of_nodes(),
        G.number_of_edges(),
    )
    return G


def compute_centrality_features(
    G: nx.Graph,
    company_ids: list[int],
    current_scores: dict[int, float] | None = None,
) -> dict[int, dict[str, float]]:
    """
    Compute graph centrality features for a list of company IDs.

    Args:
        G:              Director interlock graph (from build_interlock_graph).
        company_ids:    Companies to compute features for.
        current_scores: Optional {company_id: mandate_probability_30d} for peer distress.

    Returns:
        dict: {company_id: {graph_centrality: float, peer_distress_score: float}}
    """
    if G.number_of_nodes() == 0:
        return {cid: {"graph_centrality": 0.0, "peer_distress_score": 0.0} for cid in company_ids}

    # Degree centrality: fraction of nodes this node is connected to
    degree_centrality = nx.degree_centrality(G)

    results: dict[int, dict[str, float]] = {}

    for company_id in company_ids:
        if company_id not in G:
            results[company_id] = {"graph_centrality": 0.0, "peer_distress_score": 0.0}
            continue

        centrality = degree_centrality.get(company_id, 0.0)

        # Peer distress: weighted average mandate prob of direct neighbours
        peer_distress = 0.0
        if current_scores:
            neighbours = list(G.neighbors(company_id))
            if neighbours:
                total_weight = 0.0
                weighted_score = 0.0
                for neighbour in neighbours:
                    edge_data = G.get_edge_data(company_id, neighbour, default={})
                    weight = edge_data.get("weight", 1.0)
                    score = current_scores.get(neighbour, 0.0)
                    weighted_score += score * weight
                    total_weight += weight
                if total_weight > 0:
                    peer_distress = weighted_score / total_weight

        results[company_id] = {
            "graph_centrality": float(centrality),
            "peer_distress_score": float(peer_distress),
        }

    return results


def build_and_compute(
    edge_records: list[dict[str, Any]],
    company_ids: list[int],
    current_scores: dict[int, float] | None = None,
) -> dict[int, dict[str, float]]:
    """
    Convenience wrapper: build graph + compute features in one call.
    Used by Celery task `agents.update_graph_features`.
    """
    G = build_interlock_graph(edge_records)
    return compute_centrality_features(G, company_ids, current_scores)


def extract_subgraph(
    G: nx.Graph,
    company_id: int,
    depth: int = 2,
) -> dict[str, Any]:
    """
    Extract ego network for a company (for API explain endpoint).

    Args:
        G:          Full interlock graph.
        company_id: Centre node.
        depth:      Hop distance to include.
    Returns:
        {nodes: [{id, name}], edges: [{source, target, weight}]}
    """
    if company_id not in G:
        return {"nodes": [], "edges": []}

    ego = nx.ego_graph(G, company_id, radius=depth)

    nodes = [{"id": n} for n in ego.nodes()]
    edges = [
        {"source": u, "target": v, "weight": d.get("weight", 1)} for u, v, d in ego.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}


# ── MongoDB async fetchers (called from Celery tasks) ─────────────────────────


async def fetch_edge_records_from_mongo(
    mongo_db: Any,
    limit: int = MAX_GRAPH_NODES * 3,
) -> list[dict[str, Any]]:
    """
    Fetch director interlock edges from MongoDB.

    Args:
        mongo_db: Motor AsyncIOMotorDatabase instance.
        limit:    Max edges to retrieve (safety cap).
    Returns:
        List of edge dicts: {source, target, weight, shared_directors, last_verified_at}
    """
    try:
        cursor = mongo_db["corporate_graph_edges"].find(
            {"weight": {"$gte": MIN_EDGE_WEIGHT}},
            {"_id": 0, "source": 1, "target": 1, "weight": 1},
            limit=limit,
        )
        records = await cursor.to_list(length=limit)
        log.info("Fetched %d corporate graph edges from MongoDB", len(records))
        return records
    except Exception:
        log.exception("Failed to fetch corporate graph edges from MongoDB")
        return []


async def upsert_company_graph_node(
    mongo_db: Any,
    company_id: int,
    company_name: str,
    sector: str,
) -> None:
    """Upsert a company node in MongoDB corporate graph."""
    try:
        await mongo_db["corporate_graph_nodes"].update_one(
            {"company_id": company_id},
            {"$set": {"name": company_name, "sector": sector}},
            upsert=True,
        )
    except Exception:
        log.exception("Failed to upsert graph node for company %d", company_id)


async def upsert_director_edge(
    mongo_db: Any,
    company_a: int,
    company_b: int,
    shared_directors: list[str],
) -> None:
    """Upsert a director interlock edge between two companies."""
    from datetime import datetime

    # Canonical edge: lower company_id always as source
    source, target = (min(company_a, company_b), max(company_a, company_b))

    try:
        await mongo_db["corporate_graph_edges"].update_one(
            {"source": source, "target": target},
            {
                "$set": {
                    "shared_directors": shared_directors,
                    "weight": len(shared_directors),
                    "last_verified_at": datetime.now(tz=UTC),
                }
            },
            upsert=True,
        )
    except Exception:
        log.exception("Failed to upsert director edge %d↔%d", source, target)
