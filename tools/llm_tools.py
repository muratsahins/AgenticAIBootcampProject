"""
Bu dosyada LLM çağrıları için yardımcı fonksiyonlar bulunur.
Bozuk veya şemaya uymayan çıktılarda hata mesajı modele geri verilerek yeniden denenir.
"""

import re
from typing import TypeVar

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, ValidationError


T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Model çağrısı tüm denemelere rağmen başarısız oldu."""


# Düşünen modeller açılış etiketini bazen atlar; </think>'e kadar olan her şeyi sil
THINK_PATTERN = re.compile(r"^.*?</think>", re.DOTALL)


def text_call(llm: BaseChatModel, system: str, user: str) -> str:
    try:
        message = llm.invoke([("system", system), ("user", user)])
    except Exception as error:
        raise LLMError(f"Model çağrısı başarısız: {error}") from error

    return THINK_PATTERN.sub("", str(message.content)).strip()


def structured_call(
    llm: BaseChatModel,
    schema: type[T],
    system: str,
    user: str,
    retries: int = 2,
) -> T:
    structured_llm = llm.with_structured_output(schema, method="json_schema")
    prompt = user
    last_error: Exception | None = None

    for _ in range(retries + 1):
        try:
            result = structured_llm.invoke([("system", system), ("user", prompt)])

            if isinstance(result, schema):
                return result

            if isinstance(result, dict):
                return schema.model_validate(result)

            last_error = ValueError("Model boş veya uyumsuz çıktı döndürdü")
        except ValidationError as error:
            last_error = error
        except Exception as error:
            last_error = error

        prompt = f"{user}\n\n[Önceki deneme hatalıydı: {last_error}. Yalnızca geçerli JSON üret.]"

    raise LLMError(f"{schema.__name__} üretilemedi: {last_error}")
