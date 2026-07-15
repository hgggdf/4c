import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pydantic import ValidationError

from app.router.schemas.chat import ChatUpdateSessionTitleModel
from app.service.chat_service import ChatService
from app.service.requests import ChatUpdateSessionTitleRequest


class ChatSessionTitleTest(unittest.TestCase):
    def test_update_session_title_schema_limits_title_to_50_characters(self):
        with self.assertRaises(ValidationError):
            ChatUpdateSessionTitleModel(session_id=1, session_title="标题" * 26)

    def test_chat_service_trims_and_updates_session_title(self):
        entity = SimpleNamespace(
            id=7,
            user_id=1,
            session_title="新对话",
            current_stock_code=None,
            created_at=None,
            updated_at=None,
        )
        repository = Mock()

        def update_title(session_id, title):
            self.assertEqual(session_id, 7)
            entity.session_title = title
            return entity

        repository.update_session_title.side_effect = update_title
        service = object.__new__(ChatService)

        with patch("app.service.chat_service.ChatRepository", return_value=repository):
            result = service._update_session_title(
                object(),
                ChatUpdateSessionTitleRequest(session_id=7, session_title="  恒瑞医药研发管线  "),
            )

        self.assertEqual(result["session_title"], "恒瑞医药研发管线")
        repository.update_session_title.assert_called_once_with(7, "恒瑞医药研发管线")


if __name__ == "__main__":
    unittest.main()
