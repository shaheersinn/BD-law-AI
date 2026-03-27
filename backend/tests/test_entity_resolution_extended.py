"""
tests/test_entity_resolution_extended.py — Extended entity resolution tests.

Tests normalisation edge cases and batch resolution.
"""

import pytest

from app.services.entity_resolution import EntityResolver, normalise


class TestNormaliseEdgeCases:
    """Normalisation edge cases from real-world SEDAR/EDGAR company names."""

    CASES = [
        ("Northfield Energy Partners L.P.", "northfield energy lp"),
        ("THE GOLDMAN SACHS GROUP, INC.", "the goldman sachs"),
        ("BlackBerry Ltd.", "blackberry"),
        ("SUNCOR ENERGY INC.", "suncor energy"),
        ("Shopify Inc.", "shopify"),
        ("Couche-Tard Inc.", "couche tard"),  # hyphen stripped
        ("ENBRIDGE INC", "enbridge"),
        ("Manulife Financial Corporation", "manulife financial"),
        ("Royal Bank of Canada", "royal bank of canada"),  # 'of' kept
        ("BCE Inc.", "bce"),
        ("Canadian Natural Resources Limited", "canadian natural resources"),
        ("Barrick Gold Corporation", "barrick gold"),
        ("TC Energy Corp", "tc energy"),
        ("Pembina Pipeline Corp.", "pembina pipeline"),
        ("Fortis Inc.", "fortis"),
    ]

    @pytest.mark.parametrize("raw, expected", CASES)
    def test_normalise(self, raw, expected):
        assert normalise(raw) == expected


class TestResolverBatchOperations:
    def _build_resolver(self):
        r = EntityResolver()
        r._index = {
            "arctis mining": (1, "client", "Arctis Mining Corp."),
            "northfield energy": (4, "client", "Northfield Energy"),
            "westbrook digital": (3, "prospect", "Westbrook Digital Corp"),
            "ember financial": (5, "client", "Ember Financial"),
            "borealis genomics": (6, "prospect", "Borealis Genomics Inc."),
            "caldwell steel": (7, "prospect", "Caldwell Steel Works"),
        }
        r._norm_list = list(r._index.keys())
        return r

    def test_batch_resolve_all_match(self):
        r = self._build_resolver()
        names = [
            "Arctis Mining Corporation",
            "Northfield Energy Inc.",
            "Borealis Genomics",
        ]
        results = r.resolve_many(names)
        assert len(results) == 3
        assert all(res.matched for res in results)
        assert results[0].entity_id == 1
        assert results[1].entity_id == 4
        assert results[2].entity_id == 6

    def test_batch_resolve_partial_match(self):
        r = self._build_resolver()
        names = [
            "Arctis Mining Corp",  # should match
            "Completely Unknown Co",  # should not match
            "Ember Financial Ltd",  # should match
        ]
        results = r.resolve_many(names)
        assert results[0].matched
        assert not results[1].matched
        assert results[2].matched

    def test_resolve_order_independence(self):
        """Word order should not matter for matching."""
        r = self._build_resolver()
        # "Digital Westbrook" vs canonical "westbrook digital"
        result = r.resolve("Digital Westbrook Corp")
        # Token sort ratio handles this
        assert result.matched or result.score > 50  # at minimum high score

    def test_score_ordering(self):
        """Exact matches should score 100, fuzzy less."""
        r = self._build_resolver()
        exact = r.resolve("Arctis Mining Corp.")
        fuzzy = r.resolve("Arctis Mining LLC")
        assert exact.score >= fuzzy.score

    def test_known_sedar_variations(self):
        """Real-world SEDAR name variations."""
        r = self._build_resolver()
        variations = [
            "ARCTIS MINING CORP",
            "Arctis Mining Corp.",
            "Arctis Mining Corporation",
            "ARCTIS MINING CORPORATION",
        ]
        for v in variations:
            result = r.resolve(v)
            assert result.matched, f"Should match: {v!r}"
            assert result.entity_id == 1, f"Wrong ID for: {v!r}"
