import unittest

from jjtq.backend.models.news import Category, News
from jjtq.backend.models.history import History
from jjtq.backend.models.users import User, UserToken


class ModelRelationshipTests(unittest.TestCase):
    def test_models_use_logical_associations_without_foreign_keys(self):
        for model in (Category, News, User, UserToken, History):
            with self.subTest(model=model.__name__):
                self.assertFalse(model.__table__.foreign_keys)
        self.assertIn("category_id", News.__table__.c)
        self.assertIn("user_id", UserToken.__table__.c)
        for model, column in (
            (News, "category_id"), (UserToken, "user_id"),
            (History, "user_id"), (History, "news_id"),
        ):
            self.assertTrue(any(column in index.columns for index in model.__table__.indexes))


if __name__ == "__main__":
    unittest.main()
