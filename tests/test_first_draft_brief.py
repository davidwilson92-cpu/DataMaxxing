import unittest
from unittest.mock import patch

from nova.conversation import plan_message


class FirstBriefTests(unittest.TestCase):
    def test_planner_cannot_add_offer_terms_to_new_draft(self):
        message = "Invite beginners to a Saturday pottery class."
        plan = '{"action":"create","brief":"Saturday at 10AM. Limited seats!"}'
        with patch("nova.ai._responses", return_value=plan):
            for history in ([], [{"role": "user", "content": message}]):
                with self.subTest(history=history):
                    result = plan_message(message, {
                        "selected_platforms": ["instagram"],
                        "conversation": history,
                    })
                    self.assertEqual(result.brief, message)
                    self.assertEqual(result.platforms, ["instagram"])

    def test_followup_keeps_existing_offer_terms(self):
        brief = "Saturday at 10AM. Limited seats!"
        with patch("nova.ai._responses", return_value='{"action":"create","brief":"Saturday at 10AM. Limited seats!"}'):
            result = plan_message("Use those details please", {
                "selected_platforms": ["instagram"], "brief": brief,
            })
        self.assertEqual(result.brief, brief)
