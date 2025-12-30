# import re


# def compile_intent_to_objective(intent: str) -> dict:
#     text = intent.lower()

#     # unread emails
#     if "unread" in text and "email" in text:
#         limit = 5
#         m = re.search(r"limit\s*=\s*(\d+)", text)
#         if m:
#             limit = int(m.group(1))

#         return {
#             "tool": "check_unread",
#             "args": {"limit": limit},
#         }

#     # read / fetch specific email (resolved later via IRIS)
#     if "fetch email" in text or "read email" in text:
#         return {
#             "tool": "get_email_content",
#             "args": {},
#         }

#     raise RuntimeError(f"Cannot compile intent: {intent}")
