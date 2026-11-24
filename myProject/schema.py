from copy import deepcopy
from http import HTTPStatus

from products.models import Category


def document_json_responses(result, generator, request, public):
    error = {
        "type": "object", "required": ["error"],
        "properties": {"error": {"type": "object", "additionalProperties": True}},
        "example": {"error": {"quantity": ["Quantity exceeds available stock."]}},
    }
    result["components"]["schemas"]["ApiError"] = error
    # Swagger renders an enum as a dropdown for form bodies. Keep JSON clients
    # on the integer foreign key and fetch current choices when serving docs.
    names = list(Category.objects.order_by("name").values_list("name", flat=True)) if request is not None else []
    for path, operations in result["paths"].items():
        for method, operation in operations.items():
            if path.startswith("/api/my-products/") and method in ("post", "put", "patch"):
                content = operation["requestBody"]["content"]
                for media in ("application/x-www-form-urlencoded", "multipart/form-data"):
                    ref = content[media]["schema"]["$ref"].split("/")[-1]
                    form = deepcopy(result["components"]["schemas"][ref])
                    field = {"type": "string", "description": "Select an admin-defined category by name."}
                    if names:
                        field["enum"] = names
                    form["properties"]["category"] = field
                    content[media] = {"schema": form}
                form_type = "application/x-www-form-urlencoded"
                operation["requestBody"]["content"] = {form_type: content[form_type], **content}
            responses = operation["responses"]
            for response in responses.values():
                media = response.get("content", {}).get("application/json")
                if media:
                    media["schema"] = {
                        "type": "object", "required": ["data"],
                        "properties": {"data": media["schema"]},
                    }
            errors = {400, 401, 403, 500}
            if "{" in path or path == "/cart/api/items/":
                errors.add(404)
            if method == "delete" and "/categories/" in path:
                errors.add(409)
            for code in errors:
                responses[str(code)] = {
                    "description": HTTPStatus(code).phrase,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiError"}}},
                }
            if method == "get" and path.startswith(("/api/products/", "/api/categories/")):
                operation.setdefault("security", []).append({})
    return result
