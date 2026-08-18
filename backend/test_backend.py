import time
import unittest

from ae_catalog import AE_SET_NUMBER, AE_TITLE
from cache import TTLCache
from wikitext import clean_wikitext, field, parse_sets


class BackendTests(unittest.TestCase):
    def test_ae_title_and_set_number(self):
        match = AE_TITLE.match("Rota-AE024 Mulcharmy Fuwaros (SR)")
        self.assertIsNotNone(match)
        self.assertTrue(AE_SET_NUMBER.match(match.group("setNumber")))
        self.assertEqual(match.group("name").strip(), "Mulcharmy Fuwaros")

    def test_wikitext_set_parser(self):
        text = "| jp_sets =\nTW03-JP063; Terminal World 3; Ultra Rare, Secret Rare\n}}"
        self.assertEqual(parse_sets(text)[0]["setNumber"], "TW03-JP063")
        self.assertEqual(field(text, "jp_sets").splitlines()[0], "TW03-JP063; Terminal World 3; Ultra Rare, Secret Rare")

    def test_wikilink_cleaning(self):
        self.assertEqual(clean_wikitext("[[Target]] [[Target|Label]]"), "Target Target")

    def test_ttl_cache_expires(self):
        cache = TTLCache()
        cache.set("key", "value", 0.01)
        self.assertEqual(cache.get("key"), "value")
        time.sleep(0.02)
        self.assertIsNone(cache.get("key"))


if __name__ == "__main__":
    unittest.main()
