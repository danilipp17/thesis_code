"""
Auto-generated tool: subtract
Subtraction function.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional


class subtractSchema(BaseModel):
    a: float = Field(..., description="Minuend")
    b: float = Field(..., description="Subtrahend")


class subtract(BaseTool):
    name: str = "subtract"
    description: str = """Subtraction function."""
    args_schema: Type[BaseModel] = subtractSchema

    def _coerce_num(self, v):
        if v is None:
            raise ValueError("Missing numeric argument")
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            try:
                if "." in v:
                    return float(v)
                return int(v)
            except Exception:
                try:
                    return float(v)
                except Exception:
                    raise ValueError(f"Unable to coerce value to number: {v}")
        raise ValueError(f"Unsupported numeric type: {type(v)}")

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: tools.arithmetic.subtract
        """
        a = kwargs.get("a", kwargs.get("x", kwargs.get("0")))
        b = kwargs.get("b", kwargs.get("y", kwargs.get("1")))

        a_num = self._coerce_num(a)
        b_num = self._coerce_num(b)

        result = a_num - b_num
        if isinstance(result, float) and result.is_integer():
            return int(result)
        return result
