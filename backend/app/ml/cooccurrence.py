"""
app/ml/cooccurrence.py — Enhancement 5: Signal co-occurrence mining.

Apriori algorithm on ground truth labels + signal_records.
Finds signal combinations that together predict mandates better individually.

Output: signal_rules table — {antecedent_signals, consequent_practice_area,
        support, confidence, lift}

Uses mlxtend.frequent_patterns.apriori (pure Python, no CUDA required).
Runs monthly as Celery task agents.mine_signal_cooccurrence.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# Apriori hyperparameters
MIN_SUPPORT: float = 0.05        # signal combo must appear in ≥ 5% of mandate events
MIN_CONFIDENCE: float = 0.50     # 50%+ of times combo fires, mandate follows
MIN_LIFT: float = 1.5            # combo predicts 50% better than individual signals
MAX_RULES: int = 200             # store top 200 rules by lift (prevents noise storage)
MAX_ITEMSET_SIZE: int = 4        # max signals in one rule (combinatorial explosion)


def build_transaction_matrix(
    mandate_events: list[dict[str, Any]],
) -> pd.DataFrame:
    """
    Build binary transaction matrix from mandate events + their preceding signals.

    Args:
        mandate_events: List of {mandate_id, practice_area, signal_types: [str...]}
                        Each event = one "basket" of signals that co-occurred.
    Returns:
        pd.DataFrame: Binary matrix [n_events × n_unique_signals]
    """
    if not mandate_events:
        return pd.DataFrame()

    # Collect all unique signal types
    all_signals: set[str] = set()
    for event in mandate_events:
        for sig in event.get("signal_types", []):
            all_signals.add(sig)

    if not all_signals:
        return pd.DataFrame()

    signal_list = sorted(all_signals)
    rows: list[dict[str, bool]] = []

    for event in mandate_events:
        event_signals = set(event.get("signal_types", []))
        rows.append({sig: sig in event_signals for sig in signal_list})

    return pd.DataFrame(rows, dtype=bool)


def mine_rules(
    transaction_df: pd.DataFrame,
    practice_area: str,
    min_support: float = MIN_SUPPORT,
    min_confidence: float = MIN_CONFIDENCE,
    min_lift: float = MIN_LIFT,
    max_rules: int = MAX_RULES,
) -> list[dict[str, Any]]:
    """
    Run Apriori + association rule mining on transaction matrix.

    Args:
        transaction_df: Binary matrix from build_transaction_matrix.
        practice_area:  Label for which practice area these rules apply to.
        min_support, min_confidence, min_lift: Apriori thresholds.
        max_rules:      Cap on output rules.

    Returns:
        List of rule dicts ready for signal_rules table.
    """
    if transaction_df.empty:
        log.info("co-occurrence: empty transaction matrix for %s, skipping", practice_area)
        return []

    try:
        from mlxtend.frequent_patterns import apriori, association_rules
    except ImportError:
        log.error("mlxtend not installed. Run: pip install mlxtend")
        return []

    n_transactions = len(transaction_df)
    if n_transactions < 50:
        log.warning(
            "co-occurrence: only %d transactions for %s — results may be unreliable",
            n_transactions, practice_area,
        )

    try:
        # Mine frequent itemsets
        frequent_itemsets = apriori(
            transaction_df,
            min_support=min_support,
            use_colnames=True,
            max_len=MAX_ITEMSET_SIZE,
        )

        if frequent_itemsets.empty:
            log.info("co-occurrence: no frequent itemsets for %s", practice_area)
            return []

        # Generate association rules
        rules = association_rules(
            frequent_itemsets,
            metric="lift",
            min_threshold=min_lift,
        )

        # Filter by confidence
        rules = rules[rules["confidence"] >= min_confidence]

        if rules.empty:
            log.info("co-occurrence: no rules meet thresholds for %s", practice_area)
            return []

        # Sort by lift descending, take top N
        rules = rules.sort_values("lift", ascending=False).head(max_rules)

    except Exception:
        log.exception("co-occurrence: Apriori failed for %s", practice_area)
        return []

    # Convert to table rows
    output_rules: list[dict[str, Any]] = []
    for _, row in rules.iterrows():
        antecedents = sorted(list(row["antecedents"]))
        consequents = sorted(list(row["consequents"]))
        output_rules.append({
            "practice_area": practice_area,
            "antecedent_signals": antecedents,
            "consequent_signals": consequents,
            "support": float(row["support"]),
            "confidence": float(row["confidence"]),
            "lift": float(row["lift"]),
            "n_transactions": n_transactions,
        })

    log.info(
        "co-occurrence: %d rules mined for %s (from %d transactions)",
        len(output_rules), practice_area, n_transactions,
    )
    return output_rules


def mine_all_practice_areas(
    events_by_pa: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """
    Run co-occurrence mining for all practice areas.

    Args:
        events_by_pa: {practice_area: [mandate_event_dicts]}
    Returns:
        {practice_area: [rule_dicts]}
    """
    all_rules: dict[str, list[dict[str, Any]]] = {}
    for pa, events in events_by_pa.items():
        df = build_transaction_matrix(events)
        rules = mine_rules(df, practice_area=pa)
        all_rules[pa] = rules
    return all_rules
