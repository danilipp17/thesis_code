"""
Auto-generated tool: Create Draft
Useful to create an email draft.
The input to this tool should be a pipe (|) separated text
of length 3 (three), representing who to send the email to,
the subject of the email and the actual message.
For example, `lorem@ipsum.com|Nice To Meet You|Hey it was great to meet you.`.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class create_draftSchema(BaseModel):
    pass


class create_draft(BaseTool):
    name: str = "Create Draft"
    description: str = """Useful to create an email draft.
The input to this tool should be a pipe (|) separated text
of length 3 (three), representing who to send the email to,
the subject of the email and the actual message.
For example, `lorem@ipsum.com|Nice To Meet You|Hey it was great to meet you.`."""
    args_schema: Type[BaseModel] = create_draftSchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: tools.create_draft.create_draft

        TODO: Implement tool logic here.
        """
        raise NotImplementedError(
            "Tool implementation must be provided. "
            "Original reference: tools.create_draft.create_draft"
        )
